CREATE SEQUENCE IF NOT EXISTS booking_id_seq START 1;
CREATE SEQUENCE IF NOT EXISTS payment_id_seq START 1;

CREATE TABLE IF NOT EXISTS planets (
  planet_id       INTEGER PRIMARY KEY,
  planet_name     VARCHAR NOT NULL,
  base_multiplier DOUBLE NOT NULL -- cost multiplier for trips to this planet (e.g. higher landing difficulty)
);

CREATE TABLE IF NOT EXISTS routes (
  route_id       INTEGER PRIMARY KEY,
  destination_id INTEGER NOT NULL REFERENCES planets(planet_id),
  base_fare_usd  INTEGER NOT NULL -- costs for the journey to this route's destination
);

CREATE TABLE IF NOT EXISTS customers (
  customer_id    INTEGER PRIMARY KEY,
  full_name      VARCHAR NOT NULL,
  home_planet_id INTEGER REFERENCES planets(planet_id)  -- which planet the customer lives on (personalization)
);

CREATE TABLE IF NOT EXISTS promo_codes (
  promo_code    VARCHAR PRIMARY KEY,
  discount_pct  DOUBLE NOT NULL -- 0.10 = 10%
);

CREATE TABLE IF NOT EXISTS bookings (
  booking_id     INTEGER PRIMARY KEY DEFAULT nextval('booking_id_seq'),
  customer_id    INTEGER NOT NULL REFERENCES customers(customer_id),
  route_id       INTEGER NOT NULL REFERENCES routes(route_id),
  booked_at      TIMESTAMP NOT NULL,
  departure_date DATE NOT NULL,
  return_date    DATE NOT NULL,
  passengers     INTEGER NOT NULL,
  promo_code     VARCHAR
);

CREATE TABLE IF NOT EXISTS payments (
  payment_id  INTEGER PRIMARY KEY DEFAULT nextval('payment_id_seq'),
  booking_id  INTEGER NOT NULL REFERENCES bookings(booking_id),
  paid_at     TIMESTAMP NOT NULL,
  amount_usd  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS menu_items (
  item_id        INTEGER PRIMARY KEY,
  item_name      VARCHAR NOT NULL,
  category       VARCHAR NOT NULL,  -- appetizer, main, dessert, beverage
  price_usd      DOUBLE NOT NULL,
  is_vegetarian  BOOLEAN NOT NULL DEFAULT false,
  spice_level    INTEGER NOT NULL DEFAULT 0  -- 0 (none) to 3 (extreme)
);

CREATE SEQUENCE IF NOT EXISTS meal_order_id_seq START 1;
CREATE TABLE IF NOT EXISTS meal_orders (
  order_id    INTEGER PRIMARY KEY DEFAULT nextval('meal_order_id_seq'),
  booking_id  INTEGER NOT NULL REFERENCES bookings(booking_id),
  customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
  item_id     INTEGER NOT NULL REFERENCES menu_items(item_id),
  quantity    INTEGER NOT NULL DEFAULT 1
);

CREATE SEQUENCE IF NOT EXISTS cosmarket_order_id_seq START 1;
CREATE TABLE IF NOT EXISTS cosmarket_orders (
  order_id     INTEGER PRIMARY KEY DEFAULT nextval('cosmarket_order_id_seq'),
  customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),  -- delivered to the customer's home planet
  item_id      INTEGER NOT NULL REFERENCES menu_items(item_id),
  ordered_at   TIMESTAMP NOT NULL,
  quantity     INTEGER NOT NULL DEFAULT 1
);

CREATE SEQUENCE IF NOT EXISTS email_thread_id_seq START 1;
CREATE TABLE IF NOT EXISTS email_threads (
  thread_id    INTEGER PRIMARY KEY DEFAULT nextval('email_thread_id_seq'),
  customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),  -- prospect is a known customer (personalization)
  subject      VARCHAR NOT NULL,
  booking_id   INTEGER REFERENCES bookings(booking_id),  -- sequence outcome: the booking it converted to; NULL = no booking
  created_at   TIMESTAMP DEFAULT current_timestamp,
  updated_at   TIMESTAMP DEFAULT current_timestamp
);

CREATE SEQUENCE IF NOT EXISTS email_message_id_seq START 1;
CREATE TABLE IF NOT EXISTS email_messages (
  message_id   INTEGER PRIMARY KEY DEFAULT nextval('email_message_id_seq'),
  thread_id    INTEGER NOT NULL REFERENCES email_threads(thread_id),
  turn         INTEGER NOT NULL,   -- 1, 2, 3, ... order within the thread
  direction    VARCHAR NOT NULL,   -- 'inbound' (prospect) / 'outbound' (agent)
  sender       VARCHAR NOT NULL,   -- address shown in the inbox
  body         VARCHAR NOT NULL,
  created_at   TIMESTAMP DEFAULT current_timestamp
);