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
  customer_id  INTEGER PRIMARY KEY,
  full_name    VARCHAR NOT NULL,
  travel_type  VARCHAR NOT NULL DEFAULT 'leisure',  -- 'leisure' or 'business'
  loyalty_tier VARCHAR NOT NULL DEFAULT 'bronze'    -- 'bronze', 'silver', 'gold'
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
  children           INTEGER NOT NULL DEFAULT 0,
  booking_agent      VARCHAR NOT NULL DEFAULT 'chatgpt',    -- 'chatgpt', 'claude', 'gemini', 'llama'
  accommodation_type VARCHAR NOT NULL DEFAULT 'mid_orbit',  -- 'high_orbit', 'mid_orbit', 'low_orbit'
  food_plan          VARCHAR NOT NULL DEFAULT 'breakfast',   -- 'all_inclusive', 'breakfast', 'budget'
  promo_code     VARCHAR
);

CREATE TABLE IF NOT EXISTS payments (
  payment_id  INTEGER PRIMARY KEY DEFAULT nextval('payment_id_seq'),
  booking_id  INTEGER NOT NULL REFERENCES bookings(booking_id),
  paid_at     TIMESTAMP NOT NULL,
  amount_usd  INTEGER NOT NULL
);

CREATE SEQUENCE IF NOT EXISTS meal_order_id_seq START 1;

CREATE TABLE IF NOT EXISTS menu_items (
  item_id        INTEGER PRIMARY KEY,
  item_name      VARCHAR NOT NULL,
  category       VARCHAR NOT NULL,  -- appetizer, main, dessert, beverage
  cuisine        VARCHAR NOT NULL,  -- destination cuisine (lunar / martian / europan / universal)
  price_usd      DOUBLE NOT NULL,
  is_vegetarian  BOOLEAN NOT NULL DEFAULT false,
  spice_level    INTEGER NOT NULL DEFAULT 0  -- 0 (none) to 3 (extreme)
);

CREATE TABLE IF NOT EXISTS meal_orders (
  order_id    INTEGER PRIMARY KEY DEFAULT nextval('meal_order_id_seq'),
  booking_id  INTEGER NOT NULL REFERENCES bookings(booking_id),
  trip_day    INTEGER NOT NULL,    -- day 1, 2, 3... of the trip
  meal_type   VARCHAR NOT NULL,    -- breakfast, lunch, dinner
  item_id     INTEGER NOT NULL REFERENCES menu_items(item_id),
  quantity    INTEGER NOT NULL DEFAULT 1
);
