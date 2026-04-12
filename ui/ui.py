import os
import requests
import pandas as pd
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://app:5000")


def fetch_json(endpoint: str):
    url = f"{BACKEND_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        response = requests.get(url, timeout=6)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.warning(f"Unable to reach backend: {exc}")
        return None


st.set_page_config(page_title="Equipment Utilization Dashboard", layout="wide")
st.title("Equipment Utilization & Activity Monitoring")

status_col, detail_col = st.columns([1, 2])

with status_col:
    st.subheader("Current Equipment Status")
    latest = fetch_json("latest")
    if latest:
        st.metric("Equipment ID", latest.get("equipment_id", "N/A"))
        st.metric("State", latest.get("state", "N/A"))
        st.metric("Activity", latest.get("activity", "N/A"))
        st.metric("Utilization", f"{latest.get('utilization_percentage', 0)} %")
        st.metric("Confidence", f"{latest.get('confidence', 0):.2f}")
        st.write(f"Last updated: {latest.get('timestamp', 'N/A')}")
    else:
        st.error("Waiting for data from the backend...")

with detail_col:
    st.subheader("Live Utilization Summary")
    metrics = fetch_json("metrics?limit=100")
    if metrics:
        df = pd.DataFrame(metrics)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values(by="timestamp")
            df = df.set_index("timestamp")
            chart = df[["utilization_percentage", "confidence"]].rename(
                columns={"utilization_percentage": "Utilization %", "confidence": "Confidence"}
            )
            st.line_chart(chart)
            st.write(df[["equipment_id", "state", "activity", "utilization_percentage", "confidence"]].tail(10))
        else:
            st.info("No metrics available yet.")
    else:
        st.info("No backend metrics available.")

with st.expander("Raw latest payload"):
    if latest:
        st.json(latest)
    else:
        st.write("No payload available.")

st.caption(f"Backend URL: {BACKEND_URL}")

st_autorefresh = st.experimental_rerun
if st.button("Refresh now"):
    st.experimental_rerun()
