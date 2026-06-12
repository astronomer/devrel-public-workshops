INSERT INTO customers (customer_id, full_name, home_planet_id)
SELECT
  2000 + i,
  CASE 2000 + i
    WHEN 2001 THEN 'James Kirk'
    WHEN 2002 THEN 'Jean-Luc Picard'
    WHEN 2003 THEN 'Benjamin Sisko'
    WHEN 2004 THEN 'Jonathan Archer'
    WHEN 2005 THEN 'Kathryn Janeway'
    WHEN 2006 THEN 'Spock'
    WHEN 2007 THEN 'William Riker'
    WHEN 2008 THEN 'T''Pol'
    WHEN 2009 THEN 'Kira Nerys'
    WHEN 2010 THEN 'Chakotay'
    ELSE (['Alex','Jordan','Sam','Taylor','Morgan','Casey','Riley','Quinn','Avery','Nova'])[1 + (i % 10)]
         || ' ' ||
         (['Nakamura','Osei','Park','Russo','Singh','Torres','Ueda','Volkov','Williams','Zhang'])[1 + ((i // 10) % 10)]
  END,
  CASE WHEN 2000 + i IN (2001, 2007) THEN 1001 ELSE 1001 + (i % 5) END  -- Kirk (2001) and Riker (2007) live on the Moon
FROM generate_series(1, 500) AS t(i);

-- Bookings.
INSERT INTO bookings (customer_id, route_id, booked_at, departure_date, return_date, passengers, promo_code)
SELECT
  2000 + ((i * 7) % 500) + 1,
  1001 + (i % 5),
  TIMESTAMP '2025-01-01 08:00:00' + INTERVAL (i * 6) HOUR,
  (TIMESTAMP '2025-01-01 08:00:00' + INTERVAL (i * 6) HOUR + INTERVAL (14 + (i % 150)) DAY)::DATE,
  (TIMESTAMP '2025-01-01 08:00:00' + INTERVAL (i * 6) HOUR + INTERVAL (14 + (i % 150)) DAY + INTERVAL (3 + (i % 28)) DAY)::DATE,
  1 + (i % 4),
  CASE WHEN i % 7 = 0 THEN (['ASTRO10','ASTRO20','LUNAR15','MARS25','EXPLORER5'])[1 + (i % 5)] ELSE NULL END
FROM generate_series(1, 2500) AS t(i);


INSERT INTO payments (booking_id, paid_at, amount_usd)
SELECT
  b.booking_id,
  b.booked_at + INTERVAL 15 MINUTE,
  GREATEST(100, CAST(
    r.base_fare_usd * b.passengers * p.base_multiplier * (1 - COALESCE(pc.discount_pct, 0))
  AS INTEGER))
FROM bookings b
JOIN routes r ON b.route_id = r.route_id
JOIN planets p ON r.destination_id = p.planet_id
LEFT JOIN promo_codes pc ON b.promo_code = pc.promo_code;


INSERT INTO meal_orders (booking_id, customer_id, item_id, quantity)
SELECT booking_id, customer_id, 1  + (hash(booking_id)      % 4),
       passengers * GREATEST(1, (return_date - departure_date) // 4) FROM bookings;
INSERT INTO meal_orders (booking_id, customer_id, item_id, quantity)
SELECT booking_id, customer_id, 11 + (hash(booking_id * 3)  % 5),
       passengers * GREATEST(1, (return_date - departure_date) // 4) FROM bookings;
INSERT INTO meal_orders (booking_id, customer_id, item_id, quantity)
SELECT booking_id, customer_id, 21 + (hash(booking_id * 7)  % 5),
       passengers * GREATEST(1, (return_date - departure_date) // 6) FROM bookings;
INSERT INTO meal_orders (booking_id, customer_id, item_id, quantity)
SELECT booking_id, customer_id, 31 + (hash(booking_id * 11) % 4),
       passengers * GREATEST(1, (return_date - departure_date) // 3) FROM bookings;


-- Latent "occasion" disposition ((booking_id * 17) % 3 = 0/1/2), carried by item 25
-- as a clean per-pp-per-day amount (occ * weight). The AI budget_signal observes
-- this same latent in feature_engineering_ai. It uses plain arithmetic, not hash(),
-- so the demo-safe Python backfill there can reproduce it exactly. The deterministic
-- features cannot see it, so it is the variance the +AI rung explains on top of the
-- deterministic baseline. Not derived from the spend outcome (latent -> spend and
-- latent -> budget_signal), so no leakage.
INSERT INTO meal_orders (booking_id, customer_id, item_id, quantity)
SELECT booking_id, customer_id, 25,
       GREATEST(0, CAST(
         ((booking_id * 17) % 3) * 6.0
           * passengers * (return_date - departure_date) / 5.0
       AS INTEGER))
FROM bookings;


INSERT INTO cosmarket_orders (customer_id, item_id, ordered_at, quantity)
SELECT
  c.customer_id,
  CASE
    WHEN (hash(c.customer_id * 5 + s.k) % 3) = 0
      THEN (CASE (hash(c.customer_id * 9 + s.k) % 3)
              WHEN 0 THEN 1  + (hash(c.customer_id + s.k) % 4)   -- appetizer 1-4
              WHEN 1 THEN 11 + (hash(c.customer_id + s.k) % 5)   -- main 11-15
              ELSE        31 + (hash(c.customer_id + s.k) % 4)   -- beverage 31-34
            END)
    ELSE 21 + (hash(c.customer_id + s.k) % 5)                    -- dessert 21-25
  END,
  TIMESTAMP '2025-01-01 12:00:00' + INTERVAL (hash(c.customer_id * 7 + s.k) % 500) DAY,
  1 + (hash(c.customer_id * 3 + s.k) % 3)
FROM customers c
CROSS JOIN (SELECT unnest([1, 2, 3, 4, 5]) AS k) s
WHERE c.customer_id <> 2007;  -- Riker is pure Ktarian Chocolate Puff, seeded below

-- Riker (2007) buys nothing but Ktarian Chocolate Puffs (item 21): an unmistakable
-- single-dessert signal for the context-layer personalization, and a clean lift to
-- his deterministic spend signal. Excluded from the varied orders above; this block
-- is sized to keep his total CosMarket spend in the same range it had before.
INSERT INTO cosmarket_orders (customer_id, item_id, ordered_at, quantity)
SELECT 2007, 21, TIMESTAMP '2025-06-01 12:00:00' + INTERVAL (k * 30) DAY, 2
FROM generate_series(1, 10) AS t(k);

-- Deterministic spend signal: food spend per day per person rises with the
-- customer's CosMarket dessert affinity and average item price, when they travel
-- to their home planet, and for Titan/Europa residents (sparse local food, so they
-- stock up). Quantity is back-solved so this extra serving adds the weighted signal
-- (USD/pp/day) after the per-pp-per-day normalization; item 25 (Sweet Kibble, $5)
-- is the carrier. This is what gives the deterministic baseline its predictive R^2.
INSERT INTO meal_orders (booking_id, customer_id, item_id, quantity)
SELECT
  b.booking_id, b.customer_id, 25,
  GREATEST(0, CAST(
    (  cm.dessert_share * 28.0
     + cm.avg_price * 1.00
     + (CASE WHEN c.home_planet_id = r.destination_id THEN 15.0 ELSE 0.0 END)
     + (CASE WHEN ph.planet_name IN ('Titan', 'Europa') THEN 9.0 ELSE 0.0 END)
    ) * b.passengers * (b.return_date - b.departure_date) / 5.0
  AS INTEGER))
FROM bookings b
JOIN customers c ON b.customer_id = c.customer_id
JOIN routes r ON b.route_id = r.route_id
JOIN planets ph ON c.home_planet_id = ph.planet_id
JOIN (
  SELECT co.customer_id,
         SUM(co.quantity * mi.price_usd) / NULLIF(SUM(co.quantity), 0) AS avg_price,
         SUM(CASE WHEN mi.category = 'dessert' THEN co.quantity ELSE 0 END)::DOUBLE
           / NULLIF(SUM(co.quantity), 0) AS dessert_share
  FROM cosmarket_orders co
  JOIN menu_items mi ON co.item_id = mi.item_id
  GROUP BY co.customer_id
) cm ON b.customer_id = cm.customer_id;

-- NOTE: ai_features is an engineered feature table. It is populated by the
-- feature_engineering_ai Dag (not here), so AI features only exist after the
-- participant runs that Dag. budget_signal there observes the latent occasion above.

-- Prospective trips: existing customers who have not emailed, each with a
-- proposed trip, so spend_inference can proactively price their food spend in batch mode.
INSERT INTO prospective_trips (customer_id, destination, passengers, trip_length_days) VALUES
(2002, 'Titan',  2, 21),
(2003, 'Europa', 4, 14),
(2004, 'Venus',  2,  9),
(2005, 'Mars',   1, 30),
(2006, 'Venus',  2,  7),
(2007, 'Moon',   6,  4),
(2008, 'Mars',   3, 12),
(2009, 'Europa', 2, 16),
(2010, 'Titan',  3, 18);