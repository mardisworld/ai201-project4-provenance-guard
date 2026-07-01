PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS contents (
    content_id TEXT PRIMARY KEY,
    creator_id TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('classified', 'under_review')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    latest_decision_id TEXT,
    FOREIGN KEY (latest_decision_id)
        REFERENCES decisions(decision_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    content_id TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('likely_ai', 'likely_human', 'uncertain')),
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    ai_likelihood REAL NOT NULL CHECK (ai_likelihood >= 0 AND ai_likelihood <= 1),
    signals_json TEXT NOT NULL,
    label_text TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('final', 'under_review')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (content_id)
        REFERENCES contents(content_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS appeals (
    appeal_id TEXT PRIMARY KEY,
    content_id TEXT NOT NULL,
    decision_id TEXT,
    creator_id TEXT NOT NULL,
    creator_reasoning TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('under_review', 'resolved', 'rejected')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (content_id)
        REFERENCES contents(content_id)
        ON DELETE CASCADE,
    FOREIGN KEY (decision_id)
        REFERENCES decisions(decision_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    content_id TEXT NOT NULL,
    creator_id TEXT,
    timestamp TEXT NOT NULL,
    attribution TEXT,
    confidence REAL,
    llm_score REAL,
    stylometric_score REAL,
    status TEXT CHECK (status IN ('final', 'under_review', 'classified')),
    decision_id TEXT,
    appeal_id TEXT,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (content_id)
        REFERENCES contents(content_id)
        ON DELETE CASCADE,
    FOREIGN KEY (decision_id)
        REFERENCES decisions(decision_id)
        ON DELETE SET NULL,
    FOREIGN KEY (appeal_id)
        REFERENCES appeals(appeal_id)
        ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_contents_creator_id ON contents(creator_id);
CREATE INDEX IF NOT EXISTS idx_decisions_content_id ON decisions(content_id);
CREATE INDEX IF NOT EXISTS idx_appeals_content_id ON appeals(content_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_content_id ON audit_events(content_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp);
