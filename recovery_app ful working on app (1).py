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

# ---------------- FIREBASE ----------------
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------- PAGE ----------------
st.title("Recovery Date Range Summary")

# ---------------- Local storage folder ----------------
LOCAL_FOLDER = "data"
LOCAL_FILE = os.path.join(LOCAL_FOLDER, "recovery.xlsx")
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# ---------------- File Upload ----------------
uploaded_file = st.file_uploader("Upload Recovery Excel / CSV", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.session_state["df"] = df
        df.to_excel(LOCAL_FILE, index=False)
        st.success("File uploaded and saved locally!")
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

# ---------------- Load from session or local file ----------------
elif "df" in st.session_state:
    df = st.session_state["df"]
    st.info("Using previously uploaded file from session.")

elif os.path.exists(LOCAL_FILE):
    try:
        df = pd.read_excel(LOCAL_FILE)
        st.session_state["df"] = df
        st.info("Loaded previously saved file from local storage.")
    except Exception as e:
        st.error(f"Error loading local file: {e}")
        st.stop()

else:
    st.info("Please upload a recovery file to proceed.")
    st.stop()

# ---------------- Column Selection ----------------
st.subheader("Available Columns")
st.write(list(df.columns))

date_col = st.selectbox("Select Date Column", df.columns)
branch_col = st.selectbox("Select Branch Column (branch_id)", df.columns)
area_col = None

if 'area_id' in df.columns:
    area_col = 'area_id'

# ---------------- Date Processing ----------------
df[date_col] = pd.to_datetime(df[date_col].astype(str).str.strip(), errors='coerce')
df = df.dropna(subset=[date_col, branch_col])

df["Day"] = df[date_col].dt.day
df = df[df["Day"].notna()]

df["Range"] = pd.cut(df["Day"], bins=[0,10,20,31], labels=["1-10","11-20","21-31"])

if df["Range"].isna().all():
    st.error("Date column format not recognized.")
    st.stop()

# ---------------- Pivot ----------------
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

# ---------------- Area Merge ----------------
if area_col:
    branch_area_df = df[[branch_col, area_col]].drop_duplicates()
    result_df = result_df.merge(branch_area_df, on=branch_col, how='left')

    cols = result_df.columns.tolist()
    branch_idx = cols.index(branch_col)
    cols.insert(branch_idx, cols.pop(cols.index(area_col)))
    result_df = result_df[cols]

# ---------------- Grand Total ----------------
numeric_cols = ["Recovery 1-10","Recovery 11-20","Recovery 21-31","Total"]

grand_total_counts = result_df[numeric_cols].sum()
grand_total_percent = (
    grand_total_counts[["Recovery 1-10","Recovery 11-20","Recovery 21-31"]] /
    grand_total_counts["Total"] * 100
).round(2)

grand_values = {}

for col in result_df.columns:
    if col == branch_col:
        grand_values[col] = "Grand Total"
    elif col == area_col:
        grand_values[col] = ""
    elif col in numeric_cols:
        grand_values[col] = grand_total_counts[col]
    elif col in ["1-10 %","11-20 %","21-31 %"]:
        map_col = {
            "1-10 %":"Recovery 1-10",
            "11-20 %":"Recovery 11-20",
            "21-31 %":"Recovery 21-31"
        }
        grand_values[col] = grand_total_percent[map_col[col]]
    else:
        grand_values[col] = ""

result_df = pd.concat([result_df, pd.DataFrame([grand_values])], ignore_index=True)

# ---------------- DISPLAY ----------------
st.subheader("Branch Wise Recovery Summary")
st.dataframe(result_df)

# ---------------- FIREBASE AUTO SAVE ----------------
if st.button("💾 Save to Firebase"):

    for _, row in result_df.iterrows():
        db.collection("recovery_summary").add(row.to_dict())

    st.success("Saved to Firebase successfully ✅")

# ---------------- FIREBASE LOAD ----------------
st.subheader("☁ Firebase Stored Data")

docs = db.collection("recovery_summary").stream()

firebase_data = [doc.to_dict() for doc in docs]

if firebase_data:
    st.dataframe(pd.DataFrame(firebase_data))

# ---------------- DOWNLOAD CSV ----------------
csv = result_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇ Download CSV",
    data=csv,
    file_name="recovery_summary.csv",
    mime="text/csv"
)

# ---------------- PDF ----------------
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
