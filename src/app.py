from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.config import PORT, RATE_LIMIT_SUBMIT
from src.labels import build_transparency_label
from src.services.classifier import classify_content
from src.store.audit_store import (
    create_content_record,
    get_audit_log,
    get_content_record,
    get_decision,
    save_appeal,
    save_decision,
)

app = Flask(__name__)
limiter = Limiter(key_func=get_remote_address, app=app, default_limits=[])


@app.get("/health")
def health() -> tuple:
    return jsonify({"ok": True, "service": "provenance-guard"}), 200


@app.post("/submit")
@limiter.limit(RATE_LIMIT_SUBMIT)
def submit() -> tuple:
    body = request.get_json(silent=True) or {}
    creator_id = body.get("creatorId")
    content = body.get("content")

    if not creator_id or not isinstance(content, str) or not content.strip():
        return jsonify({"error": "creatorId and text content are required."}), 400

    content_record = create_content_record(creator_id=creator_id, content=content)
    classification = classify_content(content)
    label_text = build_transparency_label(classification["result"], classification["confidence"])

    decision = save_decision(
        content_id=content_record["contentId"],
        result=classification["result"],
        confidence=classification["confidence"],
        ai_likelihood=classification["aiLikelihood"],
        signals=classification["signals"],
        label_text=label_text,
    )

    return (
        jsonify(
            {
                "contentId": content_record["contentId"],
                "creatorId": content_record["creatorId"],
                "attributionResult": decision["result"],
                "confidenceScore": round(decision["confidence"], 3),
                "aiLikelihood": round(decision["aiLikelihood"], 3),
                "transparencyLabel": decision["labelText"],
                "signals": decision["signals"],
                "status": content_record["status"],
                "decisionId": decision["decisionId"],
            }
        ),
        201,
    )


@app.post("/appeals")
def appeals() -> tuple:
    body = request.get_json(silent=True) or {}
    content_id = body.get("contentId")
    creator_id = body.get("creatorId")
    reasoning = body.get("reasoning")

    if not content_id or not creator_id or not isinstance(reasoning, str) or not reasoning.strip():
        return jsonify({"error": "contentId, creatorId, and reasoning are required."}), 400

    existing = get_content_record(content_id)
    if not existing:
        return jsonify({"error": "contentId not found."}), 404

    result = save_appeal(content_id=content_id, creator_id=creator_id, reasoning=reasoning)
    return (
        jsonify(
            {
                "message": "Appeal submitted. Content is now under review.",
                "contentId": content_id,
                "status": result["content"]["status"],
                "appeal": result["appeal"],
                "decision": result["decision"],
            }
        ),
        201,
    )


@app.get("/content/<content_id>")
def content(content_id: str) -> tuple:
    record = get_content_record(content_id)
    if not record:
        return jsonify({"error": "contentId not found."}), 404

    decision = get_decision(record["latestDecisionId"]) if record.get("latestDecisionId") else None
    return jsonify({"content": record, "decision": decision}), 200


@app.get("/log")
def log() -> tuple:
    return jsonify({"entries": get_audit_log()}), 200


@app.errorhandler(500)
def handle_500(_error):
    return jsonify({"error": "Internal server error."}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)