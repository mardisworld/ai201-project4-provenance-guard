# ai201-project4-provenance-guard
# AI Guard Rail Project


### M3.1
![alt text](M3.png)
| Request	                                    |     Result
| GET /                                         | ✅ 200 — {service, status}.         
| POST /submit with creator_id + content	    | ✅ 200 — returns content_id, creator_id, content

### M3.2
![alt text](M3.2.png)
| Request                                       |     Response
| GET /                                         | ✅ {service, status}
| POST /submit with creator_id + content        | ✅ status, content_id, creator_id, content, signals
| POST /submit missing content                  | ✅ {"error": "creator_id and content are required."}

** JSON Response for POST/submit**
{
  "content": "ugh my cat knocked my coffee off the desk AGAIN this morning and i just stood    there laughing lol",
  "content_id": "b4cedadb-8376-46ba-90b9-e69d6d906486",
  "creator_id": "creator-42",
  "signals": {
    "groqSignal": {
      "aiLikelihood": 0.2,
      "available": true,
      "model": "llama-3.3-70b-versatile",
      "confidence=classification": "confidence",
      "label": "decision["labelText"]",
      "name": "groq_llama_3_3_70b",
      "rationale": "informal language and personal anecdote suggest human authorship"
    }
  }
}

### M3.3 
![alt text](src/M3.3.png)
Table	Rows	Written per submit?
contents	1	✅ create_content_record — the submission record
decisions	1	✅ save_decision — result, confidence, ai_likelihood, signals, label
audit_events	1	✅ append_audit_entry — the structured log entry
appeals	0	❌ only save_appeal writes it, and the /appeals route is still commented out (M5)


## M4.1

Both of these already exist in classifier.py — the second signal is stylometric_signal, and the combined confidence/ensemble scoring is classify_content. VSCode wrote these for me, and it was working, but I restarted so I could follow the assignment instructions.  They're already wired into /submit. So the real work here is the part you flagged: verifying they match the planning thresholds exactly. I went through it line-by-line against planning.md.

### (1) Second signal — stylometric_signal

lexical_diversity_risk = clamp(1 - type_token_ratio)           # low vocab variety -> higher risk
sentence_burstiness_risk = clamp(1 - burstiness)               # uniform lengths -> higher risk
ai_likelihood = clamp(lexical_diversity_risk * 0.55 + sentence_burstiness_risk * 0.45)

### (2) Confidence + ensemble — classify_content

groq_weight  = 0.65 if groq available else 0.0
style_weight = 0.35 if groq available else 1.0
ai_likelihood = clamp(groq_weight*groq + style_weight*style)

distance_from_mid = abs(ai_likelihood - 0.5) * 2
agreement         = 1 - abs(groq - style)
confidence        = clamp(0.35 + 0.45*distance_from_mid + 0.20*agreement)

if ai_likelihood >= 0.86 and confidence >= 0.75 and groq available:  result = "likely_ai"
elif ai_likelihood <= 0.30 and confidence >= 0.70:                   result = "likely_human"
else:                                                                result = "uncertain"

if not groq available:  confidence = clamp(confidence * 0.75); result = "uncertain"


![alt text](src/M4.1.png)
Verification against planning.md — every value matches
Spec (planning.md)	Code	Match
Stylometric weights 0.55 / 0.45	*0.55 + *0.45	✅
Ensemble Groq 0.65 / stylometric 0.35	0.65 / 0.35	✅
Groq unavailable → 1.0 * stylometric	style_weight = 1.0, groq_weight = 0.0	✅
distance_from_mid = abs(ai−0.5)*2	identical	✅
agreement = 1 − abs(groq−style)	identical	✅
confidence = 0.35 + 0.45·dist + 0.20·agree	identical	✅
likely_ai: ai ≥ 0.86 and conf ≥ 0.75 and Groq available	identical	✅
likely_human: ai ≤ 0.30 and conf ≥ 0.70	identical	✅
else uncertain	identical	✅
Groq unavailable → confidence ×0.75, force uncertain	identical	✅

### M4.2


### M4.3



### M4.4 Test Your Scoring with 4 Deliberately Chosen Prompts

![alt text](<src/text_results 1.png>)
#	Text style	Groq	Stylo	ai_likelihood	Result
1	formal AI-ish "paradigm shift"	0.70	0.35	0.579	uncertain 
2	casual ramen review	0.20	0.32	0.243	likely_human
3	academic finance	0.20	0.41	0.274	likely_human
4	reflective remote-work	0.20	0.34	0.251	likely_human

Diagnosis: why it's underperforming
#	Truth	Should be	Got	Groq	Stylo
1	AI-generated	high / likely_ai	0.579 uncertain ❌	0.70	0.35
2	clearly human	low / likely_human	0.243 likely_human ✅	0.20	0.32
3	formal human	low-mid	0.274 likely_human ✅~	0.20	0.41
4	lightly-edited AI	mid / uncertain	0.251 likely_human ❌	0.20	0.34
Three root causes:

The stylometric signal is non-discriminative here — it sits at 0.32–0.41 for every sample regardless of truth. It's noise, and worse, on AI text (#1) it drags the score down (0.70 → 0.579) and suppresses confidence by "disagreeing" with Groq. It's actively hurting AI detection.
The Groq prompt is explicitly over-conservative. Its system message says "Score attribution risk conservatively to reduce false positive AI accusations." That biases genuine AI text downward — #1 only got 0.70 when it should be ~0.9.
The likely_ai threshold (0.86) is effectively unreachable for real prose given the above two — so AI never gets flagged.
#4 is genuinely hard — Groq itself reads lightly-edited AI as human (0.20). No weight/threshold change fixes that; it needs Groq to catch it (prompt) or a stronger signal.

This is fundamentally a false-positive tradeoff. The original design deliberately made AI accusations hard ("false positives are more harmful"). Your ground truth says it's now too lenient. How aggressive should I make it?

### Implemented Changes 
**Groq prompt (groq_client.py):** drop the "conservative" instruction, ask for a calibrated score → AI text scores higher.
**Ensemble weights (classifier.py):** shift toward the reliable signal — Groq 0.65 → 0.80, stylometric 0.35 → 0.20.
**Thresholds:** lower likely_ai from 0.86 → ~0.65 and its confidence gate 0.75 → ~0.65; keep likely_human ≤ 0.30.

Then I will re-run all 4 samples and fine-tune the numbers to fit the ground truth.
Update planning.md to match.

![alt text](<src/test_results 2.png>)

#	Truth	Ideal	groq	stylo	ai_like	conf	Result	
1	AI-generated	likely_ai	0.85	0.35	0.751	0.676	likely_ai	✅ fixed
2	clearly human	likely_human	0.20	0.32	0.225	0.773	likely_human	✅
3	formal human	uncertain-ish	0.80	0.41	0.722	0.672	likely_ai	❌ now false-positive
4	lightly-edited AI	uncertain/mid	0.20	0.34	0.229	0.765	likely_human	❌ still low
What happened: the calibrated prompt worked — Groq now scores the real AI text (#1) at 0.85 (was 0.70), so it correctly clears likely_ai. But the same aggressiveness makes Groq rate the formal human finance text (#3) at 0.80 too.

The core, honest problem: #1 (formal AI) and #3 (formal human) are nearly indistinguishable to the model — both formal, structured, Groq ~0.8. The only separator is 0.85 vs 0.80, and the stylometric signal can't break the tie because it's flat (0.35 vs 0.41). I could shove the likely_ai threshold to 0.73 to split them, but that's overfitting to a 0.03 gap — it'd be fragile and break on the next sample.

And #4 stays wrong because Groq itself reads lightly-edited AI as human (0.20) — no weighting fixes a signal that doesn't fire.

Notably, #3 and #4 are exactly the two edge cases your planning.md already anticipated — "highly edited human writing… can resemble LLM style" and "hybrid drafts where AI generated a base and a human revised." They're inherently hard for a Groq + stylometry pair.

So to actually improve performance further, the real lever isn't more threshold-tuning — it's a better second signal, since the current stylometric one is dead weight.

I decided to refine the Groq prompt further — explicitly tell it formal/academic/domain-expert writing is not by itself evidence of AI, to pull #3 back down without losing #1.

Big improvement — the prompt refinement fixed #3 and sharpened the clear cases:

#	Truth	Ideal	groq	ai_like	conf	Result	
1	AI-generated	likely_ai	0.90 ↑	0.791	0.702	likely_ai	✅
2	clearly human	likely_human	0.10 ↓	0.145	0.825	likely_human	✅
3	formal human	uncertain/mid	0.70 ↓	0.642	0.620	uncertain	✅ fixed
4	lightly-edited AI	uncertain/mid	0.20	0.229	0.765	likely_human	❌
Now 3 of 4 correct (up from 2), and the errors are no longer false positives:

#1 got stronger (0.90) — clearly likely_ai.
#2 got more confident human (Groq 0.10, conf 0.825).
#3 is the win — telling Groq "formal ≠ AI unless also generic/filler" dropped it from 0.80 → 0.70, so it lands on uncertain — exactly the "borderline" you wanted, no more false AI accusation.
#4 still misses — this is the genuinely hard one. Groq itself reads the lightly-edited AI as human (0.20), because the "I've been thinking…" opener and tradeoff framing look human. It's the "hybrid draft" edge case your planning.md already flags as hard.yes,


## M5 Implement the Production Layer

### M5.1 Generate Confidence Scores to Correct Label Text and Create Appeals Endpoint
Both pieces largely exist — the label function is labels.py's build_transparency_label, and the appeal logic is save_appeal in audit_store.py. I will verify the label function against the spec's three variants, and (2) add the active /appeals endpoint and confirm it updates status + logs.


![alt text](<src/Label and Post.png>)

(1) Label function — all three variants match the spec exactly ✅
Result	Match to planning.md text
likely_ai	✅ MATCH
likely_human	✅ MATCH
uncertain	✅ MATCH
Plus the placeholder rendering is correct: 0.742 → 74% (rounded whole-number percent, as specified).

(2) POST /appeals — updates status and logs correctly ✅
Submitted content (status: classified), then appealed it. Verified in the DB afterward:

Check	Result
contents.status	classified → under_review ✅
decisions.status (latest decision)	final → under_review ✅
appeals row created	✅ (status: under_review, reasoning stored)
audit_events appeal_submitted logged	✅ (1 event)
Response	plain JSON: "Appeal submitted. Content is now under review." + appeal + decision
Error paths also behave (plain JSON, no status codes):

Unknown content_id → {"error": "content_id not found."}
Missing creator_reasoning → {"error": "content_id, creator_id, and creator_reasoning are required."}

/appeal → 200, "Appeal submitted. Content is now under review." ✅

### M5.2 Transparency Label 
![alt text](<src/label transparency.png>)
Input	attribution	confidence	Label returned
templated/repetitive	likely_ai	90%	"…likely AI-generated (high confidence: 90%). If this is incorrect, the creator can submit an appeal…"
formal domain prose	uncertain	62%	"We could not confidently determine… (current confidence: 62%). No enforcement action is taken…"
casual personal	likely_human	83%	"…likely human-written (high confidence: 83%). If new evidence appears…"

Both requirements demonstrated:

1. Not static — three genuinely different label texts came back, and the confidence percent varies per submission (90% / 62% / 83%), rendered live from each decision's confidence score.

2. All three variants reachable — distinct label categories reached via /submit: ['likely_ai', 'likely_human', 'uncertain'].

The mapping works exactly as specified: the decision bucket selects the variant (AI / human / uncertain) and {{confidence}} is substituted with the rounded percent. The label is built in /submit via build_transparency_label(classification["result"], classification["confidence"]) and stored on the decision record for auditability.

### M5.3 Appeals Workflow

![alt text](src/POST:appeal;.png)
The POST /appeal endpoint now matches your instruction's contract exactly and does everything required:

Request — content_id + creator_reasoning only (no creator_id needed):
Response — 200, confirmation returned:

"message": "Appeal submitted. Content is now under review."

Checking the three required behaviors:

Requirement	Result
Accepts content_id + creator_reasoning	✅ (creator_id auto-derived from the stored content: creator-42)
Update content status to "under review"	✅ contents.status → under_review
Log appeal alongside the original classification decision	✅ audit events for this content: ['classification_decision', 'appeal_submitted']
Return confirmation	✅ "Appeal submitted. Content is now under review." + full appeal + original decision
No automated re-classification	✅ (not implemented, as specified)


### M5.4 Rate-Limiting 

request 1–10  → 200   (within limit)
request 11    → 429   (Too Many Requests)
request 12    → 429


### M5.5 Audit Log 
![alt text](<src/Audit Table.png>)
Required field	Captured?	Where
timestamp	✅	timestamp column (every entry)
content ID	✅	content_id column (every entry)
attribution result	✅	attribution column + payload_json.result
confidence score	✅	confidence column + payload_json.confidence
signal 1 (Groq) score	✅	llm_score column + payload_json.signals.groqSignal.ai_likelihood
signal 2 (stylometric) score	✅	payload_json.signals.stylometricSignal.ai_likelihood
appeal filed?	✅	presence of an appeal_submitted event + appeal_id, linked by content_id
structured format	✅	SQLite columns + JSON payload_json (not console output)

![alt text](src/audit-log.png)

```
{
  "entries": [
    {
      "appealId": null,
      "attribution": "likely_ai",
      "confidence": 0.8696250000000001,
      "content_id": "6e3f88c3-92c1-4cd5-a6a6-eb33e6a362b1",
      "creator_id": null,
      "decision_id": "4e1773f7-a99a-4501-92f8-74a1cb9f7cf3",
      "eventId": "a587a8a0-25df-4849-8d2d-9a0e851533bf",
      "eventType": "classification_decision",
      "llm_score": 0.9,
      "payload": {
        "ai_likelihood": 0.8787500000000001,
        "confidence": 0.8696250000000001,
        "labelText": "Transparency Notice: This content is likely AI-generated (high confidence: 87%). If this is incorrect, the creator can submit an appeal for human review.",
        "result": "likely_ai",
        "signals": {
          "groqSignal": {
            "ai_likelihood": 0.9,
            "available": true,
            "model": "llama-3.3-70b-versatile",
            "name": "groq_llama_3_3_70b",
            "rationale": "repetitive and formulaic phrasing with lack of specific details or personal voice"
          },
          "stylometricSignal": {
            "ai_likelihood": 0.79375,
            "components": {
              "lexicalDiversityRisk": 0.625,
              "sentenceBurstinessRisk": 1.0
            },
            "name": "stylometric_heuristics"
          },
          "weights": {
            "groq": 0.8,
            "stylometric": 0.2
          }
        }
      },
      "status": "final",
      "stylometric_score": 0.79375,
      "timestamp": "2026-07-01T05:19:18.042483+00:00"
    },
    {
      "appealId": "8dfab17d-9376-451b-bc40-ddc6f7b95b53",
      "attribution": "likely_ai",
      "confidence": 0.8696250000000001,
      "content_id": "6e3f88c3-92c1-4cd5-a6a6-eb33e6a362b1",
      "creator_id": "c1",
      "decision_id": "4e1773f7-a99a-4501-92f8-74a1cb9f7cf3",
      "eventId": "979ee1c8-80a4-444e-9f7f-e4da3d98a1b7",
      "eventType": "appeal_submitted",
      "llm_score": 0.9,
      "payload": {
        "creator_id": "c1",
        "creator_reasoning": "this is my own plain-style writing",
        "updatedContentStatus": "under_review"
      },
      "status": "under_review",
      "stylometric_score": 0.79375,
      "timestamp": "2026-07-01T05:19:18.048259+00:00"
    },
```

## Implementation Notes (divergences from the original plan)

The following reflect where the built system differs from the plan above:

- **Rate limit:** configurable via `RATE_LIMIT_SUBMIT` in `.env`; currently set to
  `10 per minute` (the original plan specified 12 per IP per 15 minutes).
- **Appeals endpoint:** the route is `POST /appeal` (singular), not `/appeals`.
- **`audit_events` columns:** in addition to the planned fields, the table has
  `creator_id`, `attribution`, `confidence`, `llm_score` (Groq signal),
  `stylometric_score`, and `status`, so each audit row is self-contained.
- **`appeals.reasoning` → `creator_reasoning`:** the column and payload field were
  renamed to `creator_reasoning`.
- **Extra endpoints:** `GET /` returns `{service, status}` and `GET /health`
  returns `{ok, service}`.
- **`GET /log` response:** each entry includes the flat columns above alongside the
  structured `payload`.
- **Field naming:** request/response payloads use snake_case
  (`content_id`, `creator_id`, `creator_reasoning`); some example payloads above
  still show camelCase and are illustrative only.


Implemented these changes before I started running trials. 
  - With only one sentence, length variance is undefined, so burstiness risk defaults to a neutral 0.5 (rather than the maximum) to avoid biasing single-sentence inputs toward AI.
- Single sentence → burstRisk = 0.500 (neutral) — previously this was pinned at 1.00, which had inflated the combined score. Now it's 0.327 instead of the old ~0.57.
- Multi-sentence → burstRisk = 0.641, computed normally from actual length variance (unchanged behavior).

--------------------------------------------------------------------------------------
# Provenance Guard — README answers

## Detection Signals

Provenance Guard combines **two independent detection signals** into a weighted ensemble (Groq 0.80 / stylometric 0.20). They are deliberately different in *what they look at*, so one covers the other's blind spots.

### Signal 1 — Groq semantic attribution (`llama-3.3-70b-versatile`)

- **What it measures:** the *semantic and discourse-level* character of the text — tone, voice, specificity, and whether the writing reads as lived/personal versus generic and formulaic. It evaluates meaning and register in context (e.g. "does this sound like a person with a real opinion, or like templated filler such as *'paradigm shift'*, *'it is important to note'*, *'furthermore, stakeholders must collaborate'*?"). It returns a calibrated `ai_likelihood` in `[0, 1]` plus a short rationale.
- **What it captures that surface stats can't:** the *difference between formal-because-AI and formal-because-expert*. Academic or domain-heavy human writing is formal but substantive; AI filler is formal but hollow. The model can tell these apart where word/sentence counts cannot.
- **What it misses / fails on:**
  - **Lightly-edited or hybrid AI** — if a human adds a personal-sounding opener ("I've been thinking about…"), the model tends to read it as human and under-scores it.
  - **Non-determinism and opacity** — it's a black-box probability with no reproducible surface metric; two similar inputs can score slightly differently.
  - **Availability** — it depends on a network API/key; when unavailable the system falls back to stylometry only and forces an `uncertain` result.

### Signal 2 — Stylometric heuristics (deterministic, local Python)

Combines two sub-metrics into one score (weighted 0.55 / 0.45):

- **Lexical diversity risk** — based on the *type–token ratio* (unique words ÷ total words). It measures how repetitive the vocabulary is: reusing the same words → low diversity → higher AI-risk; a wide vocabulary → lower risk. **Property measured:** vocabulary repetition.
- **Sentence burstiness risk** — based on the *variance in sentence lengths*. Human writing tends to mix short and long sentences (high "burstiness"); very uniform sentence lengths look more machine-like → higher risk. **Property measured:** structural/rhythmic uniformity.

- **What it captures:** cheap, deterministic, reproducible surface structure — an independent cross-check that doesn't depend on any model or network.
- **What it misses / fails on:**
  - **No semantic understanding** — it is blind to meaning, tone, or truth. A repetitive human rant scores AI-like; a lexically varied AI passage scores human-like.
  - **Short text** — with only one sentence, length variance is undefined, so burstiness defaults to a neutral 0.5; and very short submissions (< 15 words) carry too little signal to be reliable (the pipeline forces those to `uncertain`).
  - **Genre sensitivity** — poetry, song lyrics, lists, and template-driven writing (e.g. scholarship statements) can look "machine-like" to the heuristics even when human-written.

### Why Two Signals

Groq is the stronger, semantic reader (hence the 0.80 weight); stylometry is a deterministic, model-independent sanity check (0.20). The confidence score rewards **agreement** between them and drops when they disagree, so the system is appropriately less certain exactly where the two signals see the text differently.

## Confidence Scoring & Validation

### How the two signals become one score

1. **Fuse the signals into `ai_likelihood`** (both scores are in `[0, 1]`, 0 = human, 1 = AI):
   - Groq available: `ai_likelihood = clamp(0.80 * groq + 0.20 * stylometric)`
   - Groq unavailable: `ai_likelihood = clamp(1.0 * stylometric)`, and the result is forced to `uncertain` as a safety guardrail.

2. **Compute a confidence** that blends *decisiveness* (how far the score is from the ambiguous middle) with *cross-signal agreement*:
   - `distance_from_mid = abs(ai_likelihood - 0.5) * 2`
   - `agreement = 1 - abs(groq - stylometric)`
   - `confidence = clamp(0.35 + 0.45 * distance_from_mid + 0.20 * agreement)`
   - If Groq is unavailable, confidence is down-weighted by 25%.

3. **Map to a label bucket** using both the score and the confidence:
   - `likely_ai` — `ai_likelihood >= 0.65` **and** `confidence >= 0.65` **and** Groq available
   - `likely_human` — `ai_likelihood <= 0.30` **and** `confidence >= 0.70`
   - `uncertain` — anything else
   - **Short-text guard:** fewer than 15 words → forced `uncertain` (too little signal; burstiness is undefined on a single sentence).

The confidence formula is what makes disagreement visible: when Groq and stylometry point opposite ways, `agreement` is low, confidence drops, and borderline items fall into `uncertain` rather than being labeled with false certainty.

### How I validated that the scores are meaningful

**1. Inputs engineered to land in different buckets.** Submitting deliberately contrasting texts produced clearly different scores and *all three* label categories, with confidence varying per input:

| Input style | ai_likelihood | confidence | result |
|---|---|---|---|
| Templated / repetitive ("The system is fast. The system is reliable…") | ~0.79–0.90 | ~0.87–0.90 | `likely_ai` |
| Casual personal (ramen review) | ~0.14–0.25 | ~0.83–0.86 | `likely_human` |
| Formal domain prose (monetary policy) | ~0.56–0.64 | ~0.56–0.62 | `uncertain` |

This confirms the score is **not static** — a polished/uniform passage and a casual, irregular one produce very different results, and the confidence percent shown in the transparency label changes accordingly (e.g. 90% vs 62% vs 83%).

**2. Cross-signal divergence check.** Running the same inputs through each signal separately showed *where* they agree and disagree — e.g. formal writing that stylometry rates AI-ish but Groq (correctly) reads as human — which is exactly what the `agreement` term in the confidence formula down-weights.

**3. Threshold calibration against labeled samples.** An initial configuration (weights 0.65/0.35, `likely_ai` at `0.86/0.75`, a "score conservatively" prompt) *under-detected* AI: a clearly AI-generated sample stayed `uncertain` and never reached `likely_ai`. Testing against four hand-labeled inputs (clear AI, clear human, formal human, lightly-edited AI) drove the recalibration to weights `0.80/0.20`, `likely_ai` at `0.65/0.65`, and a calibrated prompt — after which clear AI → `likely_ai`, clear human → `likely_human`, and formal human → `uncertain`. (Lightly-edited/hybrid AI remains hard and is handled via the appeals workflow rather than more aggressive thresholds.)

## Transparency Label Variants

Exactly one label is returned in every `POST /submit` response and stored with the decision. `{{confidence}}` is replaced with the confidence score rendered as a rounded whole-number percent (e.g. `0.742` → `74%`).

| Result | Transparency label text |
|---|---|
| `likely_ai` | `Transparency Notice: This content is likely AI-generated (high confidence: {{confidence}}%). If this is incorrect, the creator can submit an appeal for human review.` |
| `likely_human` | `Transparency Notice: This content is likely human-written (high confidence: {{confidence}}%). If new evidence appears, this decision can still be re-reviewed.` |
| `uncertain` | `Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: {{confidence}}%). No enforcement action is taken while the decision is uncertain.` |

**Rendered examples** (with the percent filled in from a real decision):

- **likely_ai (90%)** — "Transparency Notice: This content is likely AI-generated (high confidence: 90%). If this is incorrect, the creator can submit an appeal for human review."
- **likely_human (86%)** — "Transparency Notice: This content is likely human-written (high confidence: 86%). If new evidence appears, this decision can still be re-reviewed."
- **uncertain (56%)** — "Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: 56%). No enforcement action is taken while the decision is uncertain."

Design rules: labels stay probabilistic ("likely", never absolute); the AI label includes explicit appeal guidance; and the uncertain label explicitly states that no enforcement action is taken.

## Appeals Workflow (end-to-end)

A creator disputes a decision by `POST /appeal` with the `content_id` and their reasoning. The endpoint persists the appeal, moves the content **and its latest decision** to `under_review`, and logs a structured `appeal_submitted` event.

**1. Submit an appeal (with creator reasoning):**

```bash
curl -s -X POST http://localhost:5000/appeal \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "26704006-9161-49da-ace2-6bfd8f3bef43",
    "creator_id": "creator-42",
    "creator_reasoning": "I wrote this deliberately in a plain, repetitive style from my own notes — it is my own work."
  }'
```

**Response** — confirmation + status moved to `under_review`:

```json
{
  "message": "Appeal submitted. Content is now under review.",
  "content_id": "26704006-9161-49da-ace2-6bfd8f3bef43",
  "status": "under_review",
  "appeal": {
    "appealId": "65c0ee1f-e58e-4dc2-93a6-ea910265dc31",
    "creator_reasoning": "I wrote this deliberately in a plain, repetitive style from my own notes — it is my own work.",
    "status": "under_review"
  }
}
```

**2. Content status updated to `under_review`:**

```
status BEFORE appeal:  classified
status AFTER appeal:   under_review
```

**3. Appeal visible in the audit log** (`GET /log` → the `appeal_submitted` entry, linked to the disputed decision by `content_id`/`decision_id`):

```json
{
  "eventType": "appeal_submitted",
  "content_id": "26704006-9161-49da-ace2-6bfd8f3bef43",
  "decision_id": "49c6fbae-ac71-43b2-bb52-33dc0c5150f6",
  "appealId": "65c0ee1f-e58e-4dc2-93a6-ea910265dc31",
  "timestamp": "2026-07-01T05:50:47.881365+00:00",
  "attribution": "likely_ai",
  "status": "under_review",
  "payload": {
    "creator_id": "creator-42",
    "creator_reasoning": "I wrote this deliberately in a plain, repetitive style from my own notes — it is my own work.",
    "updatedContentStatus": "under_review"
  }
}
```

The appeal event sits right alongside the original `classification_decision` for the same `content_id`/`decision_id`, so the audit trail shows both the decision and the dispute against it.

## Scoring Limits — Chosen From Testing, Not Defaults

The decision boundaries and signal weights were **tuned against platform-representative content**, not accepted as defaults. The specific limits:

- **Ensemble weights:** Groq `0.80` / stylometric `0.20`
- **`likely_ai`:** `ai_likelihood >= 0.65` **and** `confidence >= 0.65`
- **`likely_human`:** `ai_likelihood <= 0.30` **and** `confidence >= 0.70`
- **`uncertain`:** everything else; plus a short-text guard (< 15 words → `uncertain`)

### Why these values, tied to a writing platform

On a creative writing platform the **most harmful error is a false AI accusation against a real author** — especially formal, academic, or non-native-English writers whose style superficially resembles AI. So the classifier is deliberately asymmetric: it takes strong, agreeing evidence to reach `likely_ai`, while `uncertain` is a safe, no-enforcement middle ground.

To set the limits, four **realistic content types a writing platform actually sees** were tested (see M4.4 above):

| # | Sample type | Ground truth |
|---|---|---|
| 1 | Formal, generic "paradigm shift" prose | AI-generated |
| 2 | Casual first-person review | Human |
| 3 | Formal academic/domain writing | Human (borderline) |
| 4 | Lightly-edited / hybrid AI | Hybrid |

The **original defaults under-performed**: weights `0.65/0.35`, `likely_ai` at `0.86/0.75`, and a "score conservatively" prompt left clearly-AI text stuck at `uncertain`, and the stylometric signal was near-flat noise (0.32–0.41 regardless of source). That evidence drove three results-based changes:

1. **Weights → 0.80/0.20** — lean on the signal that actually discriminates (Groq), since stylometry was dragging correct AI detections toward the middle.
2. **`likely_ai` threshold → 0.65/0.65** — the `0.86` bar was effectively unreachable for real prose, so genuine AI never got flagged.
3. **Calibrated Groq prompt** — told the model that formal/academic writing is *not* by itself evidence of AI (only generic/filler-heavy text is), which pulled the formal-human sample (#3) back from a false `likely_ai` down to `uncertain`.

**Outcome:** clear AI → `likely_ai`, clear human → `likely_human`, formal human → `uncertain` (3/4 correct, and the errors are no longer false positives). The one remaining miss — lightly-edited/hybrid AI, which Groq itself reads as human — is a known-hard case that the platform handles through the **appeals workflow** rather than by lowering the bar further (which would start falsely flagging real formal writers). This is the deliberate false-positive tradeoff a writing platform should make.

## Known Limitations

These are specific content types the system will likely misclassify, each explained by how the two signals behave — not a generic disclaimer.

### 1. Lightly-edited / hybrid AI (AI draft a human revised) → under-flagged as human
An AI-generated base with a human-added personal opener or a few edits tends to be scored **`likely_human`**. **Why, by signal:** the Groq signal keys on semantic cues — personal voice, lived detail, framing like *"I've been thinking about…"* — and those human touches make it read the piece as human (in our tests it scored ~0.20). The stylometric signal has no semantic understanding to catch the AI-written body, and its surface metrics on such text also look human-ish. With **both** signals low, the ensemble lands `likely_human`. This is precisely why the appeals workflow exists.

### 2. Poetry, song lyrics, or intentionally repetitive verse → over-flagged as AI
A human poem with a repeated refrain and even line lengths can be pushed toward **`likely_ai`**. **Why, by signal:** the stylometric heuristic reads *low lexical diversity* (repeated words → high `lexicalDiversityRisk`) and *uniform line/sentence lengths* (→ high `sentenceBurstinessRisk`) as machine-like — so intentional, human stylistic repetition scores high on stylometry. If Groq is only mildly confident, the fused score can cross into AI territory: a false positive against a human artist.

### 3. Formal, academic, or non-native-English human writing → false `likely_ai` or `uncertain`
This is the exact case that forced our recalibration. Structured, formal, low-personal-voice prose shares surface features with AI. **Why, by signal:** stylometry reads it mid-to-high (uniform sentences, restrained vocabulary), and Groq — before the "formal ≠ AI" prompt fix — rated a genuine academic sample at **0.80** (AI-leaning). Even after calibration, formal-AI (#1) and formal-human (#3) are nearly indistinguishable to Groq (both ~0.7–0.9), so a real formal or ESL author can land `uncertain` or, at the margin, `likely_ai`. The conservative thresholds + appeals path are the mitigation, but the underlying signal ambiguity remains.

## Spec Reflection — How the Implementation Diverged from the Plan

**The divergence:** the plan specified a near-balanced ensemble (Groq `0.65` / stylometric `0.35`), a strict `likely_ai` threshold (`ai_likelihood >= 0.86` and `confidence >= 0.75`), and a Groq system prompt instructed to "score attribution risk conservatively." The implementation ended up at Groq `0.80` / stylometric `0.20`, `likely_ai` at `0.65 / 0.65`, and a *calibrated* (non-conservative) prompt.

**Why the plan didn't survive contact with real inputs.** The plan rested on an assumption I didn't test until implementation: that the two signals were *co-equal cross-checks*. When I ran four realistic samples, two assumptions broke:

1. **The stylometric signal wasn't an independent check — it was noise.** It scored 0.32–0.41 for *every* sample regardless of whether the text was AI or human. Weighting it at 0.35 didn't add a second opinion; it diluted the one signal that worked (Groq) and actively pulled correct AI detections down toward the ambiguous middle.
2. **"Conservative" collapsed into "useless."** The `0.86` bar plus the conservative prompt meant genuine AI text scored ~0.70 and never crossed the threshold — the system flagged AI *never*. I had equated "high bar = safe," but a classifier that can't reach its own AI label isn't cautious, it's inert.

**What I changed and the reasoning:** I shifted weight to the signal that actually discriminated (Groq → 0.80), lowered the AI bar to something reachable (0.65/0.65), and rewrote the prompt to separate *formulaic AI filler* from *substantive formal/expert human writing* — which was the specific failure the strict-conservative version couldn't fix.

**The lesson for the spec.** The real conservatism a writing platform needs lives in the **`uncertain` bucket and the appeals workflow**, not in an unreachable threshold. The plan tried to buy safety with a high number; the implementation buys it by (a) requiring *agreement* between signals for confidence, (b) defaulting genuinely ambiguous or short text to `uncertain` with no enforcement, and (c) giving creators recourse. That's a different — and I'd argue more honest — safety model than the one I originally wrote down.

(Smaller divergences, documented in planning.md's Implementation Notes: the appeals route is `POST /appeal` (singular), `audit_events` gained dedicated columns beyond the planned `payload_json`, `appeals.reasoning` was renamed `creator_reasoning`, and the rate limit is configurable via `.env`.)

## AI Tool Use

I used an AI coding assistant throughout, but directed it from my own spec and verified every output. Specific instances:

### Instance 1 — Generate the M3 skeleton + first signal (and check the function signature)
- **What I directed:** "Using my planning.md Detection Signal Design section and the architecture diagram, generate (1) a Flask app skeleton with a `POST /submit` route stub and (2) the first (Groq) detection signal function. Verify the function returns a continuous score in `[0,1]`, not a binary flag, and that the route matches my API contract."
- **What the output was:** the assistant produced the `app.py` skeleton (`app`, limiter, `GET /`, `POST /submit` with payload validation) and confirmed `groq_ai_likelihood_signal` returns `ai_likelihood` as a **float score** (not a boolean), with a graceful fallback. It also flagged a real inconsistency — my architecture diagram used camelCase (`creatorId`) while my code used snake_case (`creator_id`) — which I resolved to snake_case. I edited its draft to return plain JSON (no HTTP status codes) per my spec.

### Instance 2 — Recalibrate the scoring from ground-truth samples
- **What I directed:** I gave it four labeled test texts (clearly AI, clearly human, formal human, lightly-edited AI), said the classifier was under-performing, and asked how to fix it.
- **What the output was:** it diagnosed three concrete root causes — the stylometric signal was non-discriminative (0.32–0.41 for every sample), the Groq prompt was over-conservative, and the `0.86` `likely_ai` threshold was unreachable — then implemented weight (`0.65→0.80`), threshold (`0.86→0.65`), and prompt changes and re-ran the samples, improving results from 2/4 to 3/4 correct. It also correctly identified the remaining miss (hybrid AI) as inherently hard and recommended handling it via appeals rather than over-tuning. I approved each change and it updated planning.md to match.

### Instance 3 — Debug a failing Groq API call
- **What I directed:** after live calls errored, I asked it to check whether my Groq API key was actually valid.
- **What the output was:** it made a direct call to Groq's `/models` endpoint and determined the `403` was **not** a bad key — it was a Cloudflare "error 1010" block on `urllib`'s default `User-Agent`, plus a separate SSL certificate-verification failure. It fixed `groq_client.py` by adding a `User-Agent` header and a `certifi`-backed SSL context, after which live scoring returned real values (e.g. casual text → 0.2, formulaic text → 0.9). This saved me from wrongly regenerating a working key.


