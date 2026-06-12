-- Reference and lookup data: the stable, hand-authored rows the workshop builds
-- on. Bulk transactional data (customers, bookings, orders) is in generate_data.sql.

INSERT INTO planets VALUES
(1001, 'Moon',   0.80),
(1002, 'Mars',   1.20),
(1003, 'Europa', 1.50),
(1004, 'Titan',  2.00),
(1005, 'Venus',  1.10);

INSERT INTO routes VALUES
(1001, 1001,  5000),
(1002, 1002, 25000),
(1003, 1003, 40000),
(1004, 1004, 55000),
(1005, 1005, 15000);

INSERT INTO promo_codes VALUES
('ASTRO10',   0.10),
('ASTRO20',   0.20),
('LUNAR15',   0.15),
('MARS25',    0.25),
('EXPLORER5', 0.05);

-- Menu catalog. Dessert names are canon to the workshop; the rest are in the
-- same spirit. price_usd / is_vegetarian / spice_level are flavor for now.
INSERT INTO menu_items (item_id, item_name, category, price_usd, is_vegetarian, spice_level) VALUES
(1,  'Asteroid Belt Bruschetta',  'appetizer', 14.00, true,  0),
(2,  'Comet-Dust Calamari',       'appetizer', 19.00, false, 1),
(3,  'Nebula Nachos',             'appetizer', 16.00, true,  2),
(4,  'Zero-G Spring Rolls',       'appetizer', 13.00, true,  1),
(11, 'Lunar Regolith Risotto',    'main',      32.00, true,  1),
(12, 'Martian Red-Dust Curry',    'main',      38.00, false, 3),
(13, 'Europan Ice-Lichen Stew',   'main',      41.00, true,  1),
(14, 'Titan Methane-Glazed Ribs', 'main',      55.00, false, 2),
(15, 'Venusian Sulfur Tagine',    'main',      36.00, false, 2),
(21, 'Ktarian Chocolate Puff',        'dessert', 18.00, true, 0),
(22, 'Blue Jello',                    'dessert',  8.00, true, 0),
(23, 'Bob''s Raisin Cookies',         'dessert',  6.00, true, 0),
(24, 'Seldon''s Psychohistory Swirl', 'dessert', 22.00, true, 0),
(25, 'Sweet Kibble',                  'dessert',  5.00, true, 0),
(31, 'Cosmic Cola',     'beverage', 5.00, true, 0),
(32, 'Stardust Latte',  'beverage', 7.00, true, 0),
(33, 'Quasar Kombucha', 'beverage', 8.00, true, 0),
(34, 'Photon Fizz',     'beverage', 6.00, true, 0);