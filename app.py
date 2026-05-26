import streamlit as st

# 1. Initialize connection
# The "sql" type uses SQLAlchemy under the hood
conn = st.connection("postgresql", type="sql")

# 2. Perform a query and cache the result
df = conn.query("SELECT * FROM car_listings;", ttl=600)

#---------------------------------------------------------------------
#   Header                                                           |
#---------------------------------------------------------------------
st.write("""# Uzbekistan car analysis  
         """)



#---------------------------------------------------------------------
#   Sidebar                                                          |
#---------------------------------------------------------------------
st.sidebar.write("HI")



#---------------------------------------------------------------------
#  Tabs                                                              |
#---------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Dashbords", "Analysis", "Predictive model", "Data"])

with tab1:
    st.header("A cat")

with tab2:
    st.header("A dog")
with tab3:
    st.header("An owl")