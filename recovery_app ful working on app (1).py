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
from io import BytesIO

import firebase_admin
from firebase_admin import credentials, firestore

# ---------------- FIREBASE INIT ----------------
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------- PAGE ----------------
st.title("Recovery App (Firebase Permanent System)")

# ---------------- LOCAL STORAGE ----------------
LOCAL_FOLDER = "data"
LOCAL_FILE = os.path.join(LOCAL_FOLDER, "recovery.xlsx")
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# ---------------- FIREBASE LOAD (FIXED) ----------------
def load_from_firebase():
    doc = db.collection("recovery_summary").document("latest").get()

    if doc.exists:
        data = doc.to_dict().get("data", [])
        return pd.DataFrame(data)
    return None

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("Upload File", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.session_state["df"] = df

    # save local backup
    df.to_excel(LOCAL_FILE, index=False)

    # save to firebase
    db.collection("recovery_summary").document("latest").set({
        "data": df.to_dict(orient="records")
    })

    st.success("File uploaded + saved to Firebase ✅")

# ---------------- LOAD PRIORITY SYSTEM ----------------
if "df" in st.session_state:
    df = st.session_state["df"]

elif os.path.exists(LOCAL_FILE):
    df = pd.read_excel(LOCAL_FILE)
    st.session_state["df"] = df

else:
    firebase_df = load_from_firebase()

    if firebase_df is not None and not firebase_df.empty:
        df = firebase_df
        st.session_state["df"] = df
        st.success("Loaded from Firebase ☁ (Permanent Data)")
    else:
        st.warning("No data found. Please upload file.")
        st.stop()

# ---------------- SHOW DATA ----------------
st.subheader("Data Preview")
st.dataframe(df)

# ---------------- SAVE BUTTON (OPTIONAL MANUAL) ----------------
if st.button("💾 Save Again to Firebase"):
    db.collection("recovery_summary").document("latest").set({
        "data": df.to_dict(orient="records")
    })
    st.success("Saved again to Firebase ✅")

# ---------------- DOWNLOAD CSV ----------------
csv = df.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇ Download CSV",
    csv,
    "data.csv",
    "text/csv"
)

# ---------------- DOWNLOAD EXCEL ----------------
output = BytesIO()
df.to_excel(output, index=False)

st.download_button(
    "⬇ Download Excel",
    output.getvalue(),
    "data.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
