PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE contents (
                content_id TEXT PRIMARY KEY,
                creator_id TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                latest_decision_id TEXT
            );
INSERT INTO contents VALUES('20d2d201-e5ba-4eec-9ca1-712e6330180e','creator-1','In conclusion, it is important to note that this analysis highlights the overall trend and furthermore supports a structured response.','under_review','2026-06-29T11:42:58.458615+00:00','2026-06-29T11:43:11.896958+00:00','71811c12-9097-49ba-9374-d6f08662e128');
INSERT INTO contents VALUES('53337f8b-a51e-44dd-8697-3f4dc537ed80','creator-2','I wrote this on the train after calling my sister. The second paragraph changed three times because I kept remembering details I almost forgot.','classified','2026-06-29T11:43:05.503138+00:00','2026-06-29T11:43:05.504639+00:00','aa66a33b-1d56-4625-8140-06b2ee949def');
INSERT INTO contents VALUES('23ca0e34-aa18-4063-ab87-4126c4cf8bd8','creator-42','In conclusion, it is important to note that this highlights the broader pattern overall.','under_review','2026-06-30T02:26:31.660528+00:00','2026-06-30T02:27:04.288462+00:00','65f6ab0e-5438-466e-893f-b13b165029be');
INSERT INTO contents VALUES('24758742-e090-4ed1-8ff6-4d3e99c49bb5','creator-99','I wrote this draft after dinner and revised two paragraphs this morning before class.','classified','2026-06-30T02:26:48.749263+00:00','2026-06-30T02:26:48.840103+00:00','20e56c60-f980-4f84-a20b-d70b96764678');
CREATE TABLE decisions (
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
INSERT INTO decisions VALUES('71811c12-9097-49ba-9374-d6f08662e128','20d2d201-e5ba-4eec-9ca1-712e6330180e','uncertain',0.4387499999999999733,0.4500000000000000111,'{"groqSignal": {"name": "groq_llama_3_3_70b", "model": "llama-3.3-70b-versatile", "available": false, "aiLikelihood": 0.5, "error": "GROQ_API_KEY is not set"}, "stylometricSignal": {"name": "stylometric_heuristics", "aiLikelihood": 0.45, "components": {"lexicalDiversityRisk": 0.0, "sentenceBurstinessRisk": 1.0}}, "weights": {"groq": 0.0, "stylometric": 1.0}}','Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: 44%). No enforcement action is taken while the decision is uncertain.','under_review','2026-06-29T11:42:58.459830+00:00');
INSERT INTO decisions VALUES('aa66a33b-1d56-4625-8140-06b2ee949def','53337f8b-a51e-44dd-8697-3f4dc537ed80','uncertain',0.4420312499999999867,0.4437499999999999778,'{"groqSignal": {"name": "groq_llama_3_3_70b", "model": "llama-3.3-70b-versatile", "available": false, "aiLikelihood": 0.5, "error": "GROQ_API_KEY is not set"}, "stylometricSignal": {"name": "stylometric_heuristics", "aiLikelihood": 0.44375, "components": {"lexicalDiversityRisk": 0.125, "sentenceBurstinessRisk": 0.8333333333333334}}, "weights": {"groq": 0.0, "stylometric": 1.0}}','Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: 44%). No enforcement action is taken while the decision is uncertain.','final','2026-06-29T11:43:05.504336+00:00');
INSERT INTO decisions VALUES('65f6ab0e-5438-466e-893f-b13b165029be','23ca0e34-aa18-4063-ab87-4126c4cf8bd8','uncertain',0.4387499999999999733,0.4500000000000000111,'{"groqSignal": {"name": "groq_llama_3_3_70b", "model": "llama-3.3-70b-versatile", "available": false, "aiLikelihood": 0.5, "error": "Groq HTTP error: 403"}, "stylometricSignal": {"name": "stylometric_heuristics", "aiLikelihood": 0.45, "components": {"lexicalDiversityRisk": 0.0, "sentenceBurstinessRisk": 1.0}}, "weights": {"groq": 0.0, "stylometric": 1.0}}','Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: 44%). No enforcement action is taken while the decision is uncertain.','under_review','2026-06-30T02:26:31.741065+00:00');
INSERT INTO decisions VALUES('20e56c60-f980-4f84-a20b-d70b96764678','24758742-e090-4ed1-8ff6-4d3e99c49bb5','uncertain',0.4181249999999999689,0.4892857142857142682,'{"groqSignal": {"name": "groq_llama_3_3_70b", "model": "llama-3.3-70b-versatile", "available": false, "aiLikelihood": 0.5, "error": "Groq HTTP error: 403"}, "stylometricSignal": {"name": "stylometric_heuristics", "aiLikelihood": 0.48928571428571427, "components": {"lexicalDiversityRisk": 0.0714285714285714, "sentenceBurstinessRisk": 1.0}}, "weights": {"groq": 0.0, "stylometric": 1.0}}','Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: 42%). No enforcement action is taken while the decision is uncertain.','final','2026-06-30T02:26:48.839283+00:00');
CREATE TABLE appeals (
                appeal_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                decision_id TEXT,
                creator_id TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
INSERT INTO appeals VALUES('435d6964-5122-4316-9b78-f858809c5bde','20d2d201-e5ba-4eec-9ca1-712e6330180e','71811c12-9097-49ba-9374-d6f08662e128','creator-1','This draft came from my notebook revisions and timestamped edits.','under_review','2026-06-29T11:43:11.896652+00:00');
INSERT INTO appeals VALUES('bfe9a718-217a-46d5-a6b3-745a666d39fe','23ca0e34-aa18-4063-ab87-4126c4cf8bd8','65f6ab0e-5438-466e-893f-b13b165029be','creator-42','This was drafted manually and I can provide revision history.','under_review','2026-06-30T02:27:04.287954+00:00');
CREATE TABLE audit_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                content_id TEXT NOT NULL,
                decision_id TEXT,
                appeal_id TEXT,
                timestamp TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
INSERT INTO audit_events VALUES('52bc2fe6-838e-4bc7-8cc9-0948f70ee8e7','classification_decision','20d2d201-e5ba-4eec-9ca1-712e6330180e','71811c12-9097-49ba-9374-d6f08662e128',NULL,'2026-06-29T11:42:58.460915+00:00','{"result": "uncertain", "confidence": 0.43875, "aiLikelihood": 0.45, "signals": {"groqSignal": {"name": "groq_llama_3_3_70b", "model": "llama-3.3-70b-versatile", "available": false, "aiLikelihood": 0.5, "error": "GROQ_API_KEY is not set"}, "stylometricSignal": {"name": "stylometric_heuristics", "aiLikelihood": 0.45, "components": {"lexicalDiversityRisk": 0.0, "sentenceBurstinessRisk": 1.0}}, "weights": {"groq": 0.0, "stylometric": 1.0}}, "labelText": "Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: 44%). No enforcement action is taken while the decision is uncertain."}');
INSERT INTO audit_events VALUES('37ce9fe2-805f-45af-bb08-68ce8a979ea8','classification_decision','53337f8b-a51e-44dd-8697-3f4dc537ed80','aa66a33b-1d56-4625-8140-06b2ee949def',NULL,'2026-06-29T11:43:05.505174+00:00','{"result": "uncertain", "confidence": 0.44203125, "aiLikelihood": 0.44375, "signals": {"groqSignal": {"name": "groq_llama_3_3_70b", "model": "llama-3.3-70b-versatile", "available": false, "aiLikelihood": 0.5, "error": "GROQ_API_KEY is not set"}, "stylometricSignal": {"name": "stylometric_heuristics", "aiLikelihood": 0.44375, "components": {"lexicalDiversityRisk": 0.125, "sentenceBurstinessRisk": 0.8333333333333334}}, "weights": {"groq": 0.0, "stylometric": 1.0}}, "labelText": "Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: 44%). No enforcement action is taken while the decision is uncertain."}');
INSERT INTO audit_events VALUES('476f19a5-a942-4abb-8d11-47d7d7a24711','appeal_submitted','20d2d201-e5ba-4eec-9ca1-712e6330180e','71811c12-9097-49ba-9374-d6f08662e128','435d6964-5122-4316-9b78-f858809c5bde','2026-06-29T11:43:11.898124+00:00','{"creatorId": "creator-1", "reasoning": "This draft came from my notebook revisions and timestamped edits.", "updatedContentStatus": "under_review"}');
INSERT INTO audit_events VALUES('fe8e3d4e-22ce-4acf-82ab-81cdfab3fd5a','classification_decision','23ca0e34-aa18-4063-ab87-4126c4cf8bd8','65f6ab0e-5438-466e-893f-b13b165029be',NULL,'2026-06-30T02:26:31.742644+00:00','{"result": "uncertain", "confidence": 0.43875, "aiLikelihood": 0.45, "signals": {"groqSignal": {"name": "groq_llama_3_3_70b", "model": "llama-3.3-70b-versatile", "available": false, "aiLikelihood": 0.5, "error": "Groq HTTP error: 403"}, "stylometricSignal": {"name": "stylometric_heuristics", "aiLikelihood": 0.45, "components": {"lexicalDiversityRisk": 0.0, "sentenceBurstinessRisk": 1.0}}, "weights": {"groq": 0.0, "stylometric": 1.0}}, "labelText": "Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: 44%). No enforcement action is taken while the decision is uncertain."}');
INSERT INTO audit_events VALUES('d2e44307-f790-44a4-98d6-9c5e7000ca5a','classification_decision','24758742-e090-4ed1-8ff6-4d3e99c49bb5','20e56c60-f980-4f84-a20b-d70b96764678',NULL,'2026-06-30T02:26:48.841143+00:00','{"result": "uncertain", "confidence": 0.41812499999999997, "aiLikelihood": 0.48928571428571427, "signals": {"groqSignal": {"name": "groq_llama_3_3_70b", "model": "llama-3.3-70b-versatile", "available": false, "aiLikelihood": 0.5, "error": "Groq HTTP error: 403"}, "stylometricSignal": {"name": "stylometric_heuristics", "aiLikelihood": 0.48928571428571427, "components": {"lexicalDiversityRisk": 0.0714285714285714, "sentenceBurstinessRisk": 1.0}}, "weights": {"groq": 0.0, "stylometric": 1.0}}, "labelText": "Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: 42%). No enforcement action is taken while the decision is uncertain."}');
INSERT INTO audit_events VALUES('a79082c6-aca8-4b54-b1ee-957d891317e8','appeal_submitted','23ca0e34-aa18-4063-ab87-4126c4cf8bd8','65f6ab0e-5438-466e-893f-b13b165029be','bfe9a718-217a-46d5-a6b3-745a666d39fe','2026-06-30T02:27:04.289267+00:00','{"creatorId": "creator-42", "reasoning": "This was drafted manually and I can provide revision history.", "updatedContentStatus": "under_review"}');
CREATE INDEX idx_contents_creator_id ON contents(creator_id);
CREATE INDEX idx_decisions_content_id ON decisions(content_id);
CREATE INDEX idx_appeals_content_id ON appeals(content_id);
CREATE INDEX idx_audit_events_content_id ON audit_events(content_id);
CREATE INDEX idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX idx_audit_events_timestamp ON audit_events(timestamp);
COMMIT;
