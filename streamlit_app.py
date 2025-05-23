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

# API call functions with full attribute retrieval
def get_vehicles(api_url: str, session_key: str) -> pd.DataFrame:
    url = f"{api_url}/vehicle/list"
    payload = {"hash": session_key}
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"Error fetching vehicles: {e}")
        return pd.DataFrame()

    if not data.get("success") or "list" not in data:
        st.error("Unexpected vehicles response format or success=false")
        st.write(data)
        return pd.DataFrame()

    # Use json_normalize to expand nested structures if any
    vehicles_df = pd.json_normalize(data["list"])
    return vehicles_df


def get_garages(api_url: str, session_key: str) -> pd.DataFrame:
    url = f"{api_url}/garage/list"
    payload = {"hash": session_key}
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        st.error(f"Error fetching garages: {e}")
        return pd.DataFrame()

    if not data.get("success") or "list" not in data:
        st.error("Unexpected garages response format or success=false")
        st.write(data)
        return pd.DataFrame()

    # Use json_normalize to flatten the location dict into separate columns, while keeping original
    garages_df = pd.json_normalize(
        data["list"],
        sep="_",
        record_prefix="",
        meta=[],
        record_path=None
    )
    return garages_df

@st.cache_data
def load_data(session_key, api_base_url):
    vehicles_df = get_vehicles(api_base_url, session_key)
    garages_df = get_garages(api_base_url, session_key)
    return vehicles_df, garages_df

# Page: Home
def show_home():
    st.title("Welcome to Navixy Dashboard")
    st.markdown("**Use the sidebar to navigate between pages.**")
    try:
        vehicles, garages = load_data(session_key, api_base_url)
        st.metric("Total Vehicles", len(vehicles))
        st.metric("Total Garages", len(garages))
    except Exception:
        st.metric("Total Vehicles", 0)
        st.metric("Total Garages", 0)

# Page: Vehicle-Garage Mapping
def show_mapping():
    st.title("Vehicle-Garage Mapping")
    with st.spinner("Loading data..."):
        vehicles, garages = load_data(session_key, api_base_url)

    # Debug counts
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

    # Merge on garage_id
    merged = vehicles.merge(
        garages,
        left_on="garage_id",
        right_on="id",
        suffixes=("_vehicle", "_garage"),
        how="left"
    )
    # Drop duplicate id_garage column if present
    if "id_garage" in merged.columns:
        merged = merged.drop(columns=["id_garage"])
    if "id_vehicle" in merged.columns:
        merged = merged.rename(columns={"id_vehicle": "vehicle_id"})

    # Show merged table with full schema
    st.subheader("3) Merged Vehicles & Garages Data")
    st.dataframe(merged)

# Main page routing
if page == "Home":
    show_home()
elif page == "Vehicle-Garage Mapping":
    show_mapping()
