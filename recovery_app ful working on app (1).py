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

# ================= FIREBASE =================
import firebase_admin
from firebase_admin import credentials, firestore

# ================= PDF =================
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# ================= INIT FIREBASE =================
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

# ================= AUTO DETECT =================
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

    if date_col is None:
        date_col = df.columns[0]

    if branch_col is None:
        branch_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

    return date_col, branch_col, area_col


# ================= FIREBASE LOAD =================
def load_from_firebase():
    doc = db.collection("recovery_summary").document("latest").get()
    if doc.exists:
        data = doc.to_dict().get("data", [])
        return pd.DataFrame(data) if data else None
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
    st.success("Uploaded & saved successfully ✅")

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
    st.warning("Please upload file first")
    st.stop()

# ================= VALIDATION =================
if df is None or df.empty:
    st.stop()

# ================= AUTO COLUMNS =================
date_col, branch_col, area_col = detect_columns(df)

# ================= CLEAN =================
df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
df = df.dropna(subset=[date_col, branch_col])

# ================= RANGE =================
df["Day"] = df[date_col].dt.day
df["Range"] = pd.cut(df["Day"], bins=[0,10,20,31], labels=["1-10","11-20","21-30"])

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

pivot["1-10 %"] = (pivot["1-10"] / pivot["Total"].replace(0,1) * 100).round(2)
pivot["11-20 %"] = (pivot["11-20"] / pivot["Total"].replace(0,1) * 100).round(2)
pivot["21-30 %"] = (pivot["21-30"] / pivot["Total"].replace(0,1) * 100).round(2)

result_df = pivot.reset_index()

# ================= ADD AREA =================
if area_col:
    area_map = df[[branch_col, area_col]].drop_duplicates()
    result_df = result_df.merge(area_map, on=branch_col, how="left")

# ================= COLUMN ORDER FIX =================
cols = result_df.columns.tolist()

ordered_cols = []

# Area first
for c in cols:
    if "area" in c.lower():
        ordered_cols.append(c)

# Branch second
for c in cols:
    if "branch" in c.lower():
        ordered_cols.append(c)

# rest
for c in cols:
    if c not in ordered_cols:
        ordered_cols.append(c)

result_df = result_df[ordered_cols]

# ================= CLEAN SCREEN OUTPUT =================
st.subheader("Recovery Summary")
st.dataframe(result_df, use_container_width=True)

# ================= WATERMARK =================
WATERMARK = "Created by M Khaleel"

# ================= EXCEL WITH GRAND TOTAL =================
import openpyxl
from openpyxl import Workbook

def create_excel(df):
    output = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = "Recovery Summary"

    ws.append(df.columns.tolist())

    numeric_cols = df.select_dtypes(include="number").columns

    for _, row in df.iterrows():
        ws.append(list(row))

    # GRAND TOTAL LAST ROW
    grand = []
    for col in df.columns:
        if col in numeric_cols:
            grand.append(df[col].sum())
        else:
            grand.append("Grand Total")

    ws.append(grand)

    wb.save(output)
    output.seek(0)
    return output


excel_buffer = create_excel(result_df)

st.download_button(
    "📥 Download Excel",
    excel_buffer,
    "recovery_summary.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ================= PDF WATERMARK =================
class WatermarkCanvas(canvas.Canvas):
    def draw_watermark(self):
        self.saveState()
        self.setFont("Helvetica", 45)
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

    table_data = [df.columns.tolist()] + df.values.tolist()

    table = Table(table_data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    pdf.build([Spacer(1, 10), table], canvasmaker=WatermarkCanvas)

    buffer.seek(0)
    return buffer


pdf_buffer = create_pdf(result_df)

st.download_button(
    "📄 Download PDF",
    pdf_buffer,
    "recovery_summary.pdf",
    "application/pdf"
)

# ================= SAVE =================
if st.button("🔄 Save Again Firebase"):
    save_to_firebase(df)
    st.success("Saved successfully ☁")
import streamlit as st
import pandas as pd
import io

import firebase_admin
from firebase_admin import credentials, firestore

# ================= FIREBASE INIT =================
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= LOAD FROM FIREBASE =================
def load_data():
    doc = db.collection("recovery_data").document("records").get()
    if doc.exists:
        data = doc.to_dict().get("data", [])
        return pd.DataFrame(data)
    return pd.DataFrame()

# ================= SAVE TO FIREBASE =================
def save_data(df):
    df_clean = df.fillna("").astype(str)
    db.collection("recovery_data").document("records").set({
        "data": df_clean.to_dict(orient="records")
    })

# ================= SAMPLE / LOAD DATA =================
df = load_data()

if df.empty:
    df = pd.DataFrame(columns=[
        "Sr","Name","Parentage","CNIC","Mobile",
        "Address","Amount","Received By","Branch"
    ])

st.title("Recovery MIS System")

# ================= INPUT FORM =================
st.subheader("Add New Record")

with st.form("entry_form"):
    sr = st.number_input("Sr", step=1)
    name = st.text_input("Name")
    parentage = st.text_input("Parentage")
    cnic = st.text_input("CNIC")
    mobile = st.text_input("Mobile")
    address = st.text_input("Address")
    amount = st.number_input("Amount", step=1)
    received_by = st.text_input("Received By")
    branch = st.text_input("Branch")

    submit = st.form_submit_button("Save")

if submit:
    new_row = pd.DataFrame([{
        "Sr": sr,
        "Name": name,
        "Parentage": parentage,
        "CNIC": cnic,
        "Mobile": mobile,
        "Address": address,
        "Amount": amount,
        "Received By": received_by,
        "Branch": branch
    }])

    df = pd.concat([df, new_row], ignore_index=True)
    save_data(df)
    st.success("Saved to Firebase ☁")

# ================= FILTER =================
st.subheader("Filters")

branches = ["All"] + sorted(df["Branch"].dropna().unique().tolist()) if not df.empty else ["All"]
selected_branch = st.selectbox("Select Branch", branches)

search = st.text_input("Search (Name / CNIC / Mobile)")

filtered_df = df.copy()

if selected_branch != "All":
    filtered_df = filtered_df[filtered_df["Branch"] == selected_branch]

if search:
    search = search.lower()
    filtered_df = filtered_df[
        filtered_df.astype(str).apply(
            lambda row: row.str.lower().str.contains(search).any(),
            axis=1
        )
    ]

# ================= DISPLAY =================
st.subheader("Records")
st.dataframe(filtered_df, use_container_width=True)

# ================= EXCEL DOWNLOAD =================
def to_excel(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Recovery")
    output.seek(0)
    return output

excel_file = to_excel(filtered_df)

st.download_button(
    "📥 Download Excel",
    excel_file,
    "recovery_data.xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
