import streamlit as st
import requests
import pandas as pd

st.title("Monitoring objects last status report")

# Get session_key from the URL
session_key = st.query_params["session_key"]

if not session_key:
    st.error("Missing session_key in URL")
    st.stop()

# Step 1: Get list of trackers
trackers_resp = requests.post(
    "https://api.eu.navixy.com/v2/tracker/list",
    json={"hash": session_key}
).json()

if not trackers_resp.get("success"):
    st.error("Failed to fetch trackers")
    st.stop()

trackers = trackers_resp["list"]

# Preload supporting data
tag_list = requests.post(
    "https:/api.eu.navixy.com/v2/tag/list",
    json={"hash": session_key}
).json().get("list", [])

tag_map = {tag["id"]: tag["name"] for tag in tag_list}

vehicle_list = requests.post(
    "https://api.eu.navixy.com/v2/vehicle/list",
    json={"hash": session_key}
).json().get("list", [])

vehicle_map = {v["tracker_id"]: v for v in vehicle_list}

employee_list = requests.post(
    "https://api.eu.navixy.com/v2/employee/list",
    json={"hash": session_key}
).json()

employees = employee_list if isinstance(employee_list, list) else employee_list.get("list", [])
employee_map = {e["tracker_id"]: e for e in employees if e["tracker_id"] is not None}

dept_list = requests.post(
    "https://api.eu.navixy.com/v2/department/list",
    json={"hash": session_key}
).json().get("list", [])

dept_map = {d["id"]: d for d in dept_list}

# Final output list
combined_data = []

# Step 2 onward: enrich each tracker
for tracker in trackers:
    tracker_id = tracker["id"]
    source_id = tracker["source"]["id"]
    tag_id = tracker.get("tag_bindings", [{}])[0].get("tag_id")

    # Step 2: Get state
    state_resp = requests.post(
        "https://api.eu.navixy.com/v2/tracker/get_state",
        json={"hash": session_key, "tracker_id": tracker_id}
    ).json()
    state = state_resp.get("state", {})

    # Step 3: Tag name
    tag_name = tag_map.get(tag_id, "")

    # Step 4: Vehicle
    vehicle = vehicle_map.get(tracker_id, {})
    # Step 5: Employee
    employee = employee_map.get(tracker_id, {})
    # Step 6: Department
    dept = dept_map.get(employee.get("department_id")) if employee else {}

    # Step 7: Geofences
    lat, lng = state.get("gps", {}).get("location", {}).get("lat"), state.get("gps", {}).get("location", {}).get("lng")
    geofence_labels = []
    if lat and lng:
        zone_resp = requests.post(
            "https://api.eu.navixy.com/v2/zone/search_location",
            json={"hash": session_key, "location": {"lat": lat, "lng": lng}}
        ).json()
        geofence_labels = [z["label"] for z in zone_resp.get("list", [])]

    combined_data.append({
        "tracker_id": tracker_id,
        "tracker_label": tracker.get("label"),
        "group_id": tracker.get("group_id"),
        "source_id": source_id,
        "model": tracker["source"].get("model"),
        "tag_name": tag_name,
        "gps_updated": state.get("gps", {}).get("updated"),
        "lat": lat,
        "lng": lng,
        "connection_status": state.get("connection_status"),
        "movement_status": state.get("movement_status"),
        "movement_status_update": state.get("movement_status_update"),
        "ignition": state.get("ignition"),
        "ignition_update": state.get("ignition_update"),
        "gsm_updated": state.get("gsm", {}).get("updated"),
        "gsm_signal": state.get("gsm", {}).get("signal_level"),
        "battery_level": state.get("battery_level"),
        "battery_update": state.get("battery_update"),
        "vehicle_label": vehicle.get("label"),
        "vehicle_model": vehicle.get("model"),
        "garage_name": vehicle.get("garage_organization_name"),
        "reg_number": vehicle.get("reg_number"),
        "vin": vehicle.get("vin"),
        "employee_first_name": employee.get("first_name"),
        "employee_last_name": employee.get("last_name"),
        "employee_phone": employee.get("phone"),
        "department_label": dept.get("label"),
        "department_address": dept.get("location", {}).get("address") if dept else "",
        "geofences": ", ".join(geofence_labels)
    })

# Show in Streamlit
df = pd.DataFrame(combined_data)
st.dataframe(df)

