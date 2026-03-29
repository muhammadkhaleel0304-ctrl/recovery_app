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

# ================= PAGE CONFIG (MUST BE FIRST) =================
st.set_page_config(
    page_title="Recovery Date Range Summary",
    layout="wide",
    page_icon="🔄"
)

# ================= TITLE =================
st.title("🔄 Recovery Date Range Summary")

# ================= FIREBASE =================
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase initialization failed: {e}")
        st.stop()

db = firestore.client()

# ================= LOCAL STORAGE =================
LOCAL_FOLDER = "data"
LOCAL_FILE = os.path.join(LOCAL_FOLDER, "recovery.xlsx")
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# ================= FIREBASE FUNCTIONS =================
def load_from_firebase():
    try:
        doc = db.collection("recovery_summary").document("latest").get()
        if doc.exists:
            data = doc.to_dict().get("data", [])
            if data:
                return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Firebase load failed: {e}")
    return None

def save_to_firebase(df):
    try:
        safe_df = df.astype(str).replace("nan", "").replace("NaT", "")
        db.collection("recovery_summary").document("latest").set({
            "data": safe_df.to_dict(orient="records")
        })
    except Exception as e:
        st.warning(f"Firebase save failed: {e}")

# ================= FILE UPLOAD =================
uploaded_file = st.file_uploader("Upload Recovery Excel or CSV", 
                                 type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df.to_excel(LOCAL_FILE, index=False)
        save_to_firebase(df)
        st.success("✅ File uploaded and saved permanently")
    except Exception as e:
        st.error(f"Error reading file: {e}")

# ================= LOAD DATA =================
df = None

fb_df = load_from_firebase()
if fb_df is not None and not fb_df.empty:
    df = fb_df
    st.success("☁️ Loaded from Firebase")
elif os.path.exists(LOCAL_FILE):
    try:
        df = pd.read_excel(LOCAL_FILE)
        st.info("📁 Loaded from local backup")
    except Exception as e:
        st.error(f"Local file error: {e}")
else:
    st.warning("⚠️ No data found. Please upload an Excel or CSV file.")
    st.stop()

# ================= SAFETY CHECK =================
if df is None or df.empty:
    st.warning("No data available")
    st.stop()

# ================= COLUMN SELECTION =================
st.subheader("Column Selection")

cols = list(df.columns)
st.write("**Available Columns:**", cols)

# Smart defaults
date_default = next((i for i, c in enumerate(cols) if "recovery_date" in c.lower() or "date" in c.lower()), 0)
branch_default = next((i for i, c in enumerate(cols) if "name" in c.lower() or "branch" in c.lower()), 1)

date_col = st.selectbox(
    "Select **Date Column**", 
    cols, 
    index=date_default,
    key="date_col_key"
)

branch_col = st.selectbox(
    "Select **Branch Column** (Name / branch_id)", 
    cols, 
    index=branch_default,
    key="branch_col_key"
)

# Area Column
area_col = None
for possible in ["area_id", "region_id"]:
    if possible in cols:
        area_col = possible
        break

# ================= DATA PROCESSING =================
try:
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col].astype(str).str.strip(), errors='coerce')
    df = df.dropna(subset=[date_col, branch_col])
    
    df["Day"] = df[date_col].dt.day
    df = df[(df["Day"] >= 1) & (df["Day"] <= 31)]

    if df.empty:
        st.error("No valid dates found.")
        st.stop()

    df["Range"] = pd.cut(df["Day"], bins=[0, 10, 20, 31], 
                        labels=["1-10", "11-20", "21-31"], include_lowest=True)

    # Pivot Table
    pivot = pd.pivot_table(
        df, index=branch_col, columns="Range", aggfunc="size", fill_value=0
    )

    for c in ["1-10", "11-20", "21-31"]:
        if c not in pivot.columns:
            pivot[c] = 0

    pivot["Total"] = pivot.sum(axis=1)

    for c in ["1-10", "11-20", "21-31"]:
        pivot[f"{c} %"] = (pivot[c] / pivot["Total"] * 100).round(2)

    pivot.rename(columns={
        "1-10": "Recovery 1-10",
        "11-20": "Recovery 11-20",
        "21-31": "Recovery 21-31"
    }, inplace=True)

    result_df = pivot.reset_index()

    # Add Area Column
    if area_col and area_col in df.columns:
        area_map = df[[branch_col, area_col]].drop_duplicates()
        result_df = result_df.merge(area_map, on=branch_col, how='left')
        
        # Move area right after branch
        cols_list = result_df.columns.tolist()
        if area_col in cols_list:
            area_idx = cols_list.index(area_col)
            branch_idx = cols_list.index(branch_col)
            cols_list.insert(branch_idx + 1, cols_list.pop(area_idx))
            result_df = result_df[cols_list]

    # Grand Total
    numeric_cols = ["Recovery 1-10", "Recovery 11-20", "Recovery 21-31", "Total"]
    grand = result_df[numeric_cols].sum()

    grand_row = {col: "" for col in result_df.columns}
    grand_row[branch_col] = "Grand Total"
    if area_col:
        grand_row[area_col] = ""

    for col in numeric_cols:
        grand_row[col] = grand[col]

    for c in ["1-10", "11-20", "21-31"]:
        pct = f"{c} %"
        if pct in grand_row and grand["Total"] > 0:
            grand_row[pct] = round(grand[f"Recovery {c}"] / grand["Total"] * 100, 2)

    result_df = pd.concat([result_df, pd.DataFrame([grand_row])], ignore_index=True)

except Exception as e:
    st.error(f"Processing Error: {str(e)}")
    st.stop()

# ================= DISPLAY RESULT =================
st.subheader("📊 Branch Wise Recovery Summary")
st.dataframe(result_df, use_container_width=True, height=650)

# ================= DOWNLOADS =================
col1, col2 = st.columns(2)

with col1:
    csv = result_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Download CSV", csv, "recovery_summary.csv", "text/csv")

with col2:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        table_data = [result_df.columns.tolist()] + result_df.values.tolist()

        table = Table(table_data)
        style = TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey)
        ])
        table.setStyle(style)
        doc.build([table])
        pdf_bytes = buffer.getvalue()
        buffer.close()

        st.download_button("⬇ Download PDF", pdf_bytes, "recovery_summary.pdf", "application/pdf")
    except:
        st.info("PDF support requires `reportlab` package.")

# ================= SAVE TO FIREBASE =================
if st.button("🔄 Save Current Data to Firebase"):
    save_to_firebase(df)
    st.success("✅ Saved to Firebase successfully")
