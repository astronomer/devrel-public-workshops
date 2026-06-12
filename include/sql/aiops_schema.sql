CREATE TABLE IF NOT EXISTS context_units (
  chunk_id            VARCHAR PRIMARY KEY,              -- UUID, also embedded in the body
  created_at          TIMESTAMP DEFAULT current_timestamp,
  updated_at          TIMESTAMP DEFAULT current_timestamp,
  version             INTEGER NOT NULL DEFAULT 1,       -- incremented on each write
  source_type         VARCHAR,                          -- where this unit came from (Human, AI, etc)
  valid_until         TIMESTAMP,                        -- optional TTL
  supersedes          VARCHAR,                          -- older chunk_id this replaces
  superseded_by       VARCHAR,                          -- newer chunk_id that replaced this
  chunk_type          VARCHAR NOT NULL,                 -- informational / instructional / actionable
  tokens              INTEGER,                          -- precomputed token count
  title               VARCHAR,
  checksum            VARCHAR,                          -- hash of the body, for integrity/dedup
  embedding_model     VARCHAR,                          -- model that produced the embedding
  body                VARCHAR,                          -- markdown/JSON, wrapped in <chunk id=...> tags
  source_uri          VARCHAR,                          -- link to raw source kept for audit / exact-quote
  context_prefix      VARCHAR,                          -- AI: 1-2 sentence note situating the chunk in its document
  embedding           FLOAT[],                          -- vector column (list_cosine_similarity)
  contradiction_flags VARCHAR[],                        -- ContextOps: set by evaluation agent 
  missing_flags       VARCHAR[],                        -- ContextOps: set by evaluation agent
  archived            BOOLEAN NOT NULL DEFAULT false    -- archived units excluded from retrieval
);

CREATE TABLE IF NOT EXISTS decision_traces (
  trace_id          VARCHAR PRIMARY KEY,
  entity_references JSON,                               -- customer / thread / turn ids
  inputs            JSON,                               -- the prospect request that opened the decision
  context_used      JSON,                               -- list of context unit chunk_ids the drafter used
  steps             JSON,                               -- ordered; each step has decision_maker/logic/output
  outcome           JSON                                -- pending until the booking result is known
);


CREATE TABLE IF NOT EXISTS context_graph (
  graph_id          VARCHAR PRIMARY KEY,
  decision_group    VARCHAR NOT NULL,                   -- business process / product type / customer key
  member_trace_ids  JSON,                               -- traces stitched into this group
  precedent_summary VARCHAR,                            -- retrievable precedent text fed back to the agent
  stats             JSON,                               -- aggregate signals (counts, avg discount, outcomes)
  created_at        TIMESTAMP DEFAULT current_timestamp,
  updated_at        TIMESTAMP DEFAULT current_timestamp
);


