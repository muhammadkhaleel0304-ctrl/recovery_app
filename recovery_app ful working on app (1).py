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

# ================= PAGE =================
st.title("Recovery Date Range Summary")

# ================= LOCAL STORAGE =================
LOCAL_FOLDER = "data"
LOCAL_FILE = os.path.join(LOCAL_FOLDER, "recovery.xlsx")
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# ================= AUTO COLUMN DETECTION =================
def detect_columns(df):
    date_col = None
    branch_col = None

    # common patterns
    date_keywords = ["date", "recovery_date", "rec_date", "tran_date"]
    branch_keywords = ["branch", "branch_id", "branchid", "br_code", "brcode"]

    for col in df.columns:
        c = col.lower()

        if any(k in c for k in date_keywords):
            date_col = col

        if any(k in c for k in branch_keywords):
            branch_col = col

    # fallback
    if date_col is None:
        date_col = df.columns[0]

    if branch_col is None:
        branch_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

    return date_col, branch_col


# ================= FIREBASE LOAD =================
def load_from_firebase():
    doc = db.collection("recovery_summary").document("latest").get()
    if doc.exists:
        data = doc.to_dict().get("data", [])
        if data:
            df = pd.DataFrame(data)

            for col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col])
                except:
                    pass

            return df
    return None


# ================= SAVE =================
def save_to_firebase(df):
    safe_df = df.astype(str).replace("nan", "")
    db.collection("recovery_summary").document("latest").set({
        "data": safe_df.to_dict(orient="records")
    })


# ================= UPLOAD =================
uploaded_file = st.file_uploader("Upload Excel / CSV", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.to_excel(LOCAL_FILE, index=False)
    save_to_firebase(df)
    st.success("Uploaded & saved permanently ✅")

# ================= LOAD DATA =================
df = None

fb_df = load_from_firebase()
if fb_df is not None and not fb_df.empty:
    df = fb_df
    st.success("Loaded from Firebase ☁")

elif os.path.exists(LOCAL_FILE):
    df = pd.read_excel(LOCAL_FILE)
    st.info("Loaded from local file")

else:
    st.warning("Please upload file")
    st.stop()

# ================= SAFETY =================
if df is None or df.empty:
    st.stop()

st.subheader("Data Preview")
st.dataframe(df)

# ================= AUTO DETECT (NO SELECTBOX) =================
date_col, branch_col = detect_columns(df)

st.info(f"Auto Selected Date Column: {date_col}")
st.info(f"Auto Selected Branch Column: {branch_col}")

# ================= CLEAN DATE =================
df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
df = df.dropna(subset=[date_col, branch_col])

# ================= RANGE =================
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

# safe division
pivot["1-10 %"] = (pivot["1-10"] / pivot["Total"].replace(0,1) * 100).round(2)
pivot["11-20 %"] = (pivot["11-20"] / pivot["Total"].replace(0,1) * 100).round(2)
pivot["21-31 %"] = (pivot["21-31"] / pivot["Total"].replace(0,1) * 100).round(2)

result_df = pivot.reset_index()

# ================= RESULT =================
st.subheader("Recovery Summary")
st.dataframe(result_df, use_container_width=True)

# ================= SAVE =================
if st.button("🔄 Save Again to Firebase"):
    save_to_firebase(df)
    st.success("Saved again to Firebase")
