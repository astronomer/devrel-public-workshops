INSERT INTO planets VALUES
(1001, 'Moon', 0.80),
(1002, 'Mars', 1.20),
(1003, 'Europa', 1.50);

INSERT INTO routes VALUES
(1001, 1001, 5000),
(1002, 1002, 25000),
(1003, 1003, 40000);

INSERT INTO promo_codes VALUES
('ASTRO10', 0.10),
('ASTRO20', 0.20);

INSERT INTO customers (customer_id, full_name, travel_type, loyalty_tier) VALUES
(1001, 'Ava Chen',       'leisure',  'gold'),
(1002, 'Noah Patel',     'business', 'silver'),
(1003, 'Mia Rodriguez',  'leisure',  'bronze'),
(1004, 'Liam Okafor',    'business', 'gold');

INSERT INTO bookings (customer_id, route_id, booked_at, departure_date, return_date, passengers, children, booking_agent, accommodation_type, food_plan, promo_code) VALUES
(1001, 1001, '2025-10-01 09:10:00', '2025-10-15', '2025-10-18', 2, 1, 'chatgpt',  'mid_orbit',  'breakfast',      'ASTRO10'),
(1002, 1002, '2025-12-05 14:45:00', '2026-03-01', '2026-09-01', 1, 0, 'gemini',   'high_orbit', 'all_inclusive',  NULL),
(1003, 1001, '2025-12-20 11:30:00', '2026-01-10', '2026-01-13', 3, 2, 'llama',    'low_orbit',  'budget',         NULL),
(1004, 1003, '2025-12-28 16:20:00', '2026-06-15', '2027-06-15', 2, 0, 'claude',   'high_orbit', 'all_inclusive',  'ASTRO20');

INSERT INTO payments (booking_id, paid_at, amount_usd) VALUES
(1, '2025-10-01 09:20:00', 7200),
(2, '2025-12-05 15:00:00', 30000),
(3, '2025-12-20 11:45:00', 12000),
(4, '2025-12-28 16:30:00', 96000);

-- ===== Space-themed menu =====
-- Appetizers (item_id 1-5)
INSERT INTO menu_items VALUES
(1,  'Plomeek Soup',           'appetizer', 'europan',  12.00, true,  0),
(2,  'Leola Root Croquettes',  'appetizer', 'europan',  10.00, true,  1),
(3,  'Belter Mushroom Bites',  'appetizer', 'martian',   8.00, true,  1),
(4,  'Jogan Fruit Salad',      'appetizer', 'lunar',    11.00, true,  0),
(5,  'Jamestown Corn Chowder', 'appetizer', 'lunar',     9.00, true,  0);

-- Mains (item_id 11-18)
INSERT INTO menu_items VALUES
(11, 'Nerf Steak',               'main', 'lunar',    28.00, false, 1),
(12, 'Gagh Platter',             'main', 'europan',  22.00, false, 3),
(13, 'Martian Fungal Risotto',   'main', 'martian',  18.00, true,  1),
(14, 'Replicated Roast',         'main', 'europan',  20.00, false, 0),
(15, 'Apollo Freeze-Dry Ration', 'main', 'lunar',    14.00, false, 0),
(16, 'Polystarch Noodle Bowl',   'main', 'martian',  15.00, true,  2),
(17, 'Red Kibble Curry',         'main', 'martian',  12.00, false, 3),
(18, 'Hasperat Wrap',            'main', 'europan',  16.00, true,  2);

-- Desserts (item_id 21-25) — classification targets
INSERT INTO menu_items VALUES
(21, 'Ktarian Chocolate Puff',       'dessert', 'universal', 14.00, true,  0),
(22, 'Blue Jello',                    'dessert', 'universal',  8.00, true,  0),
(23, 'Bobs Raisin Cookies',          'dessert', 'universal',  6.00, true,  0),
(24, 'Seldons Psychohistory Swirl',  'dessert', 'universal', 16.00, true,  0),
(25, 'Sweet Kibble',                  'dessert', 'universal',  4.00, true,  0);

-- Beverages (item_id 31-37)
INSERT INTO menu_items VALUES
(31, 'Earl Grey Hot',          'beverage', 'europan',   6.00, true,  0),
(32, 'Raktajino',              'beverage', 'europan',   7.00, true,  1),
(33, 'Romulan Ale',            'beverage', 'lunar',    15.00, true,  0),
(34, 'Martian Whiskey',        'beverage', 'martian',  12.00, true,  0),
(35, 'Blue Milk',              'beverage', 'lunar',     5.00, true,  0),
(36, 'Janeways Black Coffee',  'beverage', 'martian',   4.00, true,  0),
(37, 'Tang Rehydrated',        'beverage', 'lunar',     3.00, true,  0);
