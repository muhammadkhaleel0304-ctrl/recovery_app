import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd

# 🔥 Firebase init
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.title("📂 File Upload + Firebase Auto Load System")

# 📦 session storage
if "df" not in st.session_state:
    st.session_state.df = None

# 📁 Upload file
file = st.file_uploader("Upload Excel or CSV", type=["csv", "xlsx"])

# 🔵 If new file uploaded → save + store in Firebase
if file is not None:

    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    st.session_state.df = df

    # 🔥 SAVE TO FIREBASE
    for i, row in df.iterrows():
        db.collection("uploaded_files").add(row.to_dict())

    st.success("File saved to Firebase ✅")

# 🔄 ALWAYS LOAD FROM FIREBASE (after refresh)
docs = db.collection("uploaded_files").stream()

data_list = []
for doc in docs:
    data_list.append(doc.to_dict())

if data_list:
    df_show = pd.DataFrame(data_list)
    st.subheader("📊 Stored Data (Firebase)")
    st.dataframe(df_show)
else:
    st.warning("No data found in Firebase")
import streamlit as st
import pandas as pd
import os

# ================= FIREBASE =================
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= LOAD FIREBASE =================
def load_from_firebase():
    doc = db.collection("recovery_summary").document("latest").get()
    if doc.exists:
        data = doc.to_dict().get("data", [])
        if data:
            return pd.DataFrame(data)
    return None

# ================= SAVE FIREBASE =================
def save_to_firebase(df):
    safe_df = df.astype(str).replace("nan", "")
    db.collection("recovery_summary").document("latest").set({
        "data": safe_df.to_dict(orient="records")
    })

# ================= FILE UPLOAD =================
uploaded_file = st.file_uploader("Upload File", type=["xlsx", "csv"])

if uploaded_file:
    df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith("xlsx") else pd.read_csv(uploaded_file)
    save_to_firebase(df)
    st.success("Uploaded & Saved ✔")

# ================= LOAD DATA =================
df = load_from_firebase()

if df is None or df.empty:
    st.warning("Upload file first")
    st.stop()

st.subheader("Data Preview")
st.dataframe(df)

# ================= AUTO DETECT DATE =================
date_col = "recovery_date"

if date_col not in df.columns:
    st.error("recovery_date column not found")
    st.stop()

df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

# ================= GROUP TYPE =================
group_type = st.selectbox(
    "Select Report Type",
    ["Branch", "Area", "Region"],
    key="group_type"
)

# ================= VALIDATION =================
if group_type not in df.columns:
    st.error(f"{group_type} column not found in data")
    st.stop()

# ================= CLEAN =================
df = df.dropna(subset=[date_col, group_type])

# ================= RANGE =================
df["Day"] = df[date_col].dt.day
df["Range"] = pd.cut(df["Day"], bins=[0,10,20,31], labels=["1-10","11-20","21-31"])

# ================= PIVOT =================
pivot = pd.pivot_table(
    df,
    index=[group_type],
    columns="Range",
    aggfunc="size",
    fill_value=0
)

for c in ["1-10","11-20","21-31"]:
    if c not in pivot.columns:
        pivot[c] = 0

pivot["Total"] = pivot.sum(axis=1)

pivot["1-10 %"] = (pivot["1-10"] / pivot["Total"] * 100).round(2)
pivot["11-20 %"] = (pivot["11-20"] / pivot["Total"] * 100).round(2)
pivot["21-31 %"] = (pivot["21-31"] / pivot["Total"] * 100).round(2)

result_df = pivot.reset_index()

# ================= SHOW RESULT =================
st.subheader("Recovery Summary")
st.dataframe(result_df)
