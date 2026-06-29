# Provenance Guard Planning

## Architecture

```text
          +--------------------+
POST /submit --> API handler   |
                |              |
                v              |
         +------------------+  |
         | Detection engine |  |
         | - lexical        |  |
         |   diversity      |  |
         | - sentence       |  |
         |   burstiness     |  |
         +------------------+  |
                |              |
                v              |
         +------------------+  |
         | Confidence +     |  |
         | transparency     |  |
         | label selection  |  |
         +------------------+  |
                |              |
                v              |
         +------------------+  |
         | In-memory        |  |
         | submissions +    |  |
         | structured log   |<-+-- POST /appeal
         +------------------+  |
                ^              |
                |              |
              GET /log --------+
```

## Signals

1. **Lexical diversity** measures how often the same words are repeated. Very low diversity pushes the result toward the AI bucket.
2. **Sentence burstiness** measures how much sentence lengths vary. Low variation pushes the result toward the AI bucket.

## Confidence policy

- `confidence_score` reflects classification certainty, not just AI-likelihood.
- Scores near `0.0` mean the signals were mixed.
- Scores near `1.0` mean both signals strongly pointed in the same direction.
- To reduce harmful false positives, the system only emits a high-confidence human label at `ai_likelihood <= 0.20` and a high-confidence AI label at `ai_likelihood >= 0.80`. Everything in between becomes `uncertain`.

## Rate limiting

- Limit: **5 submissions per client per 60 seconds**
- Client identity is taken from the `X-Client-Id` header, falling back to the remote IP address.

## Appeals workflow

1. The creator submits a reason to `POST /appeal`.
2. The system stores the reason with the original submission.
3. The content status changes to `under review`.
4. A structured appeal event is appended to the audit log.
