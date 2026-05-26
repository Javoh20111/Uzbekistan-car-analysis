# Uzbekistan Car Market Analysis

End-to-end data project analyzing used car listings from OLX Uzbekistan. The project covers scraping support scripts, data cleaning, exploratory analysis and database preparation

## Project Highlights

- Cleaned and analyzed **48,273** Uzbekistan car listings with **31** final columns.
- Built a reusable data cleaning workflow for price normalization, mileage validation, engine volume normalization, model/brand cleanup, outlier flags, and feature engineering.
- Designed a relational SQL schema for cars, listings, brands, regions, fuel types, transmissions, colors, sale options, and additional vehicle options.
- Created a Streamlit app with dashboard metrics, EDA charts, filters, cleaned CSV download, and an interactive car price predictor.
- Compared regression models for price prediction. The best notebook result was a **Random Forest** model with **$1,525 MAE**, **$3,963 RMSE**, and **0.834 R2** on the test set.

## Tech Stack

- **Python:** pandas, NumPy, scikit-learn, BeautifulSoup, Selenium
- **Visualization:** Streamlit, Altair, Matplotlib, Seaborn
- **Database:** PostgreSQL-style relational schema and SQL analysis queries
- **ML:** preprocessing pipelines, one-hot encoding, imputation, Random Forest, Extra Trees, Ridge Regression

## Repository Structure

```text
.
├── app.py                         # Streamlit app entry point
├── src/
│   ├── data_loader.py             # Cached dataset loading
│   ├── charts.py                  # Matplotlib/Seaborn chart helpers
│   ├── views.py                   # Dashboard, EDA, and predictor UI
│   └── config.py                  # Shared paths and feature lists
├── notebooks/
│   ├── 01_data_cleaning.ipynb     # Data contract, audits, cleaning rules
│   ├── 02_eda.ipynb               # Exploratory analysis
│   ├── 03_database_preparation.ipynb
│   ├── 04_insert_data.ipynb
│   └── 05_predictive_model.ipynb  # Model training and comparison
├── sql/
│   ├── 01_create_tables.sql       # Normalized database schema
│   └── 02_analysis_queries.sql    # Example analysis queries
├── data/Prepared/
│   └── car_data_clean.csv         # Cleaned analysis dataset
├── car_scraper.py                 # OLX listing detail scraper
├── link_extractor.py              # Listing URL extraction by price range
├── range_finder.py                # Price range helper
└── requirements.txt
```

## Dataset

The cleaned dataset includes listing URL, location, price, currency, description, image URL, model, body type, sale type, year, mileage, transmission, color, engine volume, fuel type, condition, owners count, additional options, cleaned model fields, brand, USD price, outlier flag, mileage features, engine-volume features, and year validity.

Key cleaned dataset facts:

- Rows: **48,273**
- Columns: **31**
- Median listed price: **$6,700**
- Average listed price: **$9,711**
- Observed cleaned price range: **$500 to $167,414**
- Most common brands: Daewoo, Chevrolet, Lada, GAZ

## Data Cleaning Work

The cleaning notebook documents the data contract, validation rules, and cleaning choices before modeling. Major steps include:

- Converting listing prices into `price_usd` using a fixed UZS exchange rate.
- Creating `is_outlier` with IQR-based outlier detection.
- Cleaning model names into `brand`, `model_clean`, and `car_name`.
- Normalizing engine volume into liters with `engine_volume_l`.
- Creating mileage features such as `mileage_log` and `mileage_group`.
- Preserving a `year_valid` flag for manufacturing-year validation.
- Preparing model-ready columns for machine learning.

## Exploratory Analysis

The EDA work explores:

- Price distribution and high-value outliers
- Manufacturing year distribution
- Mileage patterns
- Engine volume distribution
- Listings by brand, body type, transmission, and fuel type
- Price relationships with year, fuel type, and other vehicle attributes

Main market observations:

- The market is heavily right-skewed, with many affordable vehicles and a smaller premium segment.
- Daewoo and Chevrolet dominate the listings, reflecting local market structure.
- Sedans and manual transmissions are especially common.
- Newer vehicles generally command higher prices, while mileage and age tend to reduce price.

## Price Prediction Model

The predictive modeling notebook builds a preprocessing and regression workflow using numeric and categorical vehicle features.

Features used include:

- Numeric: mileage, engine volume, owners count, age, condition
- Categorical: brand, model, fuel type, transmission, body type, region, color, district

Model comparison result:

| Model | Test MAE | Test RMSE | Test R2 |
| --- | ---: | ---: | ---: |
| Random Forest | $1,525 | $3,963 | 0.834 |
| Extra Trees | $1,562 | $4,090 | 0.823 |
| Ridge Regression | $2,838 | $5,602 | 0.668 |

The Streamlit app also includes an interactive prediction form that trains a Random Forest pipeline and returns a market price estimate with model error context.

## Streamlit App

Run the app locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

App sections:

- **Dashboard:** total listings, median price, average price, top brand, listings by brand, median price by region
- **Analysis:** filtered EDA views by brand, region, and year
- **Price Predictor:** form-based car price estimation using a trained regression model

## Database Design

The SQL schema separates repeated entities into dimension tables, including:

- Brands
- Currencies
- Conditions
- Colors
- Transmissions
- Fuel types
- Regions and districts
- Additional options
- Sale options

The central `cars` and `car_listings` tables store vehicle identity and listing-level details, with bridge tables for multi-value sale and additional options.