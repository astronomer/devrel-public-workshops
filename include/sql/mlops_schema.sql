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

CREATE TABLE IF NOT EXISTS spend_features (
  booking_id                  INTEGER PRIMARY KEY REFERENCES bookings(booking_id),
  passengers                  INTEGER NOT NULL,
  trip_length_days            INTEGER NOT NULL,
  destination_planet          VARCHAR NOT NULL,
  dest_base_multiplier        DOUBLE  NOT NULL,
  route_base_fare_usd         INTEGER NOT NULL,
  fare_per_person_per_day     DOUBLE  NOT NULL,
  home_planet                 VARCHAR,
  home_base_multiplier        DOUBLE,
  is_traveling_to_home_planet BOOLEAN,
  cosmarket_order_count       INTEGER NOT NULL DEFAULT 0,
  cosmarket_avg_item_price    DOUBLE,
  cosmarket_total_home_spend  DOUBLE  NOT NULL DEFAULT 0,
  cosmarket_dessert_share     DOUBLE,
  cosmarket_avg_spice_level   DOUBLE,
  cosmarket_veg_share         DOUBLE
);

CREATE TABLE IF NOT EXISTS spend_labels (
  booking_id                  INTEGER PRIMARY KEY REFERENCES bookings(booking_id),
  food_spend_pp_pd            DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_features (
  booking_id     INTEGER PRIMARY KEY REFERENCES bookings(booking_id),
  trip_occasion  VARCHAR NOT NULL,
  enthusiasm     VARCHAR NOT NULL,
  budget_signal  VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS spend_predictions (
  dag_run_id        VARCHAR PRIMARY KEY,            -- the spend_inference run that produced this estimate
  prospect          VARCHAR,                        -- JSON conf the agent passed
  food_spend_pp_pd  DOUBLE,                          -- predicted food spend per person per day (USD)
  model_name        VARCHAR,
  model_version     INTEGER,
  created_at        TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS prospective_trips (
  customer_id       INTEGER PRIMARY KEY REFERENCES customers(customer_id),  -- existing customer not yet scored
  destination       VARCHAR NOT NULL,                                       -- planet name of the proposed trip
  passengers        INTEGER NOT NULL,
  trip_length_days  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS customer_spend_estimates (
  customer_id       INTEGER PRIMARY KEY REFERENCES customers(customer_id),
  food_spend_pp_pd  DOUBLE,                                                 -- batch-scored estimate (USD pp/day)
  model_name        VARCHAR,
  model_version     INTEGER,
  created_at        TIMESTAMP DEFAULT current_timestamp
);