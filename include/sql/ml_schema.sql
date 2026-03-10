CREATE TABLE IF NOT EXISTS ml_experiments (
  experiment_id   INTEGER PRIMARY KEY,
  experiment_name VARCHAR NOT NULL UNIQUE,
  description     VARCHAR,
  created_at      TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS ml_runs (
  run_id          INTEGER PRIMARY KEY,
  experiment_id   INTEGER NOT NULL REFERENCES ml_experiments(experiment_id),
  run_number      INTEGER NOT NULL,
  dag_id          VARCHAR NOT NULL,
  task_id         VARCHAR NOT NULL,
  run_ts          TIMESTAMP DEFAULT current_timestamp,
  status          VARCHAR NOT NULL DEFAULT 'RUNNING',
  hyperparameters VARCHAR,
  metrics         VARCHAR,
  tags            VARCHAR
);

CREATE TABLE IF NOT EXISTS ml_models (
  model_name      VARCHAR NOT NULL,
  model_version   INTEGER NOT NULL,
  run_id          INTEGER NOT NULL REFERENCES ml_runs(run_id),
  model_type      VARCHAR NOT NULL,
  model_blob      VARCHAR NOT NULL,
  stage           VARCHAR NOT NULL DEFAULT 'development',
  registered_at   TIMESTAMP DEFAULT current_timestamp,
  PRIMARY KEY (model_name, model_version)
);

CREATE TABLE IF NOT EXISTS ml_plots (
  plot_id         INTEGER PRIMARY KEY,
  run_id          INTEGER NOT NULL REFERENCES ml_runs(run_id),
  plot_name       VARCHAR NOT NULL,
  plot_type       VARCHAR NOT NULL,
  plot_data       VARCHAR NOT NULL,
  created_at      TIMESTAMP DEFAULT current_timestamp
);
