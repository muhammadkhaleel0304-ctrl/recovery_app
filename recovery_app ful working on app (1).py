import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd

# 🔥 Firebase INIT
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.title("📂 File Upload + Firebase System")

# 📁 File upload
file = st.file_uploader("Upload Excel/CSV file", type=["csv", "xlsx"])

if file is not None:

    # 🔵 Read file
    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    st.subheader("📊 File Data")
    st.dataframe(df)

    # 🔵 Example result (you can change logic)
    total_rows = len(df)

    st.success(f"Total Rows: {total_rows}")

    # 🔥 Save to Firebase
    if st.button("Save Result to Firebase"):

        data = {
            "file_name": file.name,
            "total_rows": total_rows
        }

        db.collection("file_results").add(data)

        st.success("Result saved to Firebase ✅")
