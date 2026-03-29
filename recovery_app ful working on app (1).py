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

# ================= FIREBASE LOAD =================
def load_from_firebase():
    doc = db.collection("recovery_summary").document("latest").get()
    if doc.exists:
        data = doc.to_dict().get("data", [])
        if data:
            return pd.DataFrame(data)
    return None

# ================= FIREBASE SAVE =================
def save_to_firebase(df):
    safe_df = df.astype(str).replace("nan", "")
    db.collection("recovery_summary").document("latest").set({
        "data": safe_df.to_dict(orient="records")
    })

# ================= FILE UPLOAD =================
uploaded_file = st.file_uploader("Upload Recovery Excel / CSV", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.to_excel(LOCAL_FILE, index=False)
    save_to_firebase(df)

    st.success("File uploaded & saved permanently ✅")

# ================= AUTO LOAD =================
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
    st.warning("No data available")
    st.stop()

# ================= SHOW =================
st.subheader("Data Preview")
st.dataframe(df)


# force stable default index (NO session_state bug)
cols = list(df.columns)

default_date_index = 0
default_branch_index = 1 if len(cols) > 1 else 0

# ---------------- Column Selection ----------------
st.subheader("Available Columns")
st.write(list(df.columns))

date_col = st.selectbox("Select Date Column", df.columns)
branch_col = st.selectbox("Select Branch Column (branch_id)", df.columns)
area_col = None
if 'area_id' in df.columns:
    area_col = 'area_id'

# ---------------- Convert Date & Create Day/Range ----------------
df[date_col] = pd.to_datetime(df[date_col].astype(str).str.strip(), errors='coerce')
df = df.dropna(subset=[date_col, branch_col])
df["Day"] = df[date_col].dt.day
df = df[df["Day"].notna()]

df["Range"] = pd.cut(df["Day"], bins=[0,10,20,31], labels=["1-10","11-20","21-31"])
if df["Range"].isna().all():
    st.error("Date column format not recognized.")
    st.stop()

# ---------------- Pivot Table ----------------
try:
    pivot = pd.pivot_table(
        df,
        index=[branch_col],
        columns="Range",
        aggfunc="size",
        fill_value=0
    )
except KeyError as e:
    st.error(f"Pivot error: {e}")
    st.stop()

# Ensure columns exist
for c in ["1-10","11-20","21-31"]:
    if c not in pivot.columns:
        pivot[c] = 0

pivot["Total"] = pivot[["1-10","11-20","21-31"]].sum(axis=1)
pivot["1-10 %"] = (pivot["1-10"] / pivot["Total"] * 100).round(2)
pivot["11-20 %"] = (pivot["11-20"] / pivot["Total"] * 100).round(2)
pivot["21-31 %"] = (pivot["21-31"] / pivot["Total"] * 100).round(2)

pivot.rename(columns={
    "1-10": "Recovery 1-10",
    "11-20": "Recovery 11-20",
    "21-31": "Recovery 21-31"
}, inplace=True)

result_df = pivot.reset_index()

# ---------------- Add Area column BEFORE Branch ----------------
if area_col:
    branch_area_df = df[[branch_col, area_col]].drop_duplicates()
    result_df = result_df.merge(branch_area_df, on=branch_col, how='left')
    cols = result_df.columns.tolist()
    branch_idx = cols.index(branch_col)
    cols.insert(branch_idx, cols.pop(cols.index(area_col)))
    result_df = result_df[cols]

# ---------------- Grand Total Row ----------------
numeric_cols = ["Recovery 1-10","Recovery 11-20","Recovery 21-31","Total"]
grand_total_counts = result_df[numeric_cols].sum()
grand_total_percent = (grand_total_counts[["Recovery 1-10","Recovery 11-20","Recovery 21-31"]] / grand_total_counts["Total"] * 100).round(2)

grand_values = {}
for col in result_df.columns:
    if col == branch_col:
        grand_values[col] = "Grand Total"
    elif col == area_col:
        grand_values[col] = ""
    elif col in numeric_cols:
        grand_values[col] = grand_total_counts[col]
    elif col in ["1-10 %","11-20 %","21-31 %"]:
        pct_map = {"1-10 %":"Recovery 1-10","11-20 %":"Recovery 11-20","21-31 %":"Recovery 21-31"}
        grand_values[col] = grand_total_percent[pct_map[col]]
    else:
        grand_values[col] = ""

result_df = pd.concat([result_df, pd.DataFrame([grand_values])], ignore_index=True)

# ---------------- Display Table ----------------
st.subheader("Branch Wise Recovery Summary")
st.dataframe(result_df)

# ---------------- CSV Download ----------------
csv = result_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇ Download CSV",
    data=csv,
    file_name="recovery_summary.csv",
    mime="text/csv"
)

# ---------------- PDF Download ----------------
buffer = BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=A4)
table_data = [result_df.columns.tolist()] + result_df.values.tolist()

table = Table(table_data)
style = TableStyle([
    ('GRID', (0,0), (-1,-1), 1, colors.black),
    ('BACKGROUND', (0,0), (-1,0), colors.grey),
    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('FONTSIZE', (0,0), (-1,-1), 10),
    ('BOTTOMPADDING', (0,0), (-1,0), 6),
])
table.setStyle(style)
doc.build([table])
pdf_bytes = buffer.getvalue()
buffer.close()

st.download_button(
    label="⬇ Download PDF",
    data=pdf_bytes,
    file_name="recovery_summary.pdf",
    mime="application/pdf"
)
# ================= SAVE BUTTON =================
if st.button("🔄 Save Again to Firebase"):
    save_to_firebase(df)
    st.success("Saved again to Firebase")
