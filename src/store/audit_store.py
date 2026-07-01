import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.config import SQLITE_DB_PATH

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if not row:
        return None
    return dict(row)


def initialize_store() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with _connect() as conn:
        conn.executescript(schema_sql)


def create_content_record(creator_id: str, content: str) -> dict:
    content_id = str(uuid4())
    created_at = now_iso()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO contents (content_id, creator_id, content, status, created_at, updated_at, latest_decision_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (content_id, creator_id, content, "classified", created_at, created_at, None),
        )

    return {
        "content_id": content_id,
        "creator_id": creator_id,
        "content": content,
        "status": "classified",
        "createdAt": created_at,
        "updatedAt": created_at,
        "latest_decision_id": None,
    }


def append_audit_entry(
    event_type: str,
    content_id: str,
    payload: dict,
    decision_id: str | None = None,
    appeal_id: str | None = None,
    creator_id: str | None = None,
    attribution: str | None = None,
    confidence: float | None = None,
    llm_score: float | None = None,
    stylometric_score: float | None = None,
    status: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_events (
                event_id, event_type, content_id, creator_id, timestamp,
                attribution, confidence, llm_score, stylometric_score, status,
                decision_id, appeal_id, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()), event_type, content_id, creator_id, now_iso(),
                attribution, confidence, llm_score, stylometric_score, status,
                decision_id, appeal_id, json.dumps(payload),
            ),
        )


def save_decision(
    content_id: str,
    result: str,
    confidence: float,
    ai_likelihood: float,
    signals: dict,
    label_text: str,
) -> dict:
    decision_id = str(uuid4())
    created_at = now_iso()

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO decisions
            (decision_id, content_id, result, confidence, ai_likelihood, signals_json, label_text, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                content_id,
                result,
                confidence,
                ai_likelihood,
                json.dumps(signals),
                label_text,
                "final",
                created_at,
            ),
        )
        conn.execute(
            """
            UPDATE contents
            SET latest_decision_id = ?, updated_at = ?
            WHERE content_id = ?
            """,
            (decision_id, now_iso(), content_id),
        )

    append_audit_entry(
        event_type="classification_decision",
        content_id=content_id,
        decision_id=decision_id,
        payload={
            "result": result,
            "confidence": confidence,
            "ai_likelihood": ai_likelihood,
            "signals": signals,
            "labelText": label_text,
        },
        attribution=result,
        confidence=confidence,
        llm_score=(signals.get("groqSignal") or {}).get("ai_likelihood"),
        stylometric_score=(signals.get("stylometricSignal") or {}).get("ai_likelihood"),
        status="final",
    )

    return {
        "decision_id": decision_id,
        "content_id": content_id,
        "result": result,
        "confidence": confidence,
        "ai_likelihood": ai_likelihood,
        "signals": signals,
        "labelText": label_text,
        "status": "final",
        "createdAt": created_at,
    }


def get_content_record(content_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT content_id, creator_id, content, status, created_at, updated_at, latest_decision_id
            FROM contents
            WHERE content_id = ?
            """,
            (content_id,),
        ).fetchone()

    data = _row_to_dict(row)
    if not data:
        return None
    return {
        "content_id": data["content_id"],
        "creator_id": data["creator_id"],
        "content": data["content"],
        "status": data["status"],
        "createdAt": data["created_at"],
        "updatedAt": data["updated_at"],
        "latest_decision_id": data["latest_decision_id"],
    }


def get_decision(decision_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT decision_id, content_id, result, confidence, ai_likelihood, signals_json, label_text, status, created_at
            FROM decisions
            WHERE decision_id = ?
            """,
            (decision_id,),
        ).fetchone()

    data = _row_to_dict(row)
    if not data:
        return None
    return {
        "decision_id": data["decision_id"],
        "content_id": data["content_id"],
        "result": data["result"],
        "confidence": data["confidence"],
        "ai_likelihood": data["ai_likelihood"],
        "signals": json.loads(data["signals_json"]),
        "labelText": data["label_text"],
        "status": data["status"],
        "createdAt": data["created_at"],
    }


def save_appeal(content_id: str, creator_id: str, creator_reasoning: str) -> dict | None:
    content = get_content_record(content_id)
    if not content:
        return None

    decision = get_decision(content["latest_decision_id"]) if content.get("latest_decision_id") else None
    appeal_id = str(uuid4())
    created_at = now_iso()

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO appeals (appeal_id, content_id, decision_id, creator_id, creator_reasoning, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                appeal_id,
                content_id,
                decision["decision_id"] if decision else None,
                creator_id,
                creator_reasoning,
                "under_review",
                created_at,
            ),
        )
        conn.execute(
            """
            UPDATE contents
            SET status = 'under_review', updated_at = ?
            WHERE content_id = ?
            """,
            (now_iso(), content_id),
        )
        if decision:
            conn.execute(
                """
                UPDATE decisions
                SET status = 'under_review'
                WHERE decision_id = ?
                """,
                (decision["decision_id"],),
            )

    appeal = {
        "appealId": appeal_id,
        "content_id": content_id,
        "decision_id": decision["decision_id"] if decision else None,
        "creator_id": creator_id,
        "creator_reasoning": creator_reasoning,
        "status": "under_review",
        "createdAt": created_at,
    }

    append_audit_entry(
        event_type="appeal_submitted",
        content_id=content_id,
        decision_id=appeal["decision_id"],
        appeal_id=appeal_id,
        creator_id=creator_id,
        attribution=decision["result"] if decision else None,
        confidence=decision["confidence"] if decision else None,
        llm_score=(decision["signals"].get("groqSignal") or {}).get("ai_likelihood") if decision else None,
        stylometric_score=(decision["signals"].get("stylometricSignal") or {}).get("ai_likelihood") if decision else None,
        status="under_review",
        payload={
            "creator_id": creator_id,
            "creator_reasoning": creator_reasoning,
            "updatedContentStatus": "under_review",
        },
    )

    updated_content = get_content_record(content_id)
    updated_decision = get_decision(content["latest_decision_id"]) if content.get("latest_decision_id") else None
    return {"content": updated_content, "decision": updated_decision, "appeal": appeal}


def get_audit_log() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT event_id, event_type, content_id, creator_id, timestamp,
                   attribution, confidence, llm_score, stylometric_score, status,
                   decision_id, appeal_id, payload_json
            FROM audit_events
            ORDER BY timestamp ASC
            """
        ).fetchall()

    entries: list[dict] = []
    for row in rows:
        data = dict(row)
        entries.append(
            {
                "eventId": data["event_id"],
                "eventType": data["event_type"],
                "content_id": data["content_id"],
                "creator_id": data["creator_id"],
                "timestamp": data["timestamp"],
                "attribution": data["attribution"],
                "confidence": data["confidence"],
                "llm_score": data["llm_score"],
                "stylometric_score": data["stylometric_score"],
                "status": data["status"],
                "decision_id": data["decision_id"],
                "appealId": data["appeal_id"],
                "payload": json.loads(data["payload_json"]),
            }
        )
    return entries


initialize_store()