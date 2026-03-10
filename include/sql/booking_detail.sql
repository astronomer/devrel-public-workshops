SELECT mo.booking_id, mo.trip_day, mo.meal_type,
       b.customer_id, b.passengers, b.children, b.promo_code,
       b.booking_agent, b.accommodation_type, b.food_plan,
       b.return_date - b.departure_date AS trip_length,
       c.travel_type, c.loyalty_tier
FROM meal_orders mo
JOIN bookings b ON mo.booking_id = b.booking_id
JOIN customers c ON b.customer_id = c.customer_id
