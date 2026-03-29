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
import io

import firebase_admin
from firebase_admin import credentials, firestore

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# ================= FIREBASE INIT =================
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= UI =================
st.title("Recovery System Dashboard")

# ================= LOCAL STORAGE =================
LOCAL_FOLDER = "data"
LOCAL_FILE = os.path.join(LOCAL_FOLDER, "recovery.xlsx")
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# ================= COLUMN DETECTION =================
def detect_columns(df):
    date_col = None
    branch_col = None
    area_col = None

    for col in df.columns:
        c = col.lower()

        if "date" in c:
            date_col = col
        if "branch" in c:
            branch_col = col
        if "area" in c:
            area_col = col

    return date_col, branch_col, area_col


# ================= SAFE FIREBASE SAVE =================
def save_to_firebase(df):
    try:
        df_clean = df.copy()

        # NaN fix
        df_clean = df_clean.fillna("")

        # datetime fix
        for col in df_clean.columns:
            if "datetime" in str(df_clean[col].dtype):
                df_clean[col] = df_clean[col].astype(str)

        # full safe conversion
        df_clean = df_clean.astype(str)

        data = df_clean.to_dict(orient="records")

        db.collection("recovery_summary").document("latest").set({
            "data": data
        })

        st.success("Saved to Firebase ☁")

    except Exception as e:
        st.error(f"Firebase error: {e}")


# ================= LOAD FIREBASE =================
def load_from_firebase():
    doc = db.collection("recovery_summary").document("latest").get()
    if doc.exists:
        data = doc.to_dict().get("data", [])
        return pd.DataFrame(data)
    return None


# ================= FILE UPLOAD =================
uploaded_file = st.file_uploader("Upload Excel / CSV", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df.to_excel(LOCAL_FILE, index=False)
    save_to_firebase(df)

# ================= LOAD DATA =================
df = load_from_firebase()

if df is None or df.empty:
    if os.path.exists(LOCAL_FILE):
        df = pd.read_excel(LOCAL_FILE)
    else:
        st.warning("No data found")
        st.stop()

# ================= CLEAN =================
date_col, branch_col, area_col = detect_columns(df)

df = df.fillna("")

if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

# remove invalid rows
df = df.dropna(subset=[branch_col])

# ================= RANGE =================
df["Day"] = df[date_col].dt.day if date_col else 1
df["Range"] = pd.cut(df["Day"], [0,10,20,31], labels=["1-10","11-20","21-30"])

# ================= PIVOT =================
pivot = pd.pivot_table(
    df,
    index=branch_col,
    columns="Range",
    aggfunc="size",
    fill_value=0
)

for c in ["1-10","11-20","21-30"]:
    if c not in pivot.columns:
        pivot[c] = 0

pivot["Total"] = pivot.sum(axis=1)

result_df = pivot.reset_index()

# ================= AREA JOIN =================
if area_col:
    area_map = df[[branch_col, area_col]].drop_duplicates()
    result_df = result_df.merge(area_map, on=branch_col, how="left")

# ================= ORDER FIX (AREA → BRANCH → DATA) =================
cols = result_df.columns.tolist()

ordered = []

for c in cols:
    if "area" in c.lower():
        ordered.append(c)

for c in cols:
    if "branch" in c.lower():
        ordered.append(c)

for c in cols:
    if c not in ordered:
        ordered.append(c)

result_df = result_df[ordered]

# ================= CLEAN SCREEN =================
st.subheader("Recovery Report")
st.dataframe(result_df, use_container_width=True)

# ================= EXCEL EXPORT =================
def create_excel(df):
    output = io.BytesIO()
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active

    ws.append(df.columns.tolist())

    for row in df.values.tolist():
        ws.append(row)

    # GRAND TOTAL ROW
    grand = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            grand.append(df[col].sum())
        else:
            grand.append("Grand Total")

    ws.append(grand)

    wb.save(output)
    output.seek(0)
    return output


excel_file = create_excel(result_df)

st.download_button(
    "📥 Download Excel",
    excel_file,
    "recovery.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ================= PDF WATERMARK =================
WATERMARK = "Created by M Khaleel"

class WatermarkCanvas(canvas.Canvas):
    def draw_watermark(self):
        self.saveState()
        self.setFont("Helvetica", 40)
        self.setFillColorRGB(0.9, 0.9, 0.9)
        self.translate(300, 400)
        self.rotate(45)
        self.drawCentredString(0, 0, WATERMARK)
        self.restoreState()

    def showPage(self):
        self.draw_watermark()
        super().showPage()

    def save(self):
        self.draw_watermark()
        super().save()


def create_pdf(df):
    buffer = io.BytesIO()
    pdf = SimpleDocTemplate(buffer)

    data = [df.columns.tolist()] + df.values.tolist()

    table = Table(data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.whitesmoke),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))

    pdf.build([Spacer(1,10), table], canvasmaker=WatermarkCanvas)

    buffer.seek(0)
    return buffer


pdf_file = create_pdf(result_df)

st.download_button(
    "📄 Download PDF",
    pdf_file,
    "recovery.pdf",
    "application/pdf"
)

# ================= MANUAL SAVE =================
if st.button("🔄 Save Again"):
    save_to_firebase(df)
