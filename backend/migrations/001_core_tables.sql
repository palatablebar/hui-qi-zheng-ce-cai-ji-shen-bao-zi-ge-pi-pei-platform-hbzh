-- 核心表结构参考（PostgreSQL 语法，运行时不执行；建表由 SQLAlchemy create_all 完成）

CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(160) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    display_name    VARCHAR(80)  NOT NULL,
    role            VARCHAR(20)  NOT NULL,
    org             VARCHAR(120),
    created_at      TIMESTAMP    NOT NULL
);

CREATE TABLE policies (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(40)  NOT NULL UNIQUE,
    title           VARCHAR(200) NOT NULL,
    issuer          VARCHAR(120) NOT NULL,
    doc_no          VARCHAR(80)  NOT NULL DEFAULT '',
    source_kind     VARCHAR(20)  NOT NULL DEFAULT 'website',
    source_name     VARCHAR(120) NOT NULL DEFAULT '',
    published_on    DATE,
    deadline        DATE,
    fund_cap_wan    INTEGER,
    original_text   TEXT,
    status          VARCHAR(12)  NOT NULL DEFAULT 'active',
    seed_key        VARCHAR(120) UNIQUE,
    created_at      TIMESTAMP    NOT NULL,
    updated_at      TIMESTAMP    NOT NULL
);

CREATE TABLE rules (
    id                  SERIAL PRIMARY KEY,
    policy_id           INTEGER NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    field               VARCHAR(24) NOT NULL,
    op                  VARCHAR(8)  NOT NULL,
    value               VARCHAR(64) NOT NULL,
    unit                VARCHAR(16) NOT NULL DEFAULT '',
    required            BOOLEAN     NOT NULL DEFAULT TRUE,
    confidence          DOUBLE PRECISION NOT NULL DEFAULT 0.9,
    evidence_sentence   TEXT,
    seed_key            VARCHAR(120) UNIQUE,
    created_at          TIMESTAMP   NOT NULL,
    CONSTRAINT uq_rules_policy_condition UNIQUE (policy_id, field, op, value)
);

CREATE TABLE companies (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(40)  NOT NULL UNIQUE,
    name            VARCHAR(160) NOT NULL,
    industry        VARCHAR(40)  NOT NULL,
    district        VARCHAR(24)  NOT NULL,
    revenue_wan     DOUBLE PRECISION NOT NULL DEFAULT 0,
    rd_ratio        DOUBLE PRECISION NOT NULL DEFAULT 0,
    employees       INTEGER      NOT NULL DEFAULT 0,
    qualifications  JSON,
    contact         VARCHAR(40)  NOT NULL DEFAULT '',
    owner           VARCHAR(80)  NOT NULL DEFAULT '',
    seed_key        VARCHAR(120) UNIQUE,
    created_at      TIMESTAMP    NOT NULL,
    updated_at      TIMESTAMP    NOT NULL
);

CREATE TABLE match_runs (
    id              SERIAL PRIMARY KEY,
    run_no          VARCHAR(40)  NOT NULL UNIQUE,
    trigger         VARCHAR(20)  NOT NULL DEFAULT 'manual',
    status          VARCHAR(20)  NOT NULL DEFAULT 'queued',
    operator_email  VARCHAR(160) NOT NULL,
    policy_count    INTEGER      NOT NULL DEFAULT 0,
    company_count   INTEGER      NOT NULL DEFAULT 0,
    match_count     INTEGER      NOT NULL DEFAULT 0,
    p0_count        INTEGER      NOT NULL DEFAULT 0,
    params          JSON,
    metrics         JSON,
    log_text        TEXT,
    seed_key        VARCHAR(120) UNIQUE,
    started_at      TIMESTAMP    NOT NULL,
    finished_at     TIMESTAMP
);

CREATE TABLE matches (
    id              SERIAL PRIMARY KEY,
    run_id          INTEGER NOT NULL REFERENCES match_runs(id) ON DELETE CASCADE,
    policy_id       INTEGER NOT NULL REFERENCES policies(id) ON DELETE CASCADE,
    company_id      INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    score           DOUBLE PRECISION NOT NULL DEFAULT 0,
    hard_pass       BOOLEAN  NOT NULL DEFAULT FALSE,
    gaps            JSON,
    priority        VARCHAR(4)  NOT NULL DEFAULT 'P2',
    status          VARCHAR(16) NOT NULL DEFAULT 'pending',
    reviewer        VARCHAR(160),
    note            TEXT,
    payload         JSON,
    created_at      TIMESTAMP NOT NULL,
    updated_at      TIMESTAMP NOT NULL,
    CONSTRAINT uq_matches_run_pair UNIQUE (run_id, policy_id, company_id)
);

CREATE TABLE audit_logs (
    id              SERIAL PRIMARY KEY,
    actor_email     VARCHAR(160) NOT NULL,
    actor_role      VARCHAR(20)  NOT NULL,
    action          VARCHAR(64)  NOT NULL,
    entity          VARCHAR(40)  NOT NULL,
    entity_id       VARCHAR(64),
    detail          JSON,
    layer           VARCHAR(16)  NOT NULL DEFAULT 'domain',
    ip              VARCHAR(64),
    seed_key        VARCHAR(120) UNIQUE,
    created_at      TIMESTAMP    NOT NULL
);
