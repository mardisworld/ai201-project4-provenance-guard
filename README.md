# Provenance Guard

Provenance Guard is a small text-attribution API that classifies submitted writing as **high-confidence AI**, **high-confidence human**, or **uncertain**. It emphasizes transparency over overclaiming: mixed evidence stays uncertain, and every decision can be appealed and audited.

## Run the project

Start the API server:

```bash
python provenance_guard.py
```

Run the focused test suite:

```bash
python -m unittest discover -s tests -v
```

## API

### `POST /submit`

Accepts JSON content for attribution analysis.

Example request:

```json
{
  "creator_id": "writer-7",
  "content": "I revised the paragraph twice before publishing it to my readers."
}
```

Example response:

```json
{
  "content_id": "1",
  "creator_id": "writer-7",
  "attribution_result": "uncertain",
  "confidence_score": 0.18,
  "transparency_label": "Uncertain attribution: the signals were mixed, so this result should not be used as a final judgment. Review additional context and allow the creator to appeal.",
  "status": "classified",
  "created_at": "2026-06-29T11:30:00Z",
  "signals_used": [
    {
      "name": "lexical_diversity",
      "description": "Measures how often the writer reuses the same words.",
      "value": 0.73,
      "ai_score": 0.0
    },
    {
      "name": "sentence_burstiness",
      "description": "Measures how much sentence lengths vary across the submission.",
      "value": 0.24,
      "ai_score": 0.56
    }
  ],
  "appeal_reasons": []
}
```

### `POST /appeal`

Accepts JSON with the original `content_id` and the creator's reasoning. The system stores the appeal, logs it, and updates the content status to `under review`.

Example request:

```json
{
  "content_id": "1",
  "reason": "I wrote this myself and can share my revision history."
}
```

### `GET /log`

Returns the structured audit log of attribution decisions and appeals.

## Multi-signal detection pipeline

The classifier uses two distinct signals:

1. **Lexical diversity**: repeated reuse of the same vocabulary pushes the result toward AI-generated.
2. **Sentence burstiness**: low variation in sentence lengths pushes the result toward AI-generated.

These two signals were chosen because they capture different writing behaviors: word reuse versus rhythm variation. Using both avoids a single-signal verdict.

## Confidence scoring and uncertainty

`confidence_score` is the certainty of the final classification, not an "AI probability." It is computed from the distance between the combined signal score and the middle of the scale:

- scores near **1.0** = both signals strongly agree
- scores near **0.0** = the signals are mixed, so the system should stay uncertain

This design makes `0.51` and `0.95` meaningfully different. A score near `0.51` can still fall into the **uncertain** bucket, while a score near `0.95` reflects a strong signal consensus.

The thresholds are intentionally conservative to reduce harmful false positives:

- `ai_likelihood <= 0.20` → **high-confidence human**
- `0.20 < ai_likelihood < 0.80` → **uncertain**
- `ai_likelihood >= 0.80` → **high-confidence AI**

That wide uncertain band reflects the project hint that false positives are worse than false negatives on a writing platform.

## Transparency label text

The README includes the verbatim text of all three label variants:

| Variant | Exact text |
| --- | --- |
| High-confidence AI | "High-confidence AI-generated: multiple signals consistently matched AI-like writing patterns. This is a strong indicator, not final proof, and the creator may appeal." |
| High-confidence human | "High-confidence human-written: the submission showed varied phrasing and natural sentence patterns that align with human writing. This is a strong indicator, not final proof, and the creator may appeal." |
| Uncertain | "Uncertain attribution: the signals were mixed, so this result should not be used as a final judgment. Review additional context and allow the creator to appeal." |

## Appeals workflow

Creators can contest a classification through `POST /appeal`. Each appeal:

- captures the creator's reasoning,
- is appended to the audit log alongside the original decision,
- changes the content status to `under review`.

Automated re-classification is intentionally not performed.

## Rate limiting

The submission endpoint is rate limited to **5 submissions per client per 60 seconds**.

- Client identity comes from the `X-Client-Id` header, with remote IP as a fallback.
- The limit is high enough for a normal creator to test a few drafts in quick succession.
- The limit is low enough to slow bulk probing or flooding attempts against the classifier.

## Structured audit log sample

Below is a representative `GET /log` style sample with at least three visible entries:

```json
{
  "entries": [
    {
      "event": "decision",
      "timestamp": "2026-06-29T11:31:00Z",
      "content_id": "1",
      "creator_id": "writer-1",
      "status": "classified",
      "attribution_result": "high-confidence-ai",
      "confidence_score": 0.88,
      "signals_used": [
        {
          "name": "lexical_diversity",
          "description": "Measures how often the writer reuses the same words.",
          "value": 0.29,
          "ai_score": 1.0
        },
        {
          "name": "sentence_burstiness",
          "description": "Measures how much sentence lengths vary across the submission.",
          "value": 0.05,
          "ai_score": 0.91
        }
      ]
    },
    {
      "event": "decision",
      "timestamp": "2026-06-29T11:32:00Z",
      "content_id": "2",
      "creator_id": "writer-2",
      "status": "classified",
      "attribution_result": "high-confidence-human",
      "confidence_score": 0.74,
      "signals_used": [
        {
          "name": "lexical_diversity",
          "description": "Measures how often the writer reuses the same words.",
          "value": 0.94,
          "ai_score": 0.0
        },
        {
          "name": "sentence_burstiness",
          "description": "Measures how much sentence lengths vary across the submission.",
          "value": 0.62,
          "ai_score": 0.0
        }
      ]
    },
    {
      "event": "appeal",
      "timestamp": "2026-06-29T11:33:00Z",
      "content_id": "2",
      "creator_id": "writer-2",
      "status": "under review",
      "original_decision": "high-confidence-human",
      "confidence_score": 0.74,
      "signals_used": [
        {
          "name": "lexical_diversity",
          "description": "Measures how often the writer reuses the same words.",
          "value": 0.94,
          "ai_score": 0.0
        },
        {
          "name": "sentence_burstiness",
          "description": "Measures how much sentence lengths vary across the submission.",
          "value": 0.62,
          "ai_score": 0.0
        }
      ],
      "appeal_reason": "I want a human reviewer to consider my draft history."
    }
  ]
}
```

## Project files

- `provenance_guard.py`: API server, classifier, rate limiter, appeals flow, and audit log
- `planning.md`: architecture diagram and implementation notes
- `tests/test_provenance_guard.py`: focused unit tests for required behavior
