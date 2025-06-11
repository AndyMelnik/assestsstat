import streamlit as st
import requests
import pandas as pd

API_BASE = "https://api.eu.navixy.com/v2"  # Replace if using another domain

# -------------------------------
# Step 1: Get Tracker List
# -------------------------------
def get_tracker_list(hash_key):
    url = f"{API_BASE}/tracker/list"
    response = requests.post(url, json={"hash": hash_key})
    if response.status_code == 200:
        return response.json().get("list", [])
    else:
        st.error(f"Tracker list API error: {response.status_code} - {response.text}")
        return []

# -------------------------------
# Step 2: Get Tracker State
# -------------------------------
def get_tracker_state(hash_key, tracker_id):
    url = f"{API_BASE}/tracker/get_state"
    response = requests.post(url, json={"hash": hash_key, "tracker_id": tracker_id})
    if response.status_code == 200:
        return response.json().get("state", {})
    else:
        st.warning(f"Tracker state fetch failed for ID {tracker_id}")
        return {}

# -------------------------------
# Step 3: Get Tags
# -------------------------------
def get_tag_map(hash_key):
    url = f"{API_BASE}/tag/list"
    response = requests.post(url, json={"hash": hash_key})
    if response.status_code == 200:
        return {tag["id"]: tag["name"] for tag in response.json().get("list", [])}
    return {}

# -------------------------------
# Step 4: Get Vehicles
# -------------------------------
def get_vehicle_map(hash_key):
    url = f"{API_BASE}/vehicle/list"
    response = requests.post(url, json={"hash": hash_key})
    if response.status_code == 200:
        return {v["tracker_id"]: v for v in response.json().get("list", [])}
    return {}

# -------------------------------
# Step 5: Get Employees
# -------------------------------
def get_employee_map(hash_key):
    url = f"{API_BASE}/employee/list"
    response = requests.post(url, json={"hash": hash_key})
    if response.status_code == 200:
        raw = response.json()
        employee_list = raw if isinstance(raw, list) else raw.get("list", [])
        return {e["tracker_id"]: e for e in employee_list if e.get("tracker_id") is not None}
    return {}

# -------------------------------
# Step 6: Get Departments
# -------------------------------
def get_department_map(hash_key):
    url = f"{API_BASE}/department/list"
    response = requests.post(url, json={"hash": hash_key})
    if response.status_code == 200:
        return {d["id"]: d for d in response.json().get("list", [])}
    return {}

# -------------------------------
# Step 7: Get Geofence Labels
# -------------------------------
def get_geofences_by_location(hash_key, lat, lng):
    url = f"{API_BASE}/zone/search_location"
    response = requests.post(url, json={"hash": hash_key, "location": {"lat": lat, "lng": lng}})
    if response.status_code == 200:
        return [z["label"] for z in response.json().get("list", [])]
    return []

# -------------------------------
# Step 8: Get Group Titles
# -------------------------------
def get_group_map(hash_key):
    url = f"{API_BASE}/tracker/group/list"
    response = requests.post(url, json={"hash": hash_key})
    if response.status_code == 200:
        return {g["id"]: g["title"] for g in response.json().get("list", [])}
    return {}

# -------------------------------
# MAIN STREAMLIT APP
# -------------------------------
st.title("Monitoring objects last status report")

# Get session_key from the URL
hash_key = st.query_params["session_key"]

if not hash_key:
    st.error("Missing session_key in URL.")
    st.stop()

st.info("Fetching and processing tracker data...")

trackers = get_tracker_list(hash_key)
tag_map = get_tag_map(hash_key)
vehicle_map = get_vehicle_map(hash_key)
employee_map = get_employee_map(hash_key)
department_map = get_department_map(hash_key)
group_map = get_group_map(hash_key)

final_data = []

for t in trackers:
    tracker_id = t["id"]
    state = get_tracker_state(hash_key, tracker_id)

    tag_bindings = t.get("tag_bindings", [])
    tag_id = tag_bindings[0].get("tag_id") if tag_bindings else None

    source = t.get("source", {})
    vehicle = vehicle_map.get(tracker_id, {})
    employee = employee_map.get(tracker_id, {})
    department = department_map.get(employee.get("department_id")) if employee else {}
    group_title = group_map.get(t.get("group_id"))

    gps = state.get("gps", {}).get("location", {})
    lat, lng = gps.get("lat"), gps.get("lng")
    geofences = get_geofences_by_location(hash_key, lat, lng) if lat and lng else []

    final_data.append({
        "tracker_id": tracker_id,
        "label": t.get("label"),
        "group_id": t.get("group_id"),
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
        "department_label": department.get("label"),
        "department_address": department.get("location", {}).get("address") if department else "",
        "geofences": ", ".join(geofences)
    })

st.success(f"{len(final_data)} trackers processed.")

df = pd.DataFrame(final_data)
st.dataframe(df)

# Optional CSV download
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", data=csv, file_name="tracker_data.csv", mime="text/csv")
