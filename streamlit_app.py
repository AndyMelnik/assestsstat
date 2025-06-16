import streamlit as st
import requests
import pandas as pd

API_BASE = "https://api.eu.navixy.com/v2"

# -------------------------------
# API Utilities
# -------------------------------
def fetch_json(url, payload):
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return None
    return None

# -------------------------------
# API Functions
# -------------------------------
def get_tracker_list(hash_key):
    res = fetch_json(f"{API_BASE}/tracker/list", {"hash": hash_key})
    return res.get("list", []) if res else []

def get_all_tracker_states(hash_key, tracker_ids):
    res = fetch_json(f"{API_BASE}/tracker/get_states", {
        "hash": hash_key,
        "trackers": tracker_ids,
        "allow_not_exist": True,
        "list_blocked": True
    })
    return res.get("states", {}) if res else {}

def get_tag_map(hash_key):
    res = fetch_json(f"{API_BASE}/tag/list", {"hash": hash_key})
    return {t["id"]: t["name"] for t in res.get("list", [])} if res else {}

def get_vehicle_map(hash_key):
    res = fetch_json(f"{API_BASE}/vehicle/list", {"hash": hash_key})
    return {v["tracker_id"]: v for v in res.get("list", [])} if res else {}

def get_employee_map(hash_key):
    res = fetch_json(f"{API_BASE}/employee/list", {"hash": hash_key})
    employee_list = res if isinstance(res, list) else res.get("list", [])
    return {e["tracker_id"]: e for e in employee_list if e.get("tracker_id")} if employee_list else {}

def get_department_map(hash_key):
    res = fetch_json(f"{API_BASE}/department/list", {"hash": hash_key})
    return {d["id"]: d for d in res.get("list", [])} if res else {}

def get_group_map(hash_key):
    res = fetch_json(f"{API_BASE}/tracker/group/list", {"hash": hash_key})
    return {g["id"]: g["title"] for g in res.get("list", [])} if res else {}

def get_geofences_by_location(hash_key, lat, lng):
    res = fetch_json(f"{API_BASE}/zone/search_location", {
        "hash": hash_key,
        "location": {"lat": lat, "lng": lng}
    })
    return [z["label"] for z in res.get("list", [])] if res else []

# -------------------------------
# MAIN APP
# -------------------------------
st.title("Assets Intelligence and Last Status Dashboard")

hash_key = st.query_params["session_key"]

if not hash_key:
    st.error("Missing session_key in URL.")
    st.stop()

st.info("Retrieving and fetching data...")

# Metadata loading
trackers = get_tracker_list(hash_key)
tracker_ids = [t["id"] for t in trackers]

tag_map = get_tag_map(hash_key)
vehicle_map = get_vehicle_map(hash_key)
employee_map = get_employee_map(hash_key)
department_map = get_department_map(hash_key)
group_map = get_group_map(hash_key)

# Efficient state loading
st.info("Loading tracker states in bulk...")
state_results = get_all_tracker_states(hash_key, tracker_ids)

# -------------------------------
# Build Final Table
# -------------------------------
final_data = []

for t in trackers:
    tracker_id = t["id"]
    state = state_results.get(str(tracker_id), {})  # note: keys are strings
    source = t.get("source", {})
    tag_bindings = t.get("tag_bindings", [])
    tag_id = tag_bindings[0].get("tag_id") if tag_bindings else None
    group_id = t.get("group_id")
    group_title = group_map.get(group_id, "")

    vehicle = vehicle_map.get(tracker_id, {})
    employee = employee_map.get(tracker_id, {})
    department = department_map.get(employee.get("department_id")) if employee else {}

    gps = state.get("gps", {}).get("location", {})
    lat, lng = gps.get("lat"), gps.get("lng")
    geofences = get_geofences_by_location(hash_key, lat, lng) if lat and lng else []

    final_data.append({
        "tracker_id": tracker_id,
        "label": t.get("label"),
        "group_id": group_id,
        "group_title": group_title,
        "source_id": source.get("id"),
        "model": source.get("model"),
        "tag": tag_map.get(tag_id, ""),
        "gps_updated": state.get("gps", {}).get("updated"),
        "lat": lat,
        "lng": lng,
        "connection_status": state.get("connection_status"),
        "movement_status": state.get("movement_status"),
        "movement_status_update": state.get("movement_status_update"),
        "ignition": state.get("ignition"),
        "ignition_update": state.get("ignition_update"),
        "gsm_updated": state.get("gsm", {}).get("updated"),
        "signal_level": state.get("gsm", {}).get("signal_level"),
        "battery_level": state.get("battery_level"),
        "battery_update": state.get("battery_update"),
        "vehicle_label": vehicle.get("label"),
        "vehicle_model": vehicle.get("model"),
        "garage": vehicle.get("garage_organization_name"),
        "reg_number": vehicle.get("reg_number"),
        "vin": vehicle.get("vin"),
        "employee_first_name": employee.get("first_name"),
        "employee_last_name": employee.get("last_name"),
        "employee_phone": employee.get("phone"),
        "department_label": department.get("label", ""),
        "department_address": department.get("location", {}).get("address", ""),
        "geofences": ", ".join(geofences)
    })

# -------------------------------
# Display
# -------------------------------
df = pd.DataFrame(final_data)
st.success(f"{len(df)} trackers processed.")
st.dataframe(df)

csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", csv, "trackers_full_export.csv", "text/csv")
