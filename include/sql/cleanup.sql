-- Drop everything so the åsetup Dag can rebuild the database from scratch on every run.

-- Feature tables
DROP TABLE IF EXISTS ai_features;
DROP TABLE IF EXISTS spend_features;
DROP TABLE IF EXISTS spend_labels;

-- Spend-model inference / scoring outputs (reference customers, so drop before them)
DROP TABLE IF EXISTS spend_predictions;
DROP TABLE IF EXISTS customer_spend_estimates;
DROP TABLE IF EXISTS prospective_trips;

-- MLOps tracking
DROP TABLE IF EXISTS ml_plots;
DROP TABLE IF EXISTS ml_models;
DROP TABLE IF EXISTS ml_runs;
DROP TABLE IF EXISTS ml_experiments;

-- AI / context engineering
DROP TABLE IF EXISTS context_graph;
DROP TABLE IF EXISTS decision_traces;
DROP TABLE IF EXISTS context_units;

-- Email exchange
DROP TABLE IF EXISTS email_messages;
DROP TABLE IF EXISTS email_threads;

-- Food orders
DROP TABLE IF EXISTS cosmarket_orders;
DROP TABLE IF EXISTS meal_orders;
DROP TABLE IF EXISTS menu_items;

-- Core AstroTrips tables
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS promo_codes;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS planets;

-- Sequences
DROP SEQUENCE IF EXISTS email_message_id_seq;
DROP SEQUENCE IF EXISTS email_thread_id_seq;
DROP SEQUENCE IF EXISTS cosmarket_order_id_seq;
DROP SEQUENCE IF EXISTS meal_order_id_seq;
DROP SEQUENCE IF EXISTS payment_id_seq;
DROP SEQUENCE IF EXISTS booking_id_seq;