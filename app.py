import streamlit as st
import subprocess
import json
import glob
import os

st.set_page_config(
    page_title="Data Quality Checker",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Production Data Quality Monitoring System")

if st.button("Run Data Quality Checks"):
    os.system("python checker.py")
    st.success("Checks completed successfully!")

reports = sorted(
    glob.glob("reports/*.json"),
    reverse=True
)

if reports:
    latest_report = reports[0]

    with open(latest_report, "r") as f:
        report = json.load(f)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Checks", report["total_checks"])
    col2.metric("Passed", report["passed"])
    col3.metric("Warnings", report["warnings"])
    col4.metric("Criticals", report["criticals"])

    st.subheader("Validation Results")
    st.json(report)