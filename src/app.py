import uuid
import sys
from pathlib import Path
from flask import Flask, request, jsonify 
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
from datetime import datetime, timezone

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.labels import build_transparency_label
from src.services.classifier import classify_content
from src.services.groq_client import groq_ai_likelihood_signal
from src.config import PORT, RATE_LIMIT_SUBMIT
from src.store.audit_store import (
    create_content_record,
    get_audit_log,
    get_content_record,
    get_decision,
    initialize_store,
    save_appeal,
    save_decision,
)

app = Flask(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


@app.get("/")
def home():
    return jsonify({"service": "provenance-guard", "status": "running"})


## M3: Submit content for AI attribution analysis. Returns skeleton response with
## content_id, creator_id, content, and first detection signal (Groq). Further
## ensemble fusion, confidence, decision bucket, transparency label, and
## persistence are handled in later milestones (M4/M5).
@app.post("/submit")
@limiter.limit(RATE_LIMIT_SUBMIT)
def submit():
    body = request.get_json(silent=True) or {}
    creator_id = body.get("creator_id")
    content = body.get("content")

    # Payload validation.
    if not creator_id or not isinstance(content, str) or not content.strip():
        return jsonify({"error": "creator_id and content are required."})

    # First detection signal: Groq semantic attribution -> ai_ikelihood in [0, 1].
    content = content.strip()
    content_id = str(uuid.uuid4())
    groq_signal = groq_ai_likelihood_signal(content)

    content_record = create_content_record(creator_id=creator_id, content=content)
    classification = classify_content(content)
    label_text = build_transparency_label(classification["result"], classification["confidence"])
    classification["ai_likelihood"] = classification.pop("ai_likelihood")


    decision = save_decision(
        content_id=content_record["content_id"],
        result=classification["result"],
        confidence=classification["confidence"],
        ai_likelihood=classification["ai_likelihood"],
        signals=classification["signals"],
        label_text=label_text,
    )

    # M3 skeleton response shape. Ensemble fusion, confidence, decision bucket,
    # transparency label, and SQLite persistence are wired in M4/M5.
    return jsonify(
        {
            "content_id": content_record["content_id"],
            "creator_id": creator_id,
            "attribution": decision["result"],
            "confidence": round(decision["confidence"], 3),
            "ai_likelihood": round(decision["ai_likelihood"], 3),
            "label": decision["labelText"],
            "signals": decision["signals"],
            "status": content_record["status"],
            "decision_id": decision["decision_id"],
        }
    )


## POST /appeal: a creator disputes a decision. Persists the appeal, moves the
## content (and its latest decision) to under_review, and logs an audit event.
@app.post("/appeal")
def appeal():
    data = request.get_json(silent=True) or {}
    content_id = data.get("content_id")
    creator_id = data.get("creator_id")
    creator_reasoning = data.get("creator_reasoning")

    if not content_id or not creator_id or not isinstance(creator_reasoning, str) or not creator_reasoning.strip():
        return jsonify({"error": "content_id, creator_id, and creator_reasoning are required."})

    creator_reasoning = creator_reasoning.strip()

    existing = get_content_record(content_id)
    if not existing:
        return jsonify({"error": "content_id not found."})

    result = save_appeal(
        content_id=content_id,
        creator_id=creator_id,
        creator_reasoning=creator_reasoning,
    )

    return jsonify(
        {
            "message": "Appeal submitted. Content is now under review.",
            "content_id": content_id,
            "status": result["content"]["status"] if result and result.get("content") else "under_review",
            "appeal": result["appeal"] if result else None,
            "decision": result["decision"] if result else None,
        }
    )


@app.route("/log", methods=["GET"])
def view_log():
    return jsonify({"entries": get_audit_log()})

@app.get("/health")
def health() -> tuple:
    return jsonify({"ok": True, "service": "provenance-guard"})


if __name__ == "__main__":
    initialize_store()
    app.run(host="127.0.0.1", port=PORT, debug=True)










