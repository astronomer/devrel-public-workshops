-- Generate ML-ready data with learnable patterns for AstroTrips.
-- Patterns baked in:
--   - Price depends on route, passengers, season, and advance booking (regression target)
--   - Promo code usage correlates with repeat customers and longer trips (classification target)
--   - Customer segments: budget travelers (Moon), adventurers (Mars), luxury (Europa) (clustering target)

-- Additional planets and routes for variety
INSERT OR IGNORE INTO planets VALUES (1004, 'Titan', 2.00);
INSERT OR IGNORE INTO planets VALUES (1005, 'Venus', 1.10);
INSERT OR IGNORE INTO routes VALUES (1004, 1004, 55000);
INSERT OR IGNORE INTO routes VALUES (1005, 1005, 15000);

-- Generate 500 customers (IDs 2001-2500)
-- ~30% business travelers, rest leisure
-- loyalty: ~15% gold, ~30% silver, ~55% bronze
INSERT INTO customers (customer_id, full_name, travel_type, loyalty_tier)
SELECT
  2000 + i AS customer_id,
  CASE (i % 20)
    WHEN 0 THEN 'Alex' WHEN 1 THEN 'Jordan' WHEN 2 THEN 'Sam'
    WHEN 3 THEN 'Taylor' WHEN 4 THEN 'Morgan' WHEN 5 THEN 'Casey'
    WHEN 6 THEN 'Riley' WHEN 7 THEN 'Quinn' WHEN 8 THEN 'Avery'
    WHEN 9 THEN 'Blake' WHEN 10 THEN 'Dakota' WHEN 11 THEN 'Ellis'
    WHEN 12 THEN 'Frankie' WHEN 13 THEN 'Harper' WHEN 14 THEN 'Indigo'
    WHEN 15 THEN 'Jules' WHEN 16 THEN 'Kendall' WHEN 17 THEN 'Lane'
    WHEN 18 THEN 'Marley' WHEN 19 THEN 'Nova'
  END || ' ' ||
  CASE (i % 15)
    WHEN 0 THEN 'Nakamura' WHEN 1 THEN 'Osei' WHEN 2 THEN 'Park'
    WHEN 3 THEN 'Russo' WHEN 4 THEN 'Singh' WHEN 5 THEN 'Torres'
    WHEN 6 THEN 'Ueda' WHEN 7 THEN 'Volkov' WHEN 8 THEN 'Williams'
    WHEN 9 THEN 'Xu' WHEN 10 THEN 'Yamamoto' WHEN 11 THEN 'Zhang'
    WHEN 12 THEN 'Ali' WHEN 13 THEN 'Bergman' WHEN 14 THEN 'Costa'
  END AS full_name,
  CASE WHEN i % 10 < 3 THEN 'business' ELSE 'leisure' END AS travel_type,
  CASE
    WHEN i % 20 < 3  THEN 'gold'
    WHEN i % 20 < 9  THEN 'silver'
    ELSE 'bronze'
  END AS loyalty_tier
FROM generate_series(1, 500) AS t(i);

-- Additional promo codes
INSERT OR IGNORE INTO promo_codes VALUES ('LUNAR15', 0.15);
INSERT OR IGNORE INTO promo_codes VALUES ('MARS25', 0.25);
INSERT OR IGNORE INTO promo_codes VALUES ('EXPLORER5', 0.05);

-- Generate ~2500 bookings with deliberate patterns
-- Pattern: customer_id % 5 drives segment behavior:
--   0-1: budget (prefer Moon/Venus, short trips, rarely use promos)
--   2-3: adventurer (prefer Mars/Europa, medium trips, sometimes use promos)
--   4:   luxury (prefer Europa/Titan, long trips, frequently use promos)
INSERT INTO bookings (customer_id, route_id, booked_at, departure_date, return_date, passengers, children, booking_agent, accommodation_type, food_plan, promo_code)
SELECT
  customer_id,
  route_id,
  booked_at,
  departure_date,
  departure_date + trip_days::INTEGER AS return_date,
  passengers,
  children,
  booking_agent,
  accommodation_type,
  food_plan,
  promo_code
FROM (
  SELECT
    2000 + ((b.i * 7 + 3) % 500) + 1 AS customer_id,

    -- Route selection: segment-driven with noise
    CASE
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (0, 1) THEN
        CASE WHEN b.i % 7 < 5 THEN (CASE WHEN b.i % 2 = 0 THEN 1001 ELSE 1005 END)
             ELSE 1002 END
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (2, 3) THEN
        CASE WHEN b.i % 5 < 3 THEN 1002
             WHEN b.i % 5 = 3 THEN 1003
             ELSE 1001 END
      ELSE
        CASE WHEN b.i % 4 < 2 THEN 1003
             WHEN b.i % 4 = 2 THEN 1004
             ELSE 1002 END
    END AS route_id,

    -- Booking timestamp spread over 18 months
    TIMESTAMP '2025-01-01 08:00:00' + INTERVAL (b.i * 4 + (b.i % 17)) HOUR AS booked_at,

    -- Departure 14-180 days after booking, season pattern
    (TIMESTAMP '2025-01-01 08:00:00' + INTERVAL (b.i * 4 + (b.i % 17)) HOUR +
     INTERVAL (14 + (b.i % 13) * 13) DAY)::DATE AS departure_date,

    -- Trip duration: budget=short, luxury=long
    CASE
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (0, 1) THEN 2 + (b.i % 5)
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (2, 3) THEN 7 + (b.i % 14)
      ELSE 14 + (b.i % 30)
    END AS trip_days,

    -- Passengers: budget=1-2, adventurer=1-3, luxury=1-4
    CASE
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (0, 1) THEN 1 + (b.i % 2)
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (2, 3) THEN 1 + (b.i % 3)
      ELSE 1 + (b.i % 4)
    END AS passengers,

    -- Children: business travelers never bring kids;
    -- ~25% of leisure bookings with 2+ passengers have 1-2 kids
    CASE
      WHEN (((b.i * 7 + 3) % 500) + 1) % 10 < 3 THEN 0  -- business
      WHEN (1 + CASE
              WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (0, 1) THEN (b.i % 2)
              WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (2, 3) THEN (b.i % 3)
              ELSE (b.i % 4)
            END) >= 3
        AND b.i % 3 = 0 THEN 2
      WHEN (1 + CASE
              WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (0, 1) THEN (b.i % 2)
              WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (2, 3) THEN (b.i % 3)
              ELSE (b.i % 4)
            END) >= 2
        AND b.i % 4 = 0 THEN 1
      ELSE 0
    END AS children,

    -- AI booking agent: correlates with customer personality
    -- business → gemini (corporate), gold → chatgpt (mainstream loyal),
    -- adventurer → claude, budget → llama
    CASE
      WHEN (((b.i * 7 + 3) % 500) + 1) % 10 < 3 THEN  -- business customers
        CASE b.i % 10
          WHEN 0 THEN 'claude' WHEN 1 THEN 'chatgpt' WHEN 2 THEN 'llama'
          ELSE 'gemini'  -- 70% gemini for business
        END
      WHEN (((b.i * 7 + 3) % 500) + 1) % 20 < 3 THEN  -- gold loyalty
        CASE b.i % 10
          WHEN 0 THEN 'claude' WHEN 1 THEN 'gemini' WHEN 2 THEN 'llama'
          ELSE 'chatgpt'  -- 70% chatgpt for gold
        END
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (0, 1) THEN  -- budget segment
        CASE b.i % 10
          WHEN 0 THEN 'chatgpt' WHEN 1 THEN 'claude' WHEN 2 THEN 'gemini'
          ELSE 'llama'  -- 70% llama for budget
        END
      ELSE  -- adventurer/default
        CASE b.i % 8
          WHEN 0 THEN 'chatgpt' WHEN 1 THEN 'gemini' WHEN 2 THEN 'llama'
          ELSE 'claude'  -- ~63% claude for adventurers
        END
    END AS booking_agent,

    -- Accommodation: correlates with segment
    -- luxury → high_orbit, budget → low_orbit, mid otherwise
    CASE
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) = 4 THEN  -- luxury
        CASE b.i % 5 WHEN 0 THEN 'mid_orbit' ELSE 'high_orbit' END  -- 80% high
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (0, 1) THEN  -- budget
        CASE b.i % 5 WHEN 0 THEN 'mid_orbit' ELSE 'low_orbit' END  -- 80% low
      ELSE  -- adventurer
        CASE b.i % 3 WHEN 0 THEN 'high_orbit' WHEN 1 THEN 'low_orbit' ELSE 'mid_orbit' END
    END AS accommodation_type,

    -- Food plan: correlates with segment and accommodation
    -- luxury/high_orbit → all_inclusive, budget/low_orbit → budget, else breakfast
    CASE
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) = 4 THEN  -- luxury
        CASE b.i % 5 WHEN 0 THEN 'breakfast' ELSE 'all_inclusive' END  -- 80% all_inclusive
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (0, 1) THEN  -- budget
        CASE b.i % 5 WHEN 0 THEN 'breakfast' ELSE 'budget' END  -- 80% budget
      ELSE  -- adventurer
        CASE b.i % 3 WHEN 0 THEN 'all_inclusive' WHEN 1 THEN 'budget' ELSE 'breakfast' END
    END AS food_plan,

    -- Promo codes: budget rarely, adventurer sometimes, luxury often
    CASE
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (0, 1) AND b.i % 20 = 0 THEN 'ASTRO10'
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) IN (2, 3) AND b.i % 5 = 0 THEN
        CASE WHEN b.i % 2 = 0 THEN 'ASTRO20' ELSE 'EXPLORER5' END
      WHEN ((2000 + ((b.i * 7 + 3) % 500) + 1) % 5) = 4 AND b.i % 3 != 0 THEN
        CASE WHEN b.i % 3 = 1 THEN 'MARS25' ELSE 'LUNAR15' END
      ELSE NULL
    END AS promo_code

  FROM generate_series(1, 2500) AS b(i)
);

-- Generate payments with price that follows a formula:
-- base_fare * passengers * base_multiplier * season_factor * (1 - discount) + noise
INSERT INTO payments (booking_id, paid_at, amount_usd)
SELECT
  b.booking_id,
  b.booked_at + INTERVAL '15' MINUTE,
  GREATEST(100, CAST(
    r.base_fare_usd * b.passengers * p.base_multiplier
    * (1.0 + 0.2 * sin(extract(month FROM b.departure_date) * 0.52))
    * (1.0 - COALESCE(pc.discount_pct, 0.0))
    + ((hash(b.booking_id) % 2000)::INTEGER - 1000)
  AS INTEGER))
FROM bookings b
JOIN routes r ON b.route_id = r.route_id
JOIN planets p ON r.destination_id = p.planet_id
LEFT JOIN promo_codes pc ON b.promo_code = pc.promo_code
WHERE b.customer_id >= 2001;
