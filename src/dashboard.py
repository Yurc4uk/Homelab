import numpy as np
import streamlit as st
import pandas as pd
import sqlite3
import joblib

# Page configuration for the Streamlit application
st.set_page_config(page_title="IoT Control Room", layout="wide")
st.title("🎛️ ESP32 Control Room")

# Path to the SQLite database file
# DB_PATH = "/app/data/climate_data.db" # Example path for deployment
DB_PATH = "/home/spike/PycharmProjects/Projects/esp32_air_control/data/climate_data.db" # Local development path
MODEL_PATH = "src/temp_predictor_30m.pkl" # Path to the pre-trained model

# Cache the model loading to avoid reloading on every rerun
@st.cache_resource
def load_model():
    """Loads the pre-trained machine learning model."""
    return joblib.load(MODEL_PATH)

# Load the model once when the application starts
model = load_model()

def prepare_features_to_predict(df):
    """
    Prepares the DataFrame for prediction by resampling, creating cyclical
    and lagged features, and selecting the latest data point.

    Args:
        df (pd.DataFrame): The input DataFrame containing sensor data.

    Returns:
        pd.DataFrame: A DataFrame with features ready for model prediction.
    """
    # 0. Create a copy to avoid modifying the original DataFrame used for plotting
    df_copy = df.copy()

    # 1. Convert timestamp to datetime format and set it as the index
    # Use unit='ms' as the timestamp is in milliseconds
    df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'], unit='ms')
    df_copy.set_index('timestamp', inplace=True)

    # Resample data to 30-minute intervals and interpolate missing values
    # This aligns the data with the model's training interval
    df_resampled = df_copy.resample('30min').interpolate(method='time')

    # Create cyclical features for the hour to capture daily patterns
    df_resampled["hour_sin"] = np.sin(np.pi * 2 * df_resampled.index.hour / 24)
    df_resampled["hour_cos"] = np.cos(np.pi * 2 * df_resampled.index.hour / 24)

    # Create lagged temperature features to capture temporal dependencies
    df_resampled['temp_lag_1'] = df_resampled['temp'].shift(1) # Temperature from the previous 30-min interval
    df_resampled['temp_lag_2'] = df_resampled['temp'].shift(2) # Temperature from two 30-min intervals ago
    df_resampled['temp_lag_48'] = df_resampled['temp'].shift(48) # Temperature from 24 hours ago (48 * 30min intervals)

    # Get the latest complete data point after dropping rows with NaN values
    latest_data = df_resampled.dropna().iloc[-1:]

    # Select the specific features required by the model for prediction
    features = latest_data[['hum', 'press', 'gas', 'hour_sin', 'hour_cos', 'temp_lag_1', 'temp_lag_2', 'temp_lag_48']]

    return features

# Cache data loading to improve performance, data will be reloaded every 20 seconds
@st.cache_data(ttl=20)
def load_data(query_str):
    """
    Loads data from the SQLite database using a given SQL query.
    Caches the result for 20 seconds to reduce database load.

    Args:
        query_str (str): The SQL query to execute.

    Returns:
        pd.DataFrame: A DataFrame containing the loaded data, or an empty DataFrame if an error occurs.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql(query_str, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error connecting to the database: {e}")
        return pd.DataFrame()

# Create sidebar for user controls
with st.sidebar:
    st.sidebar.header("Settings")
    # Dropdown to select the number of records to display
    num_records = st.sidebar.selectbox("Number of records:", (72, 216, 504))

# Construct the SQL query based on the selected number of records
# This query fetches the most recent records
query = f"SELECT * FROM sensor_logs ORDER BY id DESC LIMIT {num_records}"

# Load data from the database
data = load_data(query)

with st.sidebar:
    # Button to download the displayed data as a CSV file
    if not data.empty:
        csv = data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label='⏬ Download Data as CSV',
            data=csv,
            file_name='filtered_sensor_data.csv',
            mime='text/csv'
        )

# Display data if the DataFrame is not empty
if not data.empty:
    # Get the most recent record (first in the sorted list)
    latest = data.iloc[0]

    # Initialize delta variables as None (in case there's no previous record)
    d_temp = d_hum = d_press = d_gas = None

    # Check if there are at least two records to calculate the difference
    if len(data) >= 2:
        pre_latest = data.iloc[1] # Get the second most recent record

        # Calculate the difference (current minus previous)
        diff_temp = float(latest['temp']) - float(pre_latest['temp'])
        diff_hum = float(latest['hum']) - float(pre_latest['hum'])
        diff_press = float(latest['press']) - float(pre_latest['press'])
        diff_gas = float(latest['gas']) - float(pre_latest['gas'])

        # Format the delta for display.
        # The :+.1f specifier automatically adds "+" for positive numbers and "-" for negative ones.
        d_temp = f"{diff_temp:+.1f} °C"
        d_hum = f"{diff_hum:+.1f} %"
        d_press = f"{diff_press:+.1f} hPa"
        d_gas = f"{diff_gas:+.1f} kOhm"

    # Display the latest measurement time
    st.subheader(f"Latest measurement at: {latest['hour']}:{latest['minute']}")

    # Create columns for metrics display
    col1, col2, col3, col4 = st.columns(4)

    # Display metrics with delta values
    col1.metric("Temperature", f"{latest['temp']} °C", delta=d_temp)
    col2.metric("Humidity", f"{latest['hum']} %", delta=d_hum)
    col3.metric("Pressure", f"{latest['press']} hPa", delta=d_press)
    col4.metric("Gas (Resistance)", f"{latest['gas']} kOhm", delta=d_gas)

    st.markdown("---") # Separator for visual distinction

    # Prepare features for the model prediction
    X_predict = prepare_features_to_predict(data)

    # Make a prediction using the loaded model
    predicted_temp = model.predict(X_predict)[0]

    st.subheader("AI Prediction")
    # Display the predicted temperature and its delta from the current temperature
    st.metric(
        label="Predicted Temperature (in 30 minutes)",
        value=f"{predicted_temp:.2f} °C",
        delta=f"{predicted_temp - latest['temp']:.2f} °C"
    )
    st.markdown("---") # Separator

    # Prepare data for charting (set timestamp as index for plotting)
    chart_data = data.set_index('timestamp')

    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4 = st.tabs(["Temperature", "Humidity", "Air Resistance", "All Information"])
    with tab1:
        st.subheader(f"Temperature Chart (last {num_records} measurements)")
        st.line_chart(chart_data['temp'])
    with tab2:
        st.subheader(f"Humidity Chart (last {num_records} measurements)")
        st.line_chart(chart_data['hum'])
    with tab3:
        st.subheader(f"Gas Resistance Chart (last {num_records} measurements)")
        st.line_chart(chart_data['gas'])
    with tab4:
        st.subheader(f"All last {num_records} measurements")
        st.dataframe(data)

    # Button to refresh data manually
    if st.button("🔄 Refresh Data"):
        st.rerun()

else:
    # Display a warning if no data is found in the database
    st.warning("Database is empty or the logger has not recorded any data yet.")
