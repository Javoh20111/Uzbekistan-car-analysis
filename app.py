import streamlit as st
import altair as alt
import pandas as pd

#---------------------------------------------------------------------
#   Data load                                                         |
#---------------------------------------------------------------------
# 1. Initialize connection
# The "sql" type uses SQLAlchemy under the hood
conn = st.connection("postgresql", type="sql")

# 2. Perform a query and cache the result
df = conn.query("SELECT * FROM car_listings;", ttl=600)



st.set_page_config(
    page_title="Uzbekistan Car Market",
    layout="wide",
)


#---------------------------------------------------------------------
#   Header                                                           |
#---------------------------------------------------------------------
st.write("# Uzbekistan car analysis")
st.caption("OLX car listings dashboard, exploratory analysis, and price prediction workspace.")










#---------------------------------------------------------------------
#   Sidebar                                                          |
#---------------------------------------------------------------------
st.sidebar.write("HI")














#---------------------------------------------------------------------
#  Tabs                                                              |
#---------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Dashbords", "Analysis", "Predictive model", "Data"])

with tab1:
    st.subheader("Market Overview")

    #---------------------------------------------------------------------
    #  Dashboards                                                         |
    #---------------------------------------------------------------------
    total_listings = len(df)
    median_price = df["price_usd"].median()
    average_price = df["price_usd"].mean()
    top_brand = conn.query("""
        SELECT
            brands.brand_name,
            COUNT(cars.brand_id) AS count
        FROM
            car_listings cl
            LEFT JOIN cars on cars.url = cl.url
            LEFT JOIN brands on cars.brand_id = brands.brand_id
        GROUP BY
            brands.brand_name
        HAVING COUNT(cars.brand_id) > 0
        ORDER BY
            count DESC
                    """, ttl=600)
    top_brand_name = top_brand["brand_name"].iat[0]
    top_brand_count = top_brand["count"].iat[0]
    
    col1,col2,col3,col4 = st.columns(4)
    col1.metric("Listings", f"{total_listings:,}")
    col2.metric("Median Price", f"{median_price:,.0f}")
    col3.metric("Average Price", f"{average_price:,.0f}")
    col4.metric("Top Brands", f"{top_brand_name} ({top_brand_count:,.0f})")

    


with tab2:
    st.header("A dog")

with tab3:
    st.header("An owl")