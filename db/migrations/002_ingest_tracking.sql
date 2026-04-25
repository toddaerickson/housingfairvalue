CREATE TABLE ingest_run (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    since_date     DATE NOT NULL,
    rows_obs       INT NOT NULL DEFAULT 0,
    rows_fact      INT NOT NULL DEFAULT 0,
    status         TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'ok', 'no_data', 'error')),
    error_detail   TEXT
);

CREATE INDEX ingest_run_started_idx ON ingest_run (started_at DESC);
