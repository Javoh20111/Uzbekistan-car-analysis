/* 
Create 3 categories of queries:

Business Analytics — queries that answer real market questions
    Price analysis: median/percentile prices by brand, region, fuel type
    Market trends: which brands have best resale value, depreciation patterns
    Value finder: cars below median price in their category (good deals)

Advanced SQL Techniques — show technical prowess
    Window functions: rank/row_number for price tiers within brands
    CTEs: complex multi-step analysis (e.g., find all Daewoo sedans under $5K with 4+ rating)
    Subqueries: nested conditions and filtering
    JSON functions: if you stored options as JSON

Data Quality & Validation — show you think about data
    Outlier detection using standard deviation/IQR
    Missing data analysis
    Data integrity checks (orphaned records, FK violations)

    My recommendation: Add a 03_business_insights.sql with 5-7 well-commented queries that answer real questions like:
    "What's the price distribution by brand?" (with percentiles)
    "Which regions have the most listings per capita?"
    "How does mileage affect price by transmission type?
 */



/*
Qaysi turdaki yoqilg'i omma orasida key sotilyapti?

*/
SELECT
    fuel_types.fuel_type_name,
    COUNT(*) AS count
FROM car_listings
LEFT JOIN fuel_types ON car_listings.fuel_type_id = fuel_types.fuel_type_id
GROUP BY
    fuel_types.fuel_type_name
ORDER BY count DESC

/*
Nimalar aniqlandi:
    Topilma asosida shuni ayta olamizki. Mashinalarning yarimidan ortig'i benzin va gazni birgalikda taminlaydi. Faqatgina benzin yoqilg'isini taminlaydigan mashinalar soni 19000 dan ortiq.
Nima uchun qiziq bo'lishi mumkin:
    O'zbeklar orasida gaz va benzinga asoslangan mashinalar soni juda ko'p. 
*/


/* Mashinalar xolati mashina narxiga qanday tasir etadi? */
SELECT
    conditions.condition_name,
    COUNT(conditions.condition_name) AS qaydlar_soni,
    percentile_cont(.50) WITHIN GROUP (ORDER BY price_usd) AS percentile_50
FROM car_listings
LEFT JOIN 
    conditions ON conditions.condition_id = car_listings.condition_id
GROUP BY
    conditions.condition_name
HAVING condition_name IS NOT NULL
ORDER BY percentile_50 DESC 

/* 
Natija asosida shuni ayta olamizki. Mashina xolati mashina narxiga ancha tasir qiladi.

 */


SELECT
    colors.color_name,
    COUNT(colors.color_name) AS qaydlar_soni,
    percentile_cont(.50) WITHIN GROUP (ORDER BY price_usd) AS percentile_50
FROM car_listings
LEFT JOIN 
    colors ON colors.color_id = car_listings.color_id
GROUP BY
    colors.color_name
HAVING color_name IS NOT NULL
ORDER BY percentile_50 DESC, qaydlar_soni DESC 


SELECT url, COUNT(*)
FROM car_listings
GROUP BY url
HAVING COUNT(*) > 1;