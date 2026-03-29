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

# ================= MUST BE THE VERY FIRST STREAMLIT COMMAND =================
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
        st.error(f"Firebase init failed: {e}")
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
    except:
        pass
    return None

def save_to_firebase(df):
    try:
        safe_df = df.astype(str).replace(["nan", "NaT"], "")
        db.collection("recovery_summary").document("latest").set({
            "data": safe_df.to_dict(orient="records")
        })
    except:
        pass

# ================= FILE UPLOAD =================
uploaded_file = st.file_uploader("Upload Recovery Excel or CSV", type=["xlsx", "csv"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df_upload = pd.read_csv(uploaded_file)
        else:
            df_upload = pd.read_excel(uploaded_file)

        df_upload.to_excel(LOCAL_FILE, index=False)
        save_to_firebase(df_upload)
        st.success("✅ File uploaded and saved successfully")
    except Exception as e:
        st.error(f"File read error: {e}")

# ================= LOAD DATA =================
df = None
fb_df = load_from_firebase()

if fb_df is not None and not fb_df.empty:
    df = fb_df
    st.success("☁️ Loaded from Firebase")
elif os.path.exists(LOCAL_FILE):
    try:
        df = pd.read_excel(LOCAL_FILE)
        st.info("📁 Loaded from local file")
    except:
        st.warning("Local file corrupt")
else:
    st.warning("⚠️ Please upload your Recovery file (Excel/CSV)")
    st.stop()

if df is None or df.empty:
    st.warning("No data available")
    st.stop()

# ================= COLUMN SELECTION =================
st.subheader("Column Selection")
cols = list(df.columns)
st.write("**Available Columns:**", cols)

date_default = next((i for i, c in enumerate(cols) if "recovery_date" in str(c).lower() or "date" in str(c).lower()), 0)
branch_default = next((i for i, c in enumerate(cols) if "name" in str(c).lower()), 1)

date_col = st.selectbox("Select **Date Column**", cols, index=date_default, key="date_key")
branch_col = st.selectbox("Select **Branch Column**", cols, index=branch_default, key="branch_key")

area_col = next((c for c in ["area_id", "region_id"] if c in cols), None)

# ================= PROCESSING =================
try:
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col].astype(str).str.strip(), errors='coerce')
    df = df.dropna(subset=[date_col, branch_col]).copy()

    df["Day"] = df[date_col].dt.day
    df = df[(df["Day"] >= 1) & (df["Day"] <= 31)]

    df["Range"] = pd.cut(df["Day"], bins=[0,10,20,31], labels=["1-10","11-20","21-31"], include_lowest=True)

    pivot = pd.pivot_table(df, index=branch_col, columns="Range", aggfunc="size", fill_value=0)

    for c in ["1-10", "11-20", "21-31"]:
        if c not in pivot.columns:
            pivot[c] = 0

    pivot["Total"] = pivot.sum(axis=1)

    for c in ["1-10", "11-20", "21-31"]:
        pivot[f"{c} %"] = (pivot[c] / pivot["Total"] * 100).round(2)

    pivot.rename(columns={"1-10": "Recovery 1-10", "11-20": "Recovery 11-20", "21-31": "Recovery 21-31"}, inplace=True)

    result_df = pivot.reset_index()

    # Add Area
    if area_col:
        area_map = df[[branch_col, area_col]].drop_duplicates()
        result_df = result_df.merge(area_map, on=branch_col, how="left")
        # Move area column after branch
        cols_list = list(result_df.columns)
        if area_col in cols_list:
            area_idx = cols_list.index(area_col)
            branch_idx = cols_list.index(branch_col)
            cols_list.insert(branch_idx + 1, cols_list.pop(area_idx))
            result_df = result_df[cols_list]

    # Grand Total
    numeric = ["Recovery 1-10", "Recovery 11-20", "Recovery 21-31", "Total"]
    grand = result_df[numeric].sum()

    grand_row = {col: "" for col in result_df.columns}
    grand_row[branch_col] = "Grand Total"
    if area_col:
        grand_row[area_col] = ""
    for col in numeric:
        grand_row[col] = grand[col]
    for c in ["1-10", "11-20", "21-31"]:
        if f"{c} %" in grand_row and grand["Total"] > 0:
            grand_row[f"{c} %"] = round(grand[f"Recovery {c}"] / grand["Total"] * 100, 2)

    result_df = pd.concat([result_df, pd.DataFrame([grand_row])], ignore_index=True)

except Exception as e:
    st.error(f"Error in processing: {e}")
    st.stop()

# ================= DISPLAY =================
st.subheader("📊 Branch Wise Recovery Summary")
st.dataframe(result_df, use_container_width=True, height=650)

# Downloads
c1, c2 = st.columns(2)
with c1:
    st.download_button("⬇ Download CSV", result_df.to_csv(index=False).encode("utf-8"), "recovery_summary.csv", "text/csv")

with c2:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        data = [result_df.columns.tolist()] + result_df.values.tolist()
        t = Table(data)
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
        ]))
        doc.build([t])
        st.download_button("⬇ Download PDF", buffer.getvalue(), "recovery_summary.pdf", "application/pdf")
        buffer.close()
    except:
        pass

if st.button("🔄 Save to Firebase"):
    save_to_firebase(df)
    st.success("Saved to Firebase")
