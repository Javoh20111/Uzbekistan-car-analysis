import streamlit as st

# 1. Initialize connection
# The "sql" type uses SQLAlchemy under the hood
conn = st.connection("postgresql", type="sql")

# 2. Perform a query and cache the result
df = conn.query("SELECT * FROM car_listings;", ttl=600)

# 3. Display the data
st.dataframe(df)