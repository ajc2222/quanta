-- 20260709000010_po3_phase_labels.sql
CREATE TABLE po3_phase_labels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    po3_instance_id UUID NOT NULL REFERENCES po3_instances(id) ON DELETE CASCADE,
    confirmed_phase TEXT NOT NULL CHECK (confirmed_phase IN ('bullish', 'bearish', 'exclude')),
    admin_user_id   UUID NOT NULL REFERENCES admin_users(id),
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (po3_instance_id)
);

CREATE INDEX idx_po3_labels_instance ON po3_phase_labels (po3_instance_id);
