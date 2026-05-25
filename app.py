import streamlit as st

from src.data_loader import load_car_data
from src.views import (
    render_analysis,
    render_dashboard,
    render_data_table,
    render_price_estimator,
)


st.set_page_config(
    page_title="Uzbekistan Car Market",
    layout="wide",
)


def main():
    st.title("Uzbekistan Car Market")
    st.caption("Clean OLX listings dashboard for market analysis and quick price checks.")

    df = load_car_data()

    dashboard_tab, analysis_tab, estimator_tab, data_tab = st.tabs(
        ["Dashboard", "Analysis", "Price Check", "Data"]
    )

    with dashboard_tab:
        render_dashboard(df)

    with analysis_tab:
        render_analysis(df)

    with estimator_tab:
        render_price_estimator(df)

    with data_tab:
        render_data_table(df)


if __name__ == "__main__":
    main()
