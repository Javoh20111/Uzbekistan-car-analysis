SELECT
    fuel_types.fuel_type_name,
    COUNT(*) AS count
FROM car_listings
LEFT JOIN fuel_types ON car_listings.fuel_type_id = fuel_types.fuel_type_id
GROUP BY
    fuel_types.fuel_type_name
ORDER BY count DESC

SELECT
    c.url,
    c.brand_id,
    b.brand_name,
    c.car_name
FROM cars c
LEFT JOIN brands b
    ON c.brand_id = b.brand_id
LIMIT 20;