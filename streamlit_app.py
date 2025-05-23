import streamlit as st
import requests
import pandas as pd

# Set page config
st.set_page_config(page_title="Navixy Dashboard", layout="wide")

# Retrieve session_key from URL query parameters

session_key = st.query_params["session_key"]

if not session_key:
    st.error("Missing 'session_key' in URL. Please add '?session_key=<your_key>' to the URL.")
    st.stop()

# Sidebar configuration
st.sidebar.title("Navixy Dashboard")
page = st.sidebar.radio("Navigate to", ["Home", "Vehicle-Garage Mapping"])

# Sidebar input for API base URL (common)
st.sidebar.markdown("---")
api_base_url = st.sidebar.text_input("API Base URL", value="https://api.eu.navixy.com/v2")

# API call functions with enhanced checks
def get_vehicles(api_url: str, session_key: str) -> pd.DataFrame:
    url = f"{api_url}/vehicle/list"
    payload = {"hash": session_key}
    try:
        resp = requests.post(url, json=payload)
    except requests.RequestException as e:
        st.error(f"Error connecting to Vehicles API: {e}")
        return pd.DataFrame()
    if resp.status_code != 200:
        st.error(f"Vehicle API returned status {resp.status_code}")
        return pd.DataFrame()
    try:
        data = resp.json()
    except ValueError:
        st.error("Vehicle API returned non-JSON response")
        st.write(resp.text)
        return pd.DataFrame()
    if not data.get("success"):
        st.error("Vehicle API returned success=false")
        st.write(data)
        return pd.DataFrame()
    if "list" not in data:
        st.error("Vehicle API missing 'list' in response")
        st.write(data)
        return pd.DataFrame()
    if not data["list"]:
        st.warning("Vehicle API returned empty list")
    return pd.DataFrame(data.get("list", []))


def get_garages(api_url: str, session_key: str) -> pd.DataFrame:
    url = f"{api_url}/garage/list"
    payload = {"hash": session_key}
    try:
        resp = requests.post(url, json=payload)
    except requests.RequestException as e:
        st.error(f"Error connecting to Garages API: {e}")
        return pd.DataFrame()
    if resp.status_code != 200:
        st.error(f"Garage API returned status {resp.status_code}")
        return pd.DataFrame()
    try:
        data = resp.json()
    except ValueError:
        st.error("Garage API returned non-JSON response")
        st.write(resp.text)
        return pd.DataFrame()
    if not data.get("success"):
        st.error("Garage API returned success=false")
        st.write(data)
        return pd.DataFrame()
    if "list" not in data:
        st.error("Garage API missing 'list' in response")
        st.write(data)
        return pd.DataFrame()
    list_data = data.get("list", [])
    if not list_data:
        st.warning("Garage API returned empty list")
    # Flatten location dict
    for item in list_data:
        loc = item.pop("location", {})
        item.update({
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "address": loc.get("address"),
            "radius": loc.get("radius"),
        })
    return pd.DataFrame(list_data)

@st.cache_data
def load_data(session_key, api_base_url):
    vehicles_df = get_vehicles(api_base_url, session_key)
    garages_df = get_garages(api_base_url, session_key)
    return vehicles_df, garages_df

# Page: Home
def show_home():
    st.title("Welcome to Navixy Dashboard")
    st.markdown("**Use the sidebar to navigate between pages.**")
    st.markdown("**Available Pages:**\n- Home: Overview page\n- Vehicle-Garage Mapping: Merge and display vehicles with their garage details.")

# Page: Vehicle-Garage Mapping
def show_mapping():
    st.title("Vehicle-Garage Mapping")
    with st.spinner("Loading data..."):
        vehicles, garages = load_data(session_key, api_base_url)

    # Show counts for debugging
    st.write(f"Retrieved **{len(vehicles)}** vehicles and **{len(garages)}** garages.")

    if vehicles.empty or garages.empty:
        st.info("No data to display. Check session key and API URL.")
        return

    # Show raw vehicles table
    st.subheader("1) Vehicles Table")
    st.dataframe(vehicles)

    # Show raw garages table
    st.subheader("2) Garages Table")
    st.dataframe(garages)

    # Merge on garage id
    merged = vehicles.merge(
        garages,
        left_on="garage_id",
        right_on="id",
        suffixes=("_vehicle", "_garage"),
    )
    # Drop duplicate id_garage column
    merged = merged.drop(columns=["id_garage"]).rename(columns={"id_vehicle": "vehicle_id"})
    # Select only columns that have any non-null values
    non_null_cols = merged.columns[merged.notnull().any()].tolist()
    merged = merged[non_null_cols]

    # Show merged table
    st.subheader("3) Merged Vehicles & Garages Data")
    st.dataframe(merged)

# Main page routing
if page == "Home":
    show_home()
elif page == "Vehicle-Garage Mapping":
    show_mapping()
