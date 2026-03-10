-- Generate ~12k meal orders with learnable patterns for ML.
--
-- Patterns baked in:
--   Destination cuisine: Moon→lunar, Mars→martian, Europa→europan
--   Customer segment behavior: budget=cheap+skip dessert, luxury=premium+always dessert
--   Dessert selection is CUSTOMER-DRIVEN (personality, not destination):
--     business travelers → Ktarian Chocolate Puff (expense it!)
--     gold loyalty       → Blue Jello (nostalgic safe pick)
--     budget/promo users → Bob's Raisin Cookies (cheapest decent option)
--     families with kids → Blue Jello (safe, kids love it)
--     adventurous adults → Seldon's Psychohistory Swirl
--     llama users        → Sweet Kibble (budget contrarian pick)
--   Day-of-trip spending: splurge on day 1 and last day

-- Step 1: Create a helper table with one row per booking-day-meal
CREATE TEMPORARY TABLE _meal_slots AS
SELECT
  b.booking_id,
  b.customer_id,
  b.route_id,
  r.destination_id,
  d.day_num AS trip_day,
  m.meal AS meal_type,
  b.passengers,
  b.children,
  b.promo_code,
  b.booking_agent,
  b.accommodation_type,
  b.food_plan,
  c.travel_type,
  c.loyalty_tier,
  (b.return_date - b.departure_date) AS trip_length,
  d.day_num AS day_num
FROM bookings b
JOIN routes r ON b.route_id = r.route_id
JOIN customers c ON b.customer_id = c.customer_id
CROSS JOIN (SELECT unnest(generate_series(1, 60)) AS day_num) d
CROSS JOIN (SELECT unnest(['lunch', 'dinner']) AS meal) m
WHERE b.customer_id >= 2001
  AND d.day_num <= (b.return_date - b.departure_date);

-- Step 2: Determine cuisine for each meal based on destination + noise
-- Moon(1001)→lunar, Mars(1002)→martian, Europa(1003)→europan
CREATE TEMPORARY TABLE _meal_cuisine AS
SELECT
  ms.*,
  CASE
    -- ~60% destination-native cuisine, rest random
    WHEN hash(ms.booking_id * 1000 + ms.trip_day * 10 + CASE ms.meal_type WHEN 'lunch' THEN 1 ELSE 2 END) % 100 < 60 THEN
      CASE ms.destination_id
        WHEN 1001 THEN 'lunar'
        WHEN 1002 THEN 'martian'
        WHEN 1003 THEN 'europan'
      END
    ELSE
      CASE (hash(ms.booking_id * 31 + ms.trip_day * 7 + ms.customer_id) % 3)::INTEGER
        WHEN 0 THEN 'lunar'
        WHEN 1 THEN 'martian'
        WHEN 2 THEN 'europan'
      END
  END AS meal_cuisine,
  -- Customer segment: 0-1=budget, 2-3=adventurer, 4=luxury
  (ms.customer_id % 5) AS segment
FROM _meal_slots ms;


-- Step 3: Pick a main course matching the cuisine
CREATE TEMPORARY TABLE _mains AS
SELECT
  mc.booking_id, mc.trip_day, mc.meal_type, mc.customer_id,
  mc.destination_id, mc.meal_cuisine, mc.segment, mc.passengers, mc.trip_length,
  mc.children, mc.promo_code, mc.travel_type, mc.loyalty_tier,
  mc.booking_agent, mc.accommodation_type, mc.food_plan,
  CASE mc.meal_cuisine
    WHEN 'lunar'   THEN CASE WHEN hash(mc.booking_id + mc.trip_day) % 2 = 0 THEN 11 ELSE 15 END
    WHEN 'martian' THEN CASE WHEN hash(mc.booking_id + mc.trip_day * 3) % 3 = 0 THEN 13
                              WHEN hash(mc.booking_id + mc.trip_day * 3) % 3 = 1 THEN 16
                              ELSE 17 END
    WHEN 'europan' THEN CASE WHEN hash(mc.booking_id + mc.trip_day * 2) % 3 = 0 THEN 12
                              WHEN hash(mc.booking_id + mc.trip_day * 2) % 3 = 1 THEN 14
                              ELSE 18 END
    ELSE 14
  END AS main_item_id
FROM _meal_cuisine mc;


-- Step 4: Determine which optional courses this meal gets + customer-driven dessert
CREATE TEMPORARY TABLE _meal_plan AS
SELECT
  m.*,
  -- Appetizer: budget 20%, adventurer 50%, luxury 70%
  CASE
    WHEN m.segment IN (0, 1) AND hash(m.booking_id * 13 + m.trip_day * 3 + 1) % 100 < 20 THEN true
    WHEN m.segment IN (2, 3) AND hash(m.booking_id * 13 + m.trip_day * 3 + 1) % 100 < 50 THEN true
    WHEN m.segment = 4       AND hash(m.booking_id * 13 + m.trip_day * 3 + 1) % 100 < 70 THEN true
    ELSE false
  END AS has_appetizer,
  -- Dessert: budget 30%, adventurer 65%, luxury 85%
  CASE
    WHEN m.segment IN (0, 1) AND hash(m.booking_id * 17 + m.trip_day * 5 + 2) % 100 < 30 THEN true
    WHEN m.segment IN (2, 3) AND hash(m.booking_id * 17 + m.trip_day * 5 + 2) % 100 < 65 THEN true
    WHEN m.segment = 4       AND hash(m.booking_id * 17 + m.trip_day * 5 + 2) % 100 < 85 THEN true
    ELSE false
  END AS has_dessert,
  -- Beverage: budget 40%, adventurer 60%, luxury 80%
  CASE
    WHEN m.segment IN (0, 1) AND hash(m.booking_id * 19 + m.trip_day * 7 + 3) % 100 < 40 THEN true
    WHEN m.segment IN (2, 3) AND hash(m.booking_id * 19 + m.trip_day * 7 + 3) % 100 < 60 THEN true
    WHEN m.segment = 4       AND hash(m.booking_id * 19 + m.trip_day * 7 + 3) % 100 < 80 THEN true
    ELSE false
  END AS has_beverage,
  -- DESSERT SELECTION: compound-feature-driven for strong ML signal
  -- Each compound maps to a dessert with 85-90% probability
  -- 21=Ktarian Chocolate Puff, 22=Blue Jello, 23=Bob's Raisin Cookies,
  -- 24=Seldon's Psychohistory Swirl, 25=Sweet Kibble
  (CASE
    -- COMPOUND 1: gemini + high_orbit + all_inclusive → 95% Ktarian Puff (corporate premium)
    WHEN m.booking_agent = 'gemini' AND m.accommodation_type = 'high_orbit'
         AND m.food_plan = 'all_inclusive' THEN
      CASE
        WHEN (hash(m.booking_id * 41 + m.trip_day * 17 + m.customer_id * 7) % 100)::INTEGER < 95 THEN 21
        ELSE 24
      END
    -- COMPOUND 2: claude + (high/mid orbit) + no kids → 93% Seldon's Swirl (adventurer elite)
    WHEN m.booking_agent = 'claude' AND m.accommodation_type IN ('high_orbit', 'mid_orbit')
         AND m.children = 0 THEN
      CASE
        WHEN (hash(m.booking_id * 43 + m.trip_day * 19 + m.customer_id * 11) % 100)::INTEGER < 93 THEN 24
        WHEN (hash(m.booking_id * 43 + m.trip_day * 19 + m.customer_id * 11) % 100)::INTEGER < 97 THEN 21
        ELSE 22
      END
    -- COMPOUND 3: chatgpt + gold loyalty → 92% Blue Jello (nostalgic mainstream)
    WHEN m.booking_agent = 'chatgpt' AND m.loyalty_tier = 'gold' THEN
      CASE
        WHEN (hash(m.booking_id * 47 + m.trip_day * 23 + m.customer_id * 13) % 100)::INTEGER < 92 THEN 22
        WHEN (hash(m.booking_id * 47 + m.trip_day * 23 + m.customer_id * 13) % 100)::INTEGER < 97 THEN 21
        ELSE 23
      END
    -- COMPOUND 4: llama + low_orbit + budget → 75% Sweet Kibble
    WHEN m.booking_agent = 'llama' AND m.accommodation_type = 'low_orbit'
         AND m.food_plan = 'budget' THEN
      CASE
        WHEN (hash(m.booking_id * 53 + m.trip_day * 29 + m.customer_id * 17) % 100)::INTEGER < 75 THEN 25
        WHEN (hash(m.booking_id * 53 + m.trip_day * 29 + m.customer_id * 17) % 100)::INTEGER < 93 THEN 23
        ELSE 22
      END
    -- COMPOUND 5: families with kids + chatgpt → 90% Blue Jello
    WHEN m.children > 0 AND m.booking_agent = 'chatgpt' THEN
      CASE
        WHEN (hash(m.booking_id * 57 + m.trip_day * 31 + m.customer_id * 19) % 100)::INTEGER < 90 THEN 22
        WHEN (hash(m.booking_id * 57 + m.trip_day * 31 + m.customer_id * 19) % 100)::INTEGER < 97 THEN 23
        ELSE 21
      END
    -- Families with kids (any agent): 75% Blue Jello, 18% Bob's Cookies
    WHEN m.children > 0 THEN
      CASE
        WHEN (hash(m.booking_id * 59 + m.trip_day * 33 + m.customer_id * 21) % 100)::INTEGER < 75 THEN 22
        WHEN (hash(m.booking_id * 59 + m.trip_day * 33 + m.customer_id * 21) % 100)::INTEGER < 93 THEN 23
        WHEN (hash(m.booking_id * 59 + m.trip_day * 33 + m.customer_id * 21) % 100)::INTEGER < 98 THEN 21
        ELSE 24
      END
    -- Business + gemini (but not high_orbit+all_inclusive): 80% Ktarian Puff
    WHEN m.travel_type = 'business' AND m.booking_agent = 'gemini' THEN
      CASE
        WHEN (hash(m.booking_id * 61 + m.trip_day * 37 + m.customer_id * 23) % 100)::INTEGER < 80 THEN 21
        WHEN (hash(m.booking_id * 61 + m.trip_day * 37 + m.customer_id * 23) % 100)::INTEGER < 93 THEN 24
        ELSE 22
      END
    -- Budget food plan + llama (but not low_orbit): 55% Sweet Kibble
    WHEN m.food_plan = 'budget' AND m.booking_agent = 'llama' THEN
      CASE
        WHEN (hash(m.booking_id * 67 + m.trip_day * 41 + m.customer_id * 29) % 100)::INTEGER < 55 THEN 25
        WHEN (hash(m.booking_id * 67 + m.trip_day * 41 + m.customer_id * 29) % 100)::INTEGER < 85 THEN 23
        ELSE 22
      END
    -- Llama (any other combination): 40% Sweet Kibble
    WHEN m.booking_agent = 'llama' THEN
      CASE
        WHEN (hash(m.booking_id * 69 + m.trip_day * 43 + m.customer_id * 31) % 100)::INTEGER < 40 THEN 25
        WHEN (hash(m.booking_id * 69 + m.trip_day * 43 + m.customer_id * 31) % 100)::INTEGER < 65 THEN 23
        WHEN (hash(m.booking_id * 69 + m.trip_day * 43 + m.customer_id * 31) % 100)::INTEGER < 85 THEN 22
        ELSE 24
      END
    -- Default: relatively uniform with mild preferences
    ELSE
      CASE
        WHEN (hash(m.booking_id * 71 + m.trip_day * 43 + m.customer_id * 31) % 100)::INTEGER < 28 THEN 21
        WHEN (hash(m.booking_id * 71 + m.trip_day * 43 + m.customer_id * 31) % 100)::INTEGER < 53 THEN 22
        WHEN (hash(m.booking_id * 71 + m.trip_day * 43 + m.customer_id * 31) % 100)::INTEGER < 73 THEN 24
        WHEN (hash(m.booking_id * 71 + m.trip_day * 43 + m.customer_id * 31) % 100)::INTEGER < 93 THEN 23
        ELSE 25
      END
  END) AS dessert_item_id,
  -- Appetizer item: match cuisine
  CASE m.meal_cuisine
    WHEN 'europan' THEN CASE WHEN hash(m.booking_id + m.trip_day + 77) % 2 = 0 THEN 1 ELSE 2 END
    WHEN 'martian' THEN 3
    WHEN 'lunar'   THEN CASE WHEN hash(m.booking_id + m.trip_day + 88) % 2 = 0 THEN 4 ELSE 5 END
    ELSE 1
  END AS appetizer_item_id,
  -- Beverage item: match cuisine
  CASE m.meal_cuisine
    WHEN 'europan' THEN CASE WHEN hash(m.booking_id + m.trip_day + 99) % 2 = 0 THEN 31 ELSE 32 END
    WHEN 'martian' THEN CASE WHEN hash(m.booking_id + m.trip_day + 99) % 2 = 0 THEN 34 ELSE 36 END
    WHEN 'lunar'   THEN CASE WHEN hash(m.booking_id + m.trip_day + 99) % 3 = 0 THEN 33
                              WHEN hash(m.booking_id + m.trip_day + 99) % 3 = 1 THEN 35
                              ELSE 37 END
    ELSE 31
  END AS beverage_item_id
FROM _mains m;


-- Step 5: Insert all meal orders
-- Quantities use proportional adjustments so booking features explain meaningful
-- variance in daily_spend. The food_plan column is the meal plan booked at the
-- destination: passengers with all-inclusive plans spend more freely during the
-- trip, knowing meals at the destination are already covered.

-- Main courses (every meal gets one)
INSERT INTO meal_orders (booking_id, trip_day, meal_type, item_id, quantity)
SELECT booking_id, trip_day, meal_type, main_item_id,
  CASE
    WHEN booking_agent = 'claude' THEN passengers + 2
    WHEN booking_agent = 'llama'  THEN GREATEST(1, passengers - 1)
    ELSE passengers
  END
  + CASE WHEN loyalty_tier = 'gold' THEN passengers / 2 + 1 ELSE 0 END
  + CASE WHEN accommodation_type = 'high_orbit' THEN 2 ELSE 0 END
FROM _meal_plan;

-- Appetizers
INSERT INTO meal_orders (booking_id, trip_day, meal_type, item_id, quantity)
SELECT booking_id, trip_day, meal_type, appetizer_item_id,
  CASE WHEN promo_code IS NOT NULL THEN passengers + 2 ELSE passengers END
  + CASE WHEN food_plan = 'all_inclusive' THEN passengers ELSE 0 END
FROM _meal_plan
WHERE has_appetizer;

-- Desserts
INSERT INTO meal_orders (booking_id, trip_day, meal_type, item_id, quantity)
SELECT booking_id, trip_day, meal_type, dessert_item_id,
  CASE WHEN children > 0 THEN passengers + children ELSE passengers END
  + CASE WHEN loyalty_tier = 'gold' THEN passengers / 2 + 1 ELSE 0 END
  + CASE WHEN food_plan = 'all_inclusive' THEN passengers ELSE 0 END
FROM _meal_plan
WHERE has_dessert;

-- Beverages
INSERT INTO meal_orders (booking_id, trip_day, meal_type, item_id, quantity)
SELECT booking_id, trip_day, meal_type, beverage_item_id,
  CASE
    WHEN booking_agent = 'claude' THEN passengers + children + 2
    WHEN children > 0             THEN passengers + children
    ELSE passengers
  END
  + CASE WHEN accommodation_type = 'high_orbit' THEN passengers / 2 + 1 ELSE 0 END
FROM _meal_plan
WHERE has_beverage;


-- Cleanup temp tables
DROP TABLE IF EXISTS _meal_plan;
DROP TABLE IF EXISTS _mains;
DROP TABLE IF EXISTS _meal_cuisine;
DROP TABLE IF EXISTS _meal_slots;
