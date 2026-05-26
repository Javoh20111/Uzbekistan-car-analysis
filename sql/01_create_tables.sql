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


CREATE TABLE cars (
    url TEXT PRIMARY KEY,
    brand_id INT,
    model_raw TEXT,
    model_clean TEXT,
    car_name TEXT,
    year INT,
    year_valid BOOLEAN,
    engine_volume_raw NUMERIC(8,2),
    engine_volume_l NUMERIC(3,1),

    FOREIGN KEY (brand_id) REFERENCES brands(brand_id)
);

CREATE TABLE car_listings (
    url TEXT PRIMARY KEY,
    description TEXT,
    price_raw BIGINT,
    price_usd NUMERIC(12,2),
    is_outlier BOOLEAN,
    currency_id INT NOT NULL,
    condition_id INT,
    color_id INT,
    transmission_id INT,
    fuel_type_id INT,
    region_id INT,
    district_id INT,
    mileage NUMERIC(9,2),
    mileage_log NUMERIC(14,4),
    mileage_group VARCHAR(50),
    owners_count SMALLINT,
    created_at TIMESTAMP DEFAULT NOW(),
    image_url TEXT,

    FOREIGN KEY (url) REFERENCES cars(url),
    FOREIGN KEY (currency_id) REFERENCES currencies(currency_id),
    FOREIGN KEY (condition_id) REFERENCES conditions(condition_id),
    FOREIGN KEY (color_id) REFERENCES colors(color_id),
    FOREIGN KEY (transmission_id) REFERENCES transmissions(transmission_id),
    FOREIGN KEY (fuel_type_id) REFERENCES fuel_types(fuel_type_id),
    FOREIGN KEY (region_id) REFERENCES regions(region_id),
    FOREIGN KEY (district_id) REFERENCES districts(district_id)
);

CREATE TABLE listing_sale_options (
    url TEXT,
    option_id INT,

    PRIMARY KEY (url, option_id),

    FOREIGN KEY (url) REFERENCES car_listings(url),
    FOREIGN KEY (option_id) REFERENCES sale_options(option_id)
);

CREATE TABLE listing_additional_options (
    url TEXT,
    additional_option_id INT,

    PRIMARY KEY (url, additional_option_id),

    FOREIGN KEY (url) REFERENCES car_listings(url),
    FOREIGN KEY (additional_option_id)
        REFERENCES additional_options(additional_option_id)
);