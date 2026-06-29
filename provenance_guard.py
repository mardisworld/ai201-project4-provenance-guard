from __future__ import annotations

import json
import math
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

HIGH_CONFIDENCE_AI_LABEL = (
    "High-confidence AI-generated: multiple signals consistently matched AI-like "
    "writing patterns. This is a strong indicator, not final proof, and the "
    "creator may appeal."
)
HIGH_CONFIDENCE_HUMAN_LABEL = (
    "High-confidence human-written: the submission showed varied phrasing and "
    "natural sentence patterns that align with human writing. This is a strong "
    "indicator, not final proof, and the creator may appeal."
)
UNCERTAIN_LABEL = (
    "Uncertain attribution: the signals were mixed, so this result should not be "
    "used as a final judgment. Review additional context and allow the creator to "
    "appeal."
)


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def tokenize_words(content: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", content.lower())


def split_sentences(content: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"[.!?]+", content) if part.strip()]
    return sentences or [content.strip()]


@dataclass
class SubmissionRecord:
    content_id: str
    creator_id: str
    content: str
    attribution_result: str
    confidence_score: float
    transparency_label: str
    status: str
    created_at: str
    signals_used: list[dict[str, Any]] = field(default_factory=list)
    appeal_reasons: list[str] = field(default_factory=list)


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("rate limit exceeded")
        self.retry_after = retry_after


class ProvenanceService:
    def __init__(self, submission_limit: int = 5, submission_window_seconds: int = 60) -> None:
        self.submission_limit = submission_limit
        self.submission_window_seconds = submission_window_seconds
        self.audit_log: list[dict[str, Any]] = []
        self.submissions: dict[str, SubmissionRecord] = {}
        self.request_history: dict[str, list[float]] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def submit_content(self, content: str, creator_id: str = "anonymous", client_id: str = "anonymous") -> dict[str, Any]:
        cleaned_content = content.strip()
        if not cleaned_content:
            raise ValueError("content must not be empty")

        with self._lock:
            self._enforce_rate_limit(client_id)

            content_id = str(self._next_id)
            self._next_id += 1

            ai_likelihood, signals = self._score_content(cleaned_content)
            confidence_score = round(abs(ai_likelihood - 0.5) * 2, 2)

            if ai_likelihood >= 0.8:
                attribution_result = "high-confidence-ai"
                transparency_label = HIGH_CONFIDENCE_AI_LABEL
            elif ai_likelihood <= 0.2:
                attribution_result = "high-confidence-human"
                transparency_label = HIGH_CONFIDENCE_HUMAN_LABEL
            else:
                attribution_result = "uncertain"
                transparency_label = UNCERTAIN_LABEL

            record = SubmissionRecord(
                content_id=content_id,
                creator_id=creator_id,
                content=cleaned_content,
                attribution_result=attribution_result,
                confidence_score=confidence_score,
                transparency_label=transparency_label,
                status="classified",
                created_at=utc_timestamp(),
                signals_used=signals,
            )
            self.submissions[content_id] = record
            self.audit_log.append(
                {
                    "event": "decision",
                    "timestamp": record.created_at,
                    "content_id": content_id,
                    "creator_id": creator_id,
                    "status": record.status,
                    "attribution_result": attribution_result,
                    "confidence_score": confidence_score,
                    "signals_used": signals,
                }
            )
            return self._record_to_response(record)

    def file_appeal(self, content_id: str, reason: str) -> dict[str, Any]:
        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise ValueError("reason must not be empty")

        with self._lock:
            record = self.submissions.get(content_id)
            if record is None:
                raise KeyError(content_id)

            record.status = "under review"
            record.appeal_reasons.append(cleaned_reason)
            appeal_entry = {
                "event": "appeal",
                "timestamp": utc_timestamp(),
                "content_id": content_id,
                "creator_id": record.creator_id,
                "status": record.status,
                "original_decision": record.attribution_result,
                "confidence_score": record.confidence_score,
                "signals_used": record.signals_used,
                "appeal_reason": cleaned_reason,
            }
            self.audit_log.append(appeal_entry)
            return {
                "content_id": content_id,
                "status": record.status,
                "appeal_reason": cleaned_reason,
                "original_decision": record.attribution_result,
            }

    def get_audit_log(self) -> dict[str, Any]:
        with self._lock:
            return {"entries": list(self.audit_log)}

    def _enforce_rate_limit(self, client_id: str) -> None:
        now = time.time()
        window_start = now - self.submission_window_seconds
        timestamps = [stamp for stamp in self.request_history.get(client_id, []) if stamp > window_start]
        if len(timestamps) >= self.submission_limit:
            retry_after = max(1, math.ceil(timestamps[0] + self.submission_window_seconds - now))
            self.request_history[client_id] = timestamps
            raise RateLimitExceeded(retry_after=retry_after)
        timestamps.append(now)
        self.request_history[client_id] = timestamps

    def _score_content(self, content: str) -> tuple[float, list[dict[str, Any]]]:
        words = tokenize_words(content)
        if not words:
            neutral_signals = [
                {
                    "name": "lexical_diversity",
                    "description": "Measures how often the writer reuses the same words.",
                    "value": 0.0,
                    "ai_score": 0.5,
                },
                {
                    "name": "sentence_burstiness",
                    "description": "Measures how much sentence lengths vary across the submission.",
                    "value": 0.0,
                    "ai_score": 0.5,
                },
            ]
            return 0.5, neutral_signals

        lexical_diversity = len(set(words)) / len(words)
        lexical_diversity_ai_score = clamp((0.72 - lexical_diversity) / 0.37)

        sentence_lengths = [len(tokenize_words(sentence)) for sentence in split_sentences(content)]
        if len(sentence_lengths) < 2:
            sentence_burstiness = 0.0
            sentence_burstiness_ai_score = 0.5
        else:
            average_length = sum(sentence_lengths) / len(sentence_lengths)
            variance = sum((length - average_length) ** 2 for length in sentence_lengths) / len(sentence_lengths)
            sentence_burstiness = math.sqrt(variance) / max(average_length, 1)
            sentence_burstiness_ai_score = clamp((0.55 - sentence_burstiness) / 0.55)

        signals = [
            {
                "name": "lexical_diversity",
                "description": "Measures how often the writer reuses the same words.",
                "value": round(lexical_diversity, 3),
                "ai_score": round(lexical_diversity_ai_score, 3),
            },
            {
                "name": "sentence_burstiness",
                "description": "Measures how much sentence lengths vary across the submission.",
                "value": round(sentence_burstiness, 3),
                "ai_score": round(sentence_burstiness_ai_score, 3),
            },
        ]
        ai_likelihood = round((lexical_diversity_ai_score * 0.55) + (sentence_burstiness_ai_score * 0.45), 3)
        return ai_likelihood, signals

    def _record_to_response(self, record: SubmissionRecord) -> dict[str, Any]:
        response = asdict(record)
        response.pop("content")
        response["appeal_reasons"] = list(record.appeal_reasons)
        return response


class ProvenanceGuardHandler(BaseHTTPRequestHandler):
    service = ProvenanceService()

    def do_POST(self) -> None:
        if self.path == "/submit":
            self._handle_submit()
            return
        if self.path == "/appeal":
            self._handle_appeal()
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_GET(self) -> None:
        if self.path == "/log":
            self._send_json(self.service.get_audit_log())
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def _handle_submit(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        content = str(payload.get("content", ""))
        creator_id = str(payload.get("creator_id", "anonymous"))
        client_id = self.headers.get("X-Client-Id", self.client_address[0])
        try:
            response = self.service.submit_content(content=content, creator_id=creator_id, client_id=client_id)
        except ValueError as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        except RateLimitExceeded as error:
            self._send_json(
                {"error": "rate limit exceeded", "retry_after_seconds": error.retry_after},
                HTTPStatus.TOO_MANY_REQUESTS,
                extra_headers={"Retry-After": str(error.retry_after)},
            )
            return

        self._send_json(response, HTTPStatus.CREATED)

    def _handle_appeal(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        try:
            response = self.service.file_appeal(
                content_id=str(payload.get("content_id", "")),
                reason=str(payload.get("reason", "")),
            )
        except ValueError as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        except KeyError:
            self._send_json({"error": "unknown content_id"}, HTTPStatus.NOT_FOUND)
            return

        self._send_json(response, HTTPStatus.OK)

    def _read_json_body(self) -> dict[str, Any] | None:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json({"error": "invalid content length"}, HTTPStatus.BAD_REQUEST)
            return None

        raw_body = self.rfile.read(content_length)
        try:
            return json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            self._send_json({"error": "invalid json"}, HTTPStatus.BAD_REQUEST)
            return None

    def _send_json(
        self,
        payload: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        response_body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_body)))
        if extra_headers:
            for header, value in extra_headers.items():
                self.send_header(header, value)
        self.end_headers()
        self.wfile.write(response_body)


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    httpd = ThreadingHTTPServer((host, port), ProvenanceGuardHandler)
    print(f"Serving Provenance Guard on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
