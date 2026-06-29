import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from src.config import SQLITE_DB_PATH


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if not row:
        return None
    return dict(row)


def initialize_store() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS contents (
                content_id TEXT PRIMARY KEY,
                creator_id TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                latest_decision_id TEXT
            );

            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                result TEXT NOT NULL,
                confidence REAL NOT NULL,
                ai_likelihood REAL NOT NULL,
                signals_json TEXT NOT NULL,
                label_text TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS appeals (
                appeal_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                decision_id TEXT,
                creator_id TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                content_id TEXT NOT NULL,
                decision_id TEXT,
                appeal_id TEXT,
                timestamp TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            """
        )


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
        "contentId": content_id,
        "creatorId": creator_id,
        "content": content,
        "status": "classified",
        "createdAt": created_at,
        "updatedAt": created_at,
        "latestDecisionId": None,
    }


def append_audit_entry(
    event_type: str,
    content_id: str,
    payload: dict,
    decision_id: str | None = None,
    appeal_id: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_events (event_id, event_type, content_id, decision_id, appeal_id, timestamp, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (str(uuid4()), event_type, content_id, decision_id, appeal_id, now_iso(), json.dumps(payload)),
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
            "aiLikelihood": ai_likelihood,
            "signals": signals,
            "labelText": label_text,
        },
    )

    return {
        "decisionId": decision_id,
        "contentId": content_id,
        "result": result,
        "confidence": confidence,
        "aiLikelihood": ai_likelihood,
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
        "contentId": data["content_id"],
        "creatorId": data["creator_id"],
        "content": data["content"],
        "status": data["status"],
        "createdAt": data["created_at"],
        "updatedAt": data["updated_at"],
        "latestDecisionId": data["latest_decision_id"],
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
        "decisionId": data["decision_id"],
        "contentId": data["content_id"],
        "result": data["result"],
        "confidence": data["confidence"],
        "aiLikelihood": data["ai_likelihood"],
        "signals": json.loads(data["signals_json"]),
        "labelText": data["label_text"],
        "status": data["status"],
        "createdAt": data["created_at"],
    }


def save_appeal(content_id: str, creator_id: str, reasoning: str) -> dict | None:
    content = get_content_record(content_id)
    if not content:
        return None

    decision = get_decision(content["latestDecisionId"]) if content.get("latestDecisionId") else None
    appeal_id = str(uuid4())
    created_at = now_iso()

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO appeals (appeal_id, content_id, decision_id, creator_id, reasoning, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                appeal_id,
                content_id,
                decision["decisionId"] if decision else None,
                creator_id,
                reasoning,
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
                (decision["decisionId"],),
            )

    appeal = {
        "appealId": appeal_id,
        "contentId": content_id,
        "decisionId": decision["decisionId"] if decision else None,
        "creatorId": creator_id,
        "reasoning": reasoning,
        "status": "under_review",
        "createdAt": created_at,
    }

    append_audit_entry(
        event_type="appeal_submitted",
        content_id=content_id,
        decision_id=appeal["decisionId"],
        appeal_id=appeal_id,
        payload={
            "creatorId": creator_id,
            "reasoning": reasoning,
            "updatedContentStatus": "under_review",
        },
    )

    updated_content = get_content_record(content_id)
    updated_decision = get_decision(content["latestDecisionId"]) if content.get("latestDecisionId") else None
    return {"content": updated_content, "decision": updated_decision, "appeal": appeal}


def get_audit_log() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT event_id, event_type, content_id, decision_id, appeal_id, timestamp, payload_json
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
                "contentId": data["content_id"],
                "decisionId": data["decision_id"],
                "appealId": data["appeal_id"],
                "timestamp": data["timestamp"],
                "payload": json.loads(data["payload_json"]),
            }
        )
    return entries


initialize_store()