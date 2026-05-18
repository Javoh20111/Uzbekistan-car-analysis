import streamlit as st
import time
import pandas as pd
import numpy as np

from src.charts import render_correlation_heatmap, render_boxplot, render_hist, categorical_analysis
from src.data_loader import load_car_data, stream_data
from src.views import render_analysis, render_dashboard, render_predictor


st.set_page_config(
    page_title="Uzbekistan Car Market",
    layout="wide",
)


def main():
    st.title("Uzbekistan Car Market Analysis")
    st.caption("OLX car listings dashboard, exploratory analysis, and price prediction workspace.")

    df = load_car_data()

    dashboard_tab, analysis_tab, predictor_tab = st.tabs(
        ["Dashboard", "Analysis", "Price Predictor"]
    )

    ##------------------------------------------------------------------------------ dashboard_tab

    with dashboard_tab:
        render_dashboard(df)
    ## -------------------------------------------------------------------------------- analysis_tab
    with analysis_tab:
        render_analysis(df)

        ## -------------------------------------------------------------------------------------
        '''
        ### Analysis
        Rule 1:  Every chart must have an interpretation  
        After each chart write  
        * What you see(facts)
        * What it might mean (interpretation)
        * What you would do next (action/decision)
        '''
        '---'

        render_boxplot(df)
        Content_1 = '''
        What I see  
        - Most cars priced between as low as 4k to 10k
        - The price disturebution heavily right-skewed due to high listed cars
        - Median price is roughly ~10k–12k USD
        - Majority of cars are cheap, small portion are very expensive

        What it might mean (interpretation)
        - Mass market dominance:
            - Most cars are affortable
            - Luxury cars are exist but It takes small proportion
            - High price outliers = Premium cars(Mercedes, BMW...)
        - Outliers are not errors:
            - Average price is misleading

        What I would do next
        - Log transform (CRITICAL for price)
        - Combine with mileage

        The car market is heavily right-skewed, with most vehicles priced below $20,000. A small number of high-value listings significantly extend the upper range, indicating the presence of a niche premium segment. Median price provides a more accurate representation than the mean due to extreme outliers.
        '''

        message_1 = stream_data(Content_1)
        if st.button("Show insights"):
            st.write(message_1)


        st.markdown('''---''')
        render_hist(df)
        Content_2 = '''
        What I see  
        - Most cars are between 2005 and 2025
        - There is a strong peak between 2021 - 2025
        - Very few cars before 1990
        - There is a small bump between 2007 -  2010
        - Counts increased gradually over time, in 2015 it sharply jumped.
        
        What it might mean (interpretation)
        - In Uzbekistan, people mostly buy/sell newer cars
        - Increased imports or high production by GM
        - Old cars are rare:
        - People may not posting it (bias)
        - Covid may be the reason
        - More online listings
        - Growth in resale
        - Most people sell their car in local places (bias)
        - People update often
        
        What I would do next
        - Create car age column or feature
        - Which cars selled newer by using groupby
        - Check price vs year
        
        The Uzbek car resale market is dominated by relatively new vehicles (post-2010), with a sharp increase after 2015, indicating growing purchasing power, import activity, and digital marketplace usage.
        '''
        message_2 = stream_data(Content_2)
        if st.button("Show insights for content 2"):
            st.write(message_2)
        """---"""

        categorical_analysis(df)
        Content_3 = '''
        What I see
        - Each Daewoo and Chevrolet are holding more than 14000 postings
        - Almost 50% of the cars has sedan type body
        - Manual cars are 66.7 precent, While Automstic ones are less than 33%
        - Cars that runs on both Gasoline and Gas are less that 25000 followed by cars that only runs on Gasoline closer to 17000  
          
        What it might mean (interpretation)
        - The Market is heavily local and budget-orianted 
        - All charts suggest affortable cars are being sold.  
          
        What I would next
        - In most common body types chart, there is a mistake, two `other` found 
        - In transmission types chart, There is 0.5 precent but we dont exacly know what it is.
        - Better short-term idea:
        -  - Focus on gas-related services or used car analytics tools
        - Long-term:
        -  - Track EV growth over time (trend analysis) before investing
        '''
        message_3 = stream_data(Content_3)
        if st.button("Show insights for content 3"):
            st.write(message_3)
        '''---'''
    ## ---------------------------------------------------------------------------------- predictor_tab
    with predictor_tab:
        render_predictor(df)


if __name__ == "__main__":
    main()
