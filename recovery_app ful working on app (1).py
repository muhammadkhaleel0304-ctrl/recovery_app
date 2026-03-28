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
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import os

# ================= FIREBASE =================
import firebase_admin
from firebase_admin import credentials, firestore

# init firebase only once
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")  # اپنا json file name
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= PAGE =================
st.title("Recovery Date Range Summary")

# ================= LOCAL STORAGE =================
LOCAL_FOLDER = "data"
LOCAL_FILE = os.path.join(LOCAL_FOLDER, "recovery.xlsx")
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# ================= FIREBASE LOAD =================
def load_from_firebase():
    doc = db.collection("recovery_summary").document("latest").get()
    if doc.exists:
        data = doc.to_dict().get("data", [])
        if data:
            return pd.DataFrame(data)
    return None

# ================= FIREBASE SAVE (FIXED) =================
def save_to_firebase(df):
    safe_df = df.copy()

    # ✅ FIX: categorical + NaN issue solve
    safe_df = safe_df.astype(str).replace("nan", "")

    db.collection("recovery_summary").document("latest").set({
        "data": safe_df.to_dict(orient="records")
    })

# ================= FILE UPLOAD =================
uploaded_file = st.file_uploader("Upload Recovery Excel / CSV", type=["xlsx", "csv"])

df = None

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.session_state["df"] = df

        # local save
        df.to_excel(LOCAL_FILE, index=False)

        # firebase save
        save_to_firebase(df)

        st.success("File uploaded + saved successfully!")

    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

# ================= AUTO LOAD SYSTEM =================
elif "df" in st.session_state:
    df = st.session_state["df"]
    st.info("Loaded from session")

elif os.path.exists(LOCAL_FILE):
    df = pd.read_excel(LOCAL_FILE)
    st.session_state["df"] = df
    st.info("Loaded from local file")

else:
    fb_df = load_from_firebase()
    if fb_df is not None:
        df = fb_df
        st.session_state["df"] = df
        st.info("Loaded from Firebase")
    else:
        st.warning("No data found. Please upload file.")
        st.stop()

# ================= SAFETY CHECK =================
if df is None or df.empty:
    st.warning("Empty dataset")
    st.stop()

# ================= DEBUG =================
st.write("Columns:", list(df.columns))

# ================= COLUMN SELECT =================
date_col = st.selectbox("Select Date Column", df.columns)
branch_col = st.selectbox("Select Branch Column", df.columns)

area_col = 'area_id' if 'area_id' in df.columns else None

# ================= DATE PROCESS =================
df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
df = df.dropna(subset=[date_col, branch_col])

df["Day"] = df[date_col].dt.day
df["Range"] = pd.cut(df["Day"], bins=[0,10,20,31], labels=["1-10","11-20","21-31"])

# ================= PIVOT =================
pivot = pd.pivot_table(
    df,
    index=[branch_col],
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

# ================= SHOW =================
st.subheader("Branch Wise Recovery Summary")
st.dataframe(result_df)

# ================= SAVE BUTTON =================
if st.button("🔄 Save to Firebase Again"):
    save_to_firebase(df)
    st.success("Saved successfully!")
