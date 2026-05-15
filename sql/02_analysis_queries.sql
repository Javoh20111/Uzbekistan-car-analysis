SELECT
    fuel_types.fuel_type_name,
    COUNT(*) AS count
FROM car_listings
LEFT JOIN fuel_types ON car_listings.fuel_type_id = fuel_types.fuel_type_id
GROUP BY
    fuel_types.fuel_type_name
ORDER BY count DESC