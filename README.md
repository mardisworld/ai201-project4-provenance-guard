# Provenance Guard

Provenance Guard is a backend API for creative platforms to classify submitted text as likely AI-generated, likely human-written, or uncertain. It emphasizes transparency and fairness by returning confidence scores, user-facing labels, structured audit events, and an appeals path for creators.

Implementation stack: Python + Flask + Groq + Flask-Limiter + SQLite.

## Stack Summary
| Component | Tool | Notes |
|---|---|---|
| API framework | Flask | Lightweight free Python web API |
| Detection signal 1 | Groq `llama-3.3-70b-versatile` | Uses existing Groq account |
| Detection signal 2 | Stylometric heuristics | Pure Python (no extra ML libs) |
| Rate limiting | Flask-Limiter | Free per-IP submission throttling |
| Audit log | SQLite (`sqlite3`) | Built in, no extra account/setup |

## Features Implemented
- Content submission endpoint: `POST /submit`
- Multi-signal detection pipeline (2 distinct signals)
- Confidence scoring with an explicit uncertainty region
- Transparency labels for readers
- Appeals workflow via `POST /appeals`
- Rate limiting on `POST /submit`
- Structured audit log via SQLite and `GET /log`

## API Endpoints
- `GET /health` - service health check
- `POST /submit` - classify content and return attribution + confidence + transparency label
- `POST /appeals` - creator contests a decision, records reasoning, sets content to `under_review`
- `GET /content/<content_id>` - inspect stored content + latest decision
- `GET /log` - view structured audit events

## Multi-Signal Detection Pipeline
The classifier uses an ensemble of 2 distinct signals:

1. Groq model signal (`llama-3.3-70b-versatile`)
- The backend prompts Groq to return `ai_likelihood` in `[0, 1]` plus rationale.
- This gives a semantic signal that can reason over context and style globally.

2. Stylometric heuristics signal (pure Python)
- Uses lexical diversity risk and sentence burstiness risk.
- Lower lexical diversity and overly consistent cadence increase AI likelihood.

Weights:
- Groq: 0.65
- Stylometric: 0.35
- If Groq is unavailable, stylometric runs with conservative fallback behavior and the final result is forced to `uncertain`.

## Confidence Scoring and Uncertainty
The pipeline computes a weighted AI score and then calibrates it toward avoiding false-positive AI accusations (false positives are more harmful to creators).

Decision thresholds:
- `likely_ai` when `aiLikelihood >= 0.86` and confidence is strong (stricter to reduce false positives)
- `likely_human` when `aiLikelihood <= 0.30` and confidence is strong
- `uncertain` otherwise

Confidence behavior:
- Confidence is returned for the assigned bucket.
- Borderline values (for example around 0.51-0.65) remain in `uncertain` with corresponding uncertainty language.
- Strong signals (for example above 0.90 for AI-likelihood or below 0.10) produce high-confidence labels.

How meaningful scoring was tested:
- Ran crafted samples representing probable AI output, clearly personal narrative, and borderline mixed prose.
- Verified output appears across all three buckets (`likely_ai`, `likely_human`, `uncertain`).
- Verified that close-to-middle scores remain `uncertain` while extreme scores increase confidence.
- Tested Groq-unavailable behavior to ensure conservative fallback (`uncertain`) rather than overconfident claims.

## Transparency Label Variants (Verbatim Text)
These are the exact three label templates used by the API:

| Variant | Exact Label Text |
|---|---|
| High-confidence AI | "Transparency Notice: This content is likely AI-generated (high confidence: {{confidence}}%). If this is incorrect, the creator can submit an appeal for human review." |
| High-confidence human | "Transparency Notice: This content is likely human-written (high confidence: {{confidence}}%). If new evidence appears, this decision can still be re-reviewed." |
| Uncertain | "Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: {{confidence}}%). No enforcement action is taken while the decision is uncertain." |

## Appeals Workflow
`POST /appeals` requires:
- `contentId`
- `creatorId`
- `reasoning`

Behavior:
- Stores creator reasoning as an appeal record.
- Links the appeal to the original decision.
- Updates content status to `under_review`.
- Updates latest decision status to `under_review`.
- Appends an `appeal_submitted` event to the structured audit log.

## Rate Limiting
Configured on `POST /submit` using `Flask-Limiter`:
- Window: 15 minutes
- Max submissions: 12 per IP per window

Reasoning for limits:
- Legitimate creators generally do not need more than a dozen attribution checks in 15 minutes.
- The cap reduces abuse from flooding/probing attacks without harming normal platform use.

## Audit Log
All attribution decisions and appeals are appended as structured events in SQLite.

Each event includes:
- `eventType`
- `timestamp`
- `contentId`
- `decisionId` (when relevant)
- `appealId` (when relevant)
- `payload` with confidence, signals, result, label, and/or appeal reasoning

### Sample `GET /log` Output (3+ Entries)
```json
{
  "entries": [
    {
      "eventType": "classification_decision",
      "contentId": "c1",
      "decisionId": "d1",
      "appealId": null,
      "payload": {
        "result": "likely_ai",
        "confidence": 0.93,
        "aiLikelihood": 0.9,
        "signals": {
          "groqSignal": {
            "name": "groq_llama_3_3_70b",
            "model": "llama-3.3-70b-versatile",
            "available": true,
            "aiLikelihood": 0.95
          },
          "stylometricSignal": {
            "name": "stylometric_heuristics",
            "aiLikelihood": 0.81,
            "components": {
              "lexicalDiversityRisk": 0.77,
              "sentenceBurstinessRisk": 0.86
            }
          }
        }
      }
    },
    {
      "eventType": "classification_decision",
      "contentId": "c2",
      "decisionId": "d2",
      "appealId": null,
      "payload": {
        "result": "likely_human",
        "confidence": 0.88,
        "aiLikelihood": 0.12,
        "signals": {
          "groqSignal": {
            "name": "groq_llama_3_3_70b",
            "model": "llama-3.3-70b-versatile",
            "available": true,
            "aiLikelihood": 0.05
          },
          "stylometricSignal": {
            "name": "stylometric_heuristics",
            "aiLikelihood": 0.24,
            "components": {
              "lexicalDiversityRisk": 0.19,
              "sentenceBurstinessRisk": 0.29
            }
          }
        }
      }
    },
    {
      "eventType": "appeal_submitted",
      "contentId": "c1",
      "decisionId": "d1",
      "appealId": "a1",
      "payload": {
        "creatorId": "creator-42",
        "reasoning": "I drafted this from my own notebook and can provide revision history.",
        "updatedContentStatus": "under_review"
      }
    }
  ]
}
```

## Quick Start
1. Install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Set Groq API key:
```bash
export GROQ_API_KEY="your_key_here"
```

3. Start server:
```bash
python -m src.app
```

If port 3000 is in use, run on another port:
```bash
PORT=3001 python -m src.app
```

4. Submit content:
```bash
curl -X POST http://localhost:3000/submit \
  -H "Content-Type: application/json" \
  -d '{
    "creatorId": "creator-42",
    "content": "In conclusion, it is important to note that this highlights the core issue overall."
  }'
```

5. File an appeal:
```bash
curl -X POST http://localhost:3000/appeals \
  -H "Content-Type: application/json" \
  -d '{
    "contentId": "<content-id-from-submit>",
    "creatorId": "creator-42",
    "reasoning": "This was written by me and I can provide drafts."
  }'
```

6. View audit log:
```bash
curl http://localhost:3000/log
```

## Notes
- Storage is persisted to SQLite (`provenance_guard.db`) for assignment traceability.
- `GET /log` returns structured audit events that include confidence, signals used, and appeal records.
