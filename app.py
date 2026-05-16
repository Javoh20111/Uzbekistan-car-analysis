import streamlit as st

from src.charts import render_correlation_heatmap, render_boxplot, render_hist
from src.data_loader import load_car_data
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

    with dashboard_tab:
        render_dashboard(df)

    with analysis_tab:
        render_analysis(df)
        '''
        hello
        '''
        '---'
        render_boxplot(df)
        '''
        What I see  
        - Most cars priced between as low as 4000k to 10000k
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
        render_hist(df)
    with predictor_tab:
        render_predictor(df)


if __name__ == "__main__":
    main()
