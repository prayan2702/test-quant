import streamlit as st
import pandas as pd
import quantstats as qs
import pytz
import numpy as np
import time
import os
from IPython import get_ipython
import matplotlib.pyplot as plt
import base64

# Replace with your published CSV link
csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTuyGRVZuafIk2s7moScIn5PAUcPYEyYIOOYJj54RXYUeugWmOP0iIToljSEMhHrg_Zp8Vab6YvBJDV/pub?output=csv"

# Load the data into a Pandas DataFrame
@st.cache_data
def load_data(csv_url):
    try:
        data = pd.read_csv(csv_url)
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None
    return data

# Data cleaning and preprocessing
def preprocess_data(data):
    # Delete rows with Portfolio Value, Absolute Gain, Nifty50, Day Change
    rows_to_delete = data[data['Date'].isin(['Portfolio Value', 'Absolute Gain', 'Nifty50', 'Day Change'])].index
    data.drop(rows_to_delete, inplace=True)

    # Delete the rows which does not have NAV value
    data = data.dropna(subset=['NAV'])

    # Convert the 'Date' column to datetime objects and set it as the index
    data['Date'] = pd.to_datetime(data['Date'], format='%d-%b-%y')
    # Sort the data by Date in ascending order
    data = data.sort_values(by='Date')
    # Make the index tz aware
    data['Date'] = data['Date'].apply(lambda x: x.replace(tzinfo=None))
    data.set_index('Date', inplace=True)

    # Convert the 'NAV' column to numeric values
    data['NAV'] = pd.to_numeric(data['NAV'])

    # Remove % in Nifty50 Change % Column
    data['Nifty50 Change %'] = data['Nifty50 Change %'].str.rstrip('%').astype('float')/100

    # Make a column of Nifty50 NAV
    data['Nifty50 NAV'] = (1 + data['Nifty50 Change %']).cumprod()
    return data

# Calculate the daily returns
def calculate_returns(data):
    returns = data['NAV'].pct_change().dropna()
    nifty50 = data['Nifty50 Change %'].dropna()
    return returns, nifty50

# Verify if there are overlap in date range
def filter_data_by_date(returns, nifty50):
    start_date = max(returns.index.min(), nifty50.index.min())
    end_date = min(returns.index.max(), nifty50.index.max())

    returns = returns[start_date:end_date]
    nifty50 = nifty50[start_date:end_date]
    return returns, nifty50, start_date, end_date
# Main function for Streamlit app
def main():
    st.set_page_config(layout="wide")
    st.title("Portfolio Performance Analysis")

    # Load data
    data = load_data(csv_url)

    if data is not None:
        # Preprocess data
        processed_data = preprocess_data(data.copy())

        # Calculate returns
        returns, nifty50 = calculate_returns(processed_data)

        # Verify if there are overlap in date range and filter it
        returns, nifty50, start_date, end_date = filter_data_by_date(returns, nifty50)

        st.write(f"Data Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        st.subheader("Portfolio vs Nifty50 Returns")
        # Combine returns and nifty50 into a single DataFrame for plotting
        combined_returns = pd.DataFrame({'Portfolio': returns, 'Nifty50': nifty50})
        combined_returns = combined_returns.fillna(0)

        st.line_chart(combined_returns)

        # Display QuantStats report
        st.subheader("QuantStats Report")
        try:
            # CSS to adjust the width of the iframe and remove padding
            adjust_width_css = """
                <style>
                    section.main > div:has(~ footer ) {
                        padding-bottom: 0px;
                    }
                   body {
                        overflow: auto;
                    }
                </style>
            """
            st.markdown(adjust_width_css, unsafe_allow_html=True)
            report = qs.reports.full(returns, nifty50, output="report.html")
            with open("report.html", "r") as f:
                 report_html = f.read()

            st.markdown(report_html, unsafe_allow_html=True)

        except Exception as e:
             st.error(f"Error displaying QuantStats report: {e}")

if __name__ == "__main__":
     main()
