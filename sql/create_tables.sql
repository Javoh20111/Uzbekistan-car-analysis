CREATE TABLE brands (
    brand_id SERIAL PRIMARY KEY,
    brand_name VARCHAR(100) UNIQUE
);

CREATE TABLE currencies (
    currency_id SERIAL PRIMARY KEY,
    currency_name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE conditions (
    condition_id SERIAL PRIMARY KEY,
    condition_name VARCHAR(100) UNIQUE
);
CREATE TABLE colors (
    color_id SERIAL PRIMARY KEY,
    color_name VARCHAR(100) UNIQUE
);

CREATE TABLE transmissions (
    transmission_id SERIAL PRIMARY KEY,
    transmission_name VARCHAR(100) UNIQUE
);

CREATE TABLE fuel_types (
    fuel_type_id SERIAL PRIMARY KEY,
    fuel_type_name VARCHAR(100) UNIQUE
);

CREATE TABLE regions (
    region_id SERIAL PRIMARY KEY,
    region_name VARCHAR(100) UNIQUE
);

CREATE TABLE districts (
    district_id SERIAL PRIMARY KEY,
    district_name VARCHAR(100) UNIQUE
);

CREATE TABLE additional_options (
    additional_option_id SERIAL PRIMARY KEY,
    additional_option_name VARCHAR(100) UNIQUE
);

CREATE TABLE sale_options (
    option_id SERIAL PRIMARY KEY,
    sale_type VARCHAR(100) UNIQUE
);


CREATE TABLE listing_sale_options (
    url TEXT PRIMARY KEY,
    option_id INT NOT NULL,
    FOREIGN KEY (option_id)
        REFERENCES sale_options(option_id)
);

CREATE TABLE listing_additional_options (
    url TEXT PRIMARY KEY,
    additional_option_id INT NOT NULL,
    FOREIGN KEY (additional_option_id)
        REFERENCES additional_options(additional_option_id)
);


CREATE TABLE car_listings (
    url TEXT PRIMARY KEY,
    car_id INT NOT NULL,
    description TEXT,
    price_raw INT,
    price_usd NUMERIC(7,2),
    is_outlier BOOLEAN,
    currency_id INT NOT NULL,  -- Added NOT NULL
    condition_id INT,
    color_id INT,
    transmission_id INT,
    fuel_type_id INT,
    region_id INT,
    district_id INT,
    mileage NUMERIC(7,2),
    mileage_log NUMERIC(10,4),
    mileage_group VARCHAR(50),
    owners_count SMALLINT,
    created_at TIMESTAMP DEFAULT NOW(),
    image_url TEXT,
    
    FOREIGN KEY (currency_id) REFERENCES currencies(currency_id),
    FOREIGN KEY (condition_id) REFERENCES conditions(condition_id),
    FOREIGN KEY (color_id) REFERENCES colors(color_id),
    FOREIGN KEY (transmission_id) REFERENCES transmissions(transmission_id),
    FOREIGN KEY (fuel_type_id) REFERENCES fuel_types(fuel_type_id),
    FOREIGN KEY (region_id) REFERENCES regions(region_id),
    FOREIGN KEY (district_id) REFERENCES districts(district_id),
    FOREIGN KEY (car_id) REFERENCES cars(car_id),
    FOREIGN KEY (url) REFERENCES listing_sale_options(url),
    FOREIGN KEY (url) REFERENCES listing_additional_options(url)
);

ALTER TABLE car_listings
ADD CONSTRAINT fk_brand
FOREIGN KEY (car_id)
    REFERENCES cars(car_id);


CREATE TABLE cars (
    car_id SERIAL PRIMARY KEY,
    brand_id INT,
    model_raw TEXT,
    model_clean TEXT,
    car_name TEXT,
    year INT,
    year_valid BOOLEAN,
    engine_volume_raw NUMERIC(5,2),
    engine_volume_l NUMERIC(3,1),
    FOREIGN KEY (brand_id)
        REFERENCES brands(brand_id)
);
