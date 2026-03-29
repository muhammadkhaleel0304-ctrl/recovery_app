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

import firebase_admin
from firebase_admin import credentials, firestore

# ================= FIREBASE INIT =================
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= PAGE =================
st.title("Recovery Dashboard")

# ================= STORAGE =================
LOCAL_FOLDER = "data"
LOCAL_FILE = os.path.join(LOCAL_FOLDER, "recovery.xlsx")
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# ================= FIREBASE LOAD =================
def load_from_firebase():
    doc = db.collection("recovery_summary").document("latest").get()
    if doc.exists:
        return pd.DataFrame(doc.to_dict().get("data", []))
    return None

def save_to_firebase(df):
    df = df.fillna("").astype(str)
    db.collection("recovery_summary").document("latest").set({
        "data": df.to_dict(orient="records")
    })

# ================= UPLOAD =================
uploaded_file = st.file_uploader("Upload Excel/CSV", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.to_excel(LOCAL_FILE, index=False)
    save_to_firebase(df)
    st.success("Saved ✅")

# ================= LOAD DATA =================
fb_df = load_from_firebase()

if fb_df is not None and not fb_df.empty:
    main_df = fb_df
    st.success("Loaded from Firebase ☁")
elif os.path.exists(LOCAL_FILE):
    main_df = pd.read_excel(LOCAL_FILE)
    st.info("Loaded from local file")
else:
    st.stop()

# =====================================================
# 🔷 SECTION 1: TOP (INDEPENDENT VIEW)
# =====================================================
st.header("🔷 Top Section (Independent View)")

top_cols = list(main_df.columns)

top_col = st.selectbox(
    "Select Column (Top Section)",
    top_cols,
    key="top_col"
)

st.dataframe(main_df[[top_col]].head(50))


# =====================================================
# 🔷 SECTION 2: BOTTOM (SUMMARY - COMPLETELY INDEPENDENT)
# =====================================================
st.header("🔷 Recovery Summary (Bottom Section)")

df = main_df.copy()

cols = list(df.columns)

date_col = st.selectbox(
    "Select Date Column (Bottom)",
    cols,
    key="date_col"
)

branch_col = st.selectbox(
    "Select Branch Column (Bottom)",
    cols,
    key="branch_col"
)

# ================= DATE FIX =================
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
df = df.dropna(subset=[date_col, branch_col])

df["Day"] = df[date_col].dt.day

df["Range"] = pd.cut(
    df["Day"],
    bins=[0, 10, 20, 31],
    labels=["1-10", "11-20", "21-31"]
)

# ================= PIVOT =================
pivot = pd.pivot_table(
    df,
    index=[branch_col],
    columns="Range",
    aggfunc="size",
    fill_value=0
)

for c in ["1-10", "11-20", "21-31"]:
    if c not in pivot.columns:
        pivot[c] = 0

pivot = pivot[["1-10", "11-20", "21-31"]]
pivot["Total"] = pivot.sum(axis=1)

pivot["1-10 %"] = (pivot["1-10"] / pivot["Total"].replace(0, 1) * 100).round(2)
pivot["11-20 %"] = (pivot["11-20"] / pivot["Total"].replace(0, 1) * 100).round(2)
pivot["21-31 %"] = (pivot["21-31"] / pivot["Total"].replace(0, 1) * 100).round(2)

result_df = pivot.reset_index()

st.dataframe(result_df)

# ================= SAVE =================
if st.button("Save Again to Firebase"):
    save_to_firebase(main_df)
    st.success("Saved ☁")
