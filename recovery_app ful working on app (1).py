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

# ================= FIREBASE =================
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= PAGE CONFIG =================
st.set_page_config(page_title="Recovery Date Range Summary", layout="wide")
st.title("🔄 Recovery Date Range Summary")

# ================= LOCAL STORAGE =================
LOCAL_FOLDER = "data"
LOCAL_FILE = os.path.join(LOCAL_FOLDER, "recovery.xlsx")
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# ================= FIREBASE FUNCTIONS =================
def load_from_firebase():
    doc = db.collection("recovery_summary").document("latest").get()
    if doc.exists:
        data = doc.to_dict().get("data", [])
        if data:
            return pd.DataFrame(data)
    return None

def save_to_firebase(df):
    safe_df = df.astype(str).replace("nan", "").replace("NaT", "")
    db.collection("recovery_summary").document("latest").set({
        "data": safe_df.to_dict(orient="records")
    })

# ================= FILE UPLOAD =================
uploaded_file = st.file_uploader("Upload Recovery Excel or CSV", 
                                 type=["xlsx", "csv"], 
                                 help="Upload your recovery data file")

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        df.to_excel(LOCAL_FILE, index=False)
        save_to_firebase(df)
        st.success("✅ File uploaded and saved permanently to Firebase & Local storage")
    except Exception as e:
        st.error(f"Error reading file: {e}")

# ================= LOAD DATA =================
df = None

fb_df = load_from_firebase()
if fb_df is not None and not fb_df.empty:
    df = fb_df
    st.success("☁️ Loaded latest data from Firebase")
elif os.path.exists(LOCAL_FILE):
    df = pd.read_excel(LOCAL_FILE)
    st.info("📁 Loaded from local backup")
else:
    st.warning("⚠️ No data available. Please upload a file.")
    st.stop()

# ================= SAFETY CHECK =================
if df is None or df.empty:
    st.warning("No data available")
    st.stop()

# ================= COLUMN SELECTION (FIXED) =================
st.subheader("Column Selection")

cols = list(df.columns)
st.write("**Available Columns:**", cols)

# Smart default detection
date_default = 0
if "recovery_date" in cols:
    date_default = cols.index("recovery_date")
elif any("date" in c.lower() for c in cols):
    for i, c in enumerate(cols):
        if "date" in c.lower():
            date_default = i
            break

branch_default = 0
if "Name" in cols:
    branch_default = cols.index("Name")
elif "branch" in " ".join(cols).lower():
    for i, c in enumerate(cols):
        if "name" in c.lower() or "branch" in c.lower():
            branch_default = i
            break

# Date Column
date_col = st.selectbox(
    "Select **Date Column**", 
    cols, 
    index=date_default,
    key="date_col_key"   # Unique key - yeh masla solve karega
)

# Branch Column
branch_col = st.selectbox(
    "Select **Branch Column** (branch name or id)", 
    cols, 
    index=branch_default,
    key="branch_col_key"   # Unique key - important
)

# Area Column
area_col = None
area_options = [c for c in cols if c in ["area_id", "region_id"]]
if area_options:
    area_col = area_options[0]  # pehle area_id phir region_id

# ================= DATA PROCESSING =================
try:
    # Convert date
    df[date_col] = pd.to_datetime(df[date_col].astype(str).str.strip(), errors='coerce')
    
    # Drop invalid rows
    df = df.dropna(subset=[date_col, branch_col]).copy()
    df["Day"] = df[date_col].dt.day
    
    # Filter valid days
    df = df[(df["Day"] >= 1) & (df["Day"] <= 31)]

    if df.empty:
        st.error("No valid dates found in the selected date column.")
        st.stop()

    # Create Range (1-10, 11-20, 21-31)
    df["Range"] = pd.cut(df["Day"], 
                        bins=[0, 10, 20, 31], 
                        labels=["1-10", "11-20", "21-31"],
                        include_lowest=True)

    # ================= PIVOT TABLE =================
    pivot = pd.pivot_table(
        df,
        index=[branch_col],
        columns="Range",
        aggfunc="size",
        fill_value=0
    )

    # Ensure all columns exist
    for c in ["1-10", "11-20", "21-31"]:
        if c not in pivot.columns:
            pivot[c] = 0

    pivot["Total"] = pivot.sum(axis=1)

    # Calculate percentages
    for c in ["1-10", "11-20", "21-31"]:
        pivot[f"{c} %"] = (pivot[c] / pivot["Total"] * 100).round(2)

    # Rename for better display
    pivot.rename(columns={
        "1-10": "Recovery 1-10",
        "11-20": "Recovery 11-20",
        "21-31": "Recovery 21-31"
    }, inplace=True)

    result_df = pivot.reset_index()

    # ================= ADD AREA COLUMN =================
    if area_col and area_col in df.columns:
        branch_area_map = df[[branch_col, area_col]].drop_duplicates()
        result_df = result_df.merge(branch_area_map, on=branch_col, how='left')
        
        # Move area column right after branch column
        cols_order = result_df.columns.tolist()
        if area_col in cols_order:
            area_idx = cols_order.index(area_col)
            branch_idx = cols_order.index(branch_col)
            cols_order.insert(branch_idx + 1, cols_order.pop(area_idx))
            result_df = result_df[cols_order]

    # ================= GRAND TOTAL ROW =================
    numeric_cols = ["Recovery 1-10", "Recovery 11-20", "Recovery 21-31", "Total"]
    grand_counts = result_df[numeric_cols].sum()

    grand_row = {col: "" for col in result_df.columns}
    grand_row[branch_col] = "Grand Total"
    if area_col and area_col in grand_row:
        grand_row[area_col] = ""

    for col in numeric_cols:
        if col in grand_row:
            grand_row[col] = grand_counts[col]

    for c in ["1-10", "11-20", "21-31"]:
        pct_col = f"{c} %"
        if pct_col in grand_row and grand_counts["Total"] > 0:
            grand_row[pct_col] = round((grand_counts[f"Recovery {c}"] / grand_counts["Total"] * 100), 2)

    result_df = pd.concat([result_df, pd.DataFrame([grand_row])], ignore_index=True)

except Exception as e:
    st.error(f"Processing Error: {str(e)}")
    st.stop()

# ================= DISPLAY =================
st.subheader("📊 Branch Wise Recovery Summary")
st.dataframe(result_df, use_container_width=True, height=650)

# ================= DOWNLOADS =================
col1, col2 = st.columns(2)

with col1:
    csv = result_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download CSV",
        data=csv,
        file_name="recovery_summary.csv",
        mime="text/csv"
    )

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
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
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
    except ImportError:
        st.info("For PDF download: pip install reportlab")

# ================= SAVE BUTTON =================
if st.button("🔄 Save Current Data to Firebase"):
    save_to_firebase(df)
    st.success("✅ Data saved to Firebase successfully")
