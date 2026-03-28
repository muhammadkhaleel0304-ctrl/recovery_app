import streamlit as st
import pandas as pd

st.title("📂 File Upload & Display App")

# 📁 File upload
file = st.file_uploader("Upload Excel or CSV file", type=["csv", "xlsx"])

if file is not None:

    # 🔵 Read file
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # 📊 Show file on screen
    st.subheader("📊 Uploaded File Data")
    st.dataframe(df)

    # 🔢 Basic info
    st.write("Total Rows:", len(df))
    st.write("Total Columns:", len(df.columns))
