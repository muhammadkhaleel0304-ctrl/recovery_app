import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ================= PAGE =================
st.set_page_config(page_title="Recovery System", layout="wide")
st.title("🔥 Recovery MIS System - Admin Panel")

# ================= FIREBASE INIT =================
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["gcp_service_account"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= FULL RESET BUTTON =================
st.warning("⚠️ This will delete ALL Firebase data permanently")

if st.button("🗑️ FULL RESET SYSTEM"):

    try:
        # ---------------- MAIN DATA ----------------
        docs = db.collection("main_data").stream()
        for d in docs:
            d.reference.delete()

        # ---------------- LOCKED DATA ----------------
        docs = db.collection("locked_data").stream()
        for d in docs:
            d.reference.delete()

        # ---------------- RECOVERY SUMMARY ----------------
        docs = db.collection("recovery_summary").stream()
        for d in docs:
            d.reference.delete()

        # ---------------- OPTIONAL CLEAN DOC ----------------
        try:
            db.collection("main_data").document("all").delete()
        except:
            pass

        st.cache_data.clear()

        st.success("🔥 SYSTEM RESET COMPLETE - ALL DATA DELETED")
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
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

# ================= LOAD =================
def load_data():
    doc = db.collection("recovery_data").document("records").get()
    if doc.exists:
        data = doc.to_dict().get("data", [])
        return pd.DataFrame(data)
    return pd.DataFrame(columns=[
        "Sr","Name","Parentage","CNIC","Mobile",
        "Address","Amount","Received By","Branch"
    ])

# ================= SAVE =================
def save_data(df):
    df_clean = df.fillna("").astype(str)
    db.collection("recovery_data").document("records").set({
        "data": df_clean.to_dict(orient="records")
    })

df = load_data()

DELETE_PASSWORD = "123456789"

# ================= HEADER =================
st.title("📊 Recovery MIS System")

# ================= EXPANDABLE MAIN SYSTEM =================
with st.expander("📂 Recovery MIS System (Click to Expand / Close)", expanded=True):

    st.subheader("➕ Add Record")

    with st.form("add_form"):
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
    st.subheader("🔍 Search & Filter")

    branches = ["All"] + sorted(df["Branch"].dropna().unique().tolist()) if not df.empty else ["All"]
    branch = st.selectbox("Branch", branches)

    search = st.text_input("Search")

    filtered = df.copy()

    if branch != "All":
        filtered = filtered[filtered["Branch"] == branch]

    if search:
        filtered = filtered[
            filtered.astype(str).apply(
                lambda row: row.str.contains(search, case=False).any(),
                axis=1
            )
        ]

    # ================= RECORDS =================
    st.subheader("📋 Records")
    st.dataframe(filtered, use_container_width=True)

# ================= ALWAYS VISIBLE PART =================

st.subheader("🗑 Delete Record")

delete_cnic = st.text_input("Enter CNIC")
password = st.text_input("Password", type="password")

if st.button("Delete"):
    if password == DELETE_PASSWORD:
        df = df[df["CNIC"] != delete_cnic]
        save_data(df)
        st.success("Deleted ✅")
    else:
        st.error("Wrong password ❌")

def to_excel(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False)
    output.seek(0)
    return output

st.download_button(
    "📥 Download Excel",
    to_excel(df),
    "recovery.xlsx"
)
st.markdown("""
    <h1 style='text-align: center; color: White;'>📊 Welcome to Recovery Portal Created By:M.Khaleel</h1>
    <h3 style='text-align: center; color: Yellow;'>Recovery and Overdue Portal</h3>
    <hr style='border-top: 3px solid #bbb;'>
""", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import os
import zipfile
from fpdf import FPDF

# ⚠️ MUST be first Streamlit command

st.title("📊 Excel Cleaner + Branch-wise PDF Generator")

# Upload Excel file
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)

        st.subheader("📋 Original Data")
        st.dataframe(df, use_container_width=True)

        # Clean column names
        df.columns = df.columns.astype(str).str.strip()

        columns = list(df.columns)

        # Remove columns option
        st.subheader("❌ Remove Columns")
        remove_columns = st.multiselect("Select columns to REMOVE", columns)

        if remove_columns:
            df = df.drop(columns=remove_columns)

        st.subheader("✅ Cleaned Data")
        st.dataframe(df, use_container_width=True)

        # Select Branch Column
        st.subheader("🏢 Branch Selection")
        branch_column = st.selectbox("Select Branch Column", df.columns)

        # ---------------- PDF FUNCTION ----------------
        def create_pdf(branch_df, filename, branch_name):

            pdf = FPDF(orientation='L')
            pdf.add_page()
            pdf.set_font("Arial", size=8)

            pdf.cell(0, 10, f"Branch: {branch_name}", ln=True)

            # Auto width
            page_width = 277
            col_width = page_width / len(branch_df.columns)

            # HEADER
            for col in branch_df.columns:
                pdf.cell(col_width, 8, str(col), border=1)
            pdf.ln()

            # DATA (🔥 CHEQUE NO FIX HERE)
            for _, row in branch_df.iterrows():
                for item in row:
                    text = str(item)

                    # 🔥 FIX: Cheque No / long text prevent cut
                    if len(text) > 25:
                        text = text[:25]

                    pdf.cell(col_width, 8, text, border=1)

                pdf.ln()

            pdf.output(filename)

        # ---------------- GENERATE PDFs ----------------
        if st.button("📄 Generate Branch-wise PDFs"):

            os.makedirs("pdfs", exist_ok=True)

            # clear old files
            for f in os.listdir("pdfs"):
                os.remove(os.path.join("pdfs", f))

            branches = df[branch_column].dropna().astype(str).unique()

            st.write(f"Total Branches Found: {len(branches)}")

            for branch in branches:

                branch_df = df[df[branch_column].astype(str) == branch]

                safe_branch = str(branch).replace("/", "_").replace("\\", "_")
                file_path = f"pdfs/{safe_branch}.pdf"

                create_pdf(branch_df, file_path, branch)

            # ---------------- ZIP ----------------
            zip_path = "branch_pdfs.zip"

            with zipfile.ZipFile(zip_path, "w") as zipf:
                for file in os.listdir("pdfs"):
                    zipf.write(os.path.join("pdfs", file), file)

            # ---------------- DOWNLOAD ----------------
            with open(zip_path, "rb") as f:
                st.download_button(
                    "⬇️ Download All PDFs",
                    f,
                    file_name="branch_pdfs.zip"
                )

            st.success("✅ PDFs Generated Successfully (Cheque No Fixed)")

    except Exception as e:
        st.error(f"Error: {str(e)}")
import streamlit as st
import pandas as pd


# =========================
# Merge Function
# =========================
def merge_uploaded_csv(files):
    dfs = []
    for file in files:
        df = pd.read_csv(file)
        df.columns = df.columns.str.strip()
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


# =========================
# Session State Save
# =========================
if "merged_df" not in st.session_state:
    st.session_state.merged_df = None


# =========================
# Upload
# =========================
files = st.file_uploader(
    "Upload CSV Files",
    type="csv",
    accept_multiple_files=True
)

# =========================
# Merge Button (manual trigger)
# =========================
if st.button("Merge Files"):
    if files:
        st.session_state.merged_df = merge_uploaded_csv(files)
    else:
        st.warning("Upload files first")


# =========================
# Show + Download
# =========================
if st.session_state.merged_df is not None:

    df = st.session_state.merged_df

    st.success(f"Total Rows: {len(df)}")
    st.dataframe(df)

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Merged File",
        data=csv,
        file_name="merged.csv",
        mime="text/csv"
    )

import streamlit as st
import pandas as pd
from io import BytesIO
import os

CACHE_FILE = "sustainability_cache.xlsx"

st.markdown("<h1 style='color:#003366;'>Sustainability Report</h1>", unsafe_allow_html=True)

# ---------------- SIDEBAR ---------------- #
st.sidebar.header("Options")
project_file = st.sidebar.file_uploader("Upload Project Excel", type=["xlsx"], key="project_upload")
expense_file = st.sidebar.file_uploader("Upload Expenses Excel", type=["xlsx"], key="expense_upload")

# ---------------- LOAD OR CACHE ---------------- #
def load_excel(file):
    return pd.read_excel(file)

# اگر نئی file upload ہو
if project_file is not None:
    df_raw = load_excel(project_file)
    if expense_file is not None:
        df_exp = load_excel(expense_file)
        exp_sum = df_exp.groupby("Branch Code", as_index=False)["Amount"].sum()
        df_raw = df_raw.merge(exp_sum, on="Branch Code", how="left", suffixes=("", "_Expenses"))
        df_raw["Expenses"] = df_raw["Amount_Expenses"].fillna(0)
    else:
        df_raw["Expenses"] = 0
    # save locally for next reopen
    df_raw.to_excel(CACHE_FILE, index=False)
elif os.path.exists(CACHE_FILE):
    # reopen, read cache
    df_raw = pd.read_excel(CACHE_FILE)
else:
    df_raw = pd.DataFrame()

# ---------------- AGGREGATE PER BRANCH ---------------- #
agg_list = []
if not df_raw.empty:
    branch_keys = ["Area", "Branch Name", "Branch Code"]
    grouped = df_raw.groupby(branch_keys, as_index=False)
    for _, g in grouped:
        area = g["Area"].iloc[0]
        branch = g["Branch Name"].iloc[0]
        code = g["Branch Code"].iloc[0]

        project_total = g[~g["Sanction No"].str.contains("D030|D003|D027|D028", na=False)]["Amount"].sum()
        acag_total = g[g["Sanction No"].str.contains("D030", na=False)]["Amount"].sum()
        pmlchs_total = g[g["Sanction No"].str.contains("D003", na=False)]["Amount"].sum()
        pmy_total = g[g["Sanction No"].str.contains("D027|D028", regex=True, na=False)]["Amount"].sum()
        expenses_total = g["Expenses"].dropna().iloc[0] if not g["Expenses"].dropna().empty else 0

        row = {
            "Area": area,
            "Branch": branch,
            "Branch Code": code,
            "Project Disburse": project_total,
            "6% Income": round(project_total * 0.06, 2),
            "ACAG Disburse": acag_total,
            "1% Income": round(acag_total * 0.01, 2),
            "PMLCHS Disburse": pmlchs_total,
            "2% Income": round(pmlchs_total * 0.02, 2),
            "PMY Disburse": pmy_total,
            "3% Income": round(pmy_total * 0.03, 2),
        }
        row["Total Income"] = round(row["6% Income"] + row["1% Income"] + row["2% Income"] + row["3% Income"], 2)
        row["Expenses"] = expenses_total
        row["Difference"] = round(row["Total Income"] - row["Expenses"], 2)
        agg_list.append(row)

df = pd.DataFrame(agg_list)

# ---------------- AREA FILTER ---------------- #
if not df.empty and "Area" in df.columns:
    areas = ["All Areas"] + sorted(df["Area"].dropna().unique())
    selected_area = st.sidebar.selectbox("Select Area", areas)
    if selected_area != "All Areas":
        df_display = df[df["Area"] == selected_area]
    else:
        df_display = df.copy()
else:
    df_display = df.copy()

# ---------------- DISPLAY TABLE ---------------- #
st.subheader("Data Table")
if df_display.empty:
    st.info("Upload Project Excel to view table.")
else:
    st.markdown("<style>td,th{color:white;}</style>", unsafe_allow_html=True)
    st.dataframe(df_display)

# ---------------- DOWNLOAD BUTTON ---------------- #
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Filtered Report")
    output.seek(0)
    return output

if not df_display.empty:
    excel_data = to_excel(df_display)
    st.sidebar.download_button(
        label=f"⬇️ Download {selected_area} Excel",
        data=excel_data,
        file_name=f"Sustainability_{selected_area}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
# -------------------
# MDP Section with G/P and Grand Total
# -------------------

import streamlit as st
import pandas as pd

from io import BytesIO

# ---------- Fixed Signin Menu ----------

# ---------- MDP Report Expander (Below Signin) ----------
with st.sidebar.expander("📊 MDP Report"):
    st.write("Upload sheets and generate MDP report here")

    # --- File Upload ---
    active_file = st.file_uploader("Upload Active Sheet", type=["xlsx","xls","csv"], key="mdp_active_upload")
    mdp_file = st.file_uploader("Upload MDP Sheet", type=["xlsx","xls","csv"], key="mdp_mdp_upload")

    # --- Placeholders ---
    table_placeholder = st.empty()
    overall_download_placeholder = st.empty()
    area_dropdown_placeholder = st.empty()
    area_download_placeholder = st.empty()

    # --- Show info if files not uploaded ---
    if not active_file or not mdp_file:
        table_placeholder.info("Upload both Active and MDP sheets to generate the MDP report and download options.")

    # --- Main Logic (same as your existing code) ---
    if active_file and mdp_file:
        try:
            active_df = pd.read_csv(active_file) if active_file.name.endswith(".csv") else pd.read_excel(active_file)
            mdp_df = pd.read_csv(mdp_file) if mdp_file.name.endswith(".csv") else pd.read_excel(mdp_file)
        except Exception as e:
            table_placeholder.error(f"Error reading files: {e}")
            st.stop()

        # --- Clean columns ---
        active_df.columns = active_df.columns.str.strip()
        mdp_df.columns = mdp_df.columns.str.strip()

        # --- Pivot Calculation ---
        report_data = []

        for (area, branch), group in mdp_df.groupby(['area_id','branch_id']):
            due_count = len(active_df[active_df['branch_id']==branch])
            amount_sum = group['Due Amount'].sum()
            active_sanctions = active_df[active_df['branch_id']==branch]['Sanction No'].tolist()
            g_by_count = sum([1 for x in active_sanctions if x in group['sanction_no'].values])
            n_a_count = due_count - g_by_count
            p_b = round((g_by_count/due_count)*100,2) if due_count!=0 else 0
            n_p = round((n_a_count/due_count)*100,2) if due_count!=0 else 0
            g_p = p_b  # G/P = same as % of counted borrowers

            report_data.append({
                'Area': area,
                'Branch': branch,
                'Active': '',
                'Due': due_count,
                'Amount': amount_sum,
                'Given/BY': g_by_count,
                'G/P %': g_p,
                'MDP/Box %': p_b,
                'N/A': n_a_count,
                'N/P %': n_p
            })

        report_df = pd.DataFrame(report_data)

        # --- Add Grand Total Row ---
        grand_total = {
            'Area': 'Grand Total',
            'Branch': '',
            'Active': '',
            'Due': report_df['Due'].sum(),
            'Amount': report_df['Amount'].sum(),
            'Given/BY': report_df['Given/BY'].sum(),
            'G/P %': round((report_df['Given/BY'].sum()/report_df['Due'].sum())*100,2) if report_df['Due'].sum()!=0 else 0,
            'MDP/Box %': round((report_df['Given/BY'].sum()/report_df['Due'].sum())*100,2) if report_df['Due'].sum()!=0 else 0,
            'N/A': report_df['N/A'].sum(),
            'N/P %': round((report_df['N/A'].sum()/report_df['Due'].sum())*100,2) if report_df['Due'].sum()!=0 else 0
        }

        report_df = pd.concat([report_df, pd.DataFrame([grand_total])], ignore_index=True)

        # --- Display Table ---
        table_placeholder.dataframe(report_df)

        # --- Excel Helper ---
        def to_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='MDP_Report')
            return output.getvalue()

        # --- Overall Download ---
        excel_data = to_excel(report_df)
        overall_download_placeholder.download_button(
            label="📥 Download Overall Report",
            data=excel_data,
            file_name="MDP_Report_Overall.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="mdp_overall_download"
        )

        # --- Area-wise Dropdown & Download ---
        areas = report_df['Area'].unique().tolist()
        areas = [x for x in areas if x!='Grand Total']
        areas.sort()
        areas.insert(0,"All Areas")

        selected_area = area_dropdown_placeholder.selectbox("Select Area", areas, key="mdp_area_dropdown")
        df_to_download = report_df if selected_area=="All Areas" else report_df[report_df['Area']==selected_area]
        excel_data_area = to_excel(df_to_download)

        area_download_placeholder.download_button(
            label=f"📥 Download {selected_area} Report",
            data=excel_data_area,
            file_name=f"MDP_Report_{selected_area}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="mdp_area_download"
        )
import streamlit as st
import pandas as pd
from io import BytesIO

st.markdown("---")
st.subheader("📁 Merge File Upload And Take File With Branch&Area")

# --- File Upload ---
col1, col2 = st.columns(2)
with col1:
    merge_file = st.file_uploader("Upload Merge File (Sanction No)", type=["xlsx","xls","csv"], key="merge_file")
with col2:
    branch_file = st.file_uploader("Upload Branch File (Branch Code)", type=["xlsx","xls","csv"], key="branch_file")

# --- Placeholders ---
merge_table_placeholder = st.empty()
merge_download_placeholder = st.empty()

if merge_file and branch_file:
    try:
        df_merge = pd.read_csv(merge_file) if merge_file.name.endswith(".csv") else pd.read_excel(merge_file)
        df_branch = pd.read_csv(branch_file) if branch_file.name.endswith(".csv") else pd.read_excel(branch_file)
    except Exception as e:
        merge_table_placeholder.error(f"Error reading files: {e}")
        st.stop()

    # --- Clean column names ---
    df_merge.columns = df_merge.columns.str.strip()
    df_branch.columns = df_branch.columns.str.strip()

    # --- Check required columns ---
    if 'sanctionno' not in df_merge.columns:
        st.error("Merge File must have column 'sanctionno'")
        st.stop()
    if 'branch code' not in df_branch.columns or 'branch_name' not in df_branch.columns or 'area_name' not in df_branch.columns:
        st.error("Branch File must have columns 'branch code', 'branch_name', 'area_name'")
        st.stop()

    # --- Ensure columns are string for merge ---
    df_merge['Sanction_Prefix'] = df_merge['sanctionno'].astype(str).str[:4]
    df_branch['branch code'] = df_branch['branch code'].astype(str)

    # --- Merge logic ---
    merged_df = pd.merge(
        df_merge,
        df_branch.rename(columns={'branch code':'Sanction_Prefix'}),
        on='Sanction_Prefix',
        how='left'
    )

    # --- Add Branch Name & Area Name as 3rd and 4th column ---
    if 'branch_name' in merged_df.columns and 'area_name' in merged_df.columns:
        branch_col = merged_df.pop('branch_name')
        area_col = merged_df.pop('area_name')
        merged_df.insert(2, 'Branch Name', branch_col)
        merged_df.insert(3, 'Area Name', area_col)

    # --- Display table ---
    merge_table_placeholder.dataframe(merged_df)

    # --- Download helper ---
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Merged_Report')
        return output.getvalue()

    excel_data = to_excel(merged_df)

    # --- Download button ---
    merge_download_placeholder.download_button(
        label="📥 Download Merged File",
        data=excel_data,
        file_name="Merged_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="merge_download"
    )

else:
    merge_table_placeholder.info("Upload both Merge File and Branch File to generate merged report.")
import streamlit as st
import pandas as pd
import plotly.express as px
from fpdf import FPDF

st.title("📊 Recovery System Dashboard")

# Upload Recovery File
uploaded_file = st.file_uploader("📁 Upload Recovery File (Excel)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Date conversion
    df['recovery_date'] = pd.to_datetime(df['recovery_date'], errors='coerce')
    df.dropna(subset=['recovery_date'], inplace=True)

    df['day'] = df['recovery_date'].dt.day

    # Range function
    def get_range(day):
        if 1 <= day <= 10:
            return "1-10"
        elif 11 <= day <= 20:
            return "11-20"
        elif 21 <= day <= 31:
            return "21-31"
        return "Unknown"

    df['range'] = df['day'].apply(get_range)

    st.write("### 📄 Complete Recovery Data")
    st.dataframe(df)

    # SUMMARY
    summary = df.groupby(['branch_id', 'range']).agg({
        'amount': 'sum',
        'receipt_no': 'count'
    }).reset_index()

    summary.rename(columns={'receipt_no': 'receipts'}, inplace=True)

    # Branch totals
    branch_totals = df.groupby('branch_id')['amount'].sum().reset_index()
    branch_totals.rename(columns={'amount': 'total_amount'}, inplace=True)

    summary = summary.merge(branch_totals, on='branch_id')

    summary['percentage'] = (summary['amount'] / summary['total_amount']) * 100
    summary['percentage_text'] = summary['percentage'].map(lambda x: f"{x:.1f}%")

    st.subheader("📊 Branch-wise Recovery Summary")
    st.dataframe(summary.style.format({
        'amount': 'Rs {:,.0f}',
        'total_amount': 'Rs {:,.0f}',
        'percentage': '{:.2f}%'
    }))

    # CHART
    st.subheader("📈 Recovery Chart by Date Range")

    fig = px.bar(
        summary,
        x='branch_id',
        y='amount',
        color='range',
        barmode='group',
        text='percentage_text',
        labels={
            'amount': 'Amount Recovered',
            'branch_id': 'Branch'
        }
    )

    fig.update_traces(textposition='outside')
    fig.update_layout(
        xaxis_title="Branch",
        yaxis_title="Amount",
        legend_title="Date Range"
    )

    st.plotly_chart(fig, use_container_width=True)

    # PIVOT TABLE
    st.subheader("📌 Pivot Table (Branch → Project → Date)")

    df['recovery_date'] = df['recovery_date'].dt.date

    pivot_df = df.groupby(['branch_id', 'project', 'recovery_date']).agg(
        Receipts=('receipt_no', 'count'),
        Amount=('amount', 'sum')
    ).reset_index()

    st.dataframe(pivot_df)

    # PDF CLASS
    class PDF(FPDF):
        def header(self):
            self.set_font("Arial", 'B', 14)
            self.cell(0, 10, "Recovery Report", ln=True, align='C')

        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", 'I', 8)
            self.cell(0, 10, f"Page {self.page_no()}", align='C')

    # PDF DOWNLOADS
    st.subheader("📥 Download Branch-wise PDFs")

    for branch, branch_df in pivot_df.groupby('branch_id'):
        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, f"Branch: {branch}", ln=True)

        total_amount = 0
        total_receipts = 0

        for project, proj_df in branch_df.groupby('project'):
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, f"Project: {project}", ln=True)

            pdf.set_font("Arial", 'B', 10)
            pdf.cell(50, 8, "Date", border=1)
            pdf.cell(40, 8, "Receipts", border=1)
            pdf.cell(50, 8, "Amount", border=1)
            pdf.ln()

            project_amount = 0
            project_receipts = 0

            pdf.set_font("Arial", '', 10)

            for _, row in proj_df.iterrows():
                pdf.cell(50, 8, str(row['recovery_date']), border=1)
                pdf.cell(40, 8, str(row['Receipts']), border=1)
                pdf.cell(50, 8, f"Rs {row['Amount']:,.0f}", border=1)
                pdf.ln()

                project_amount += row['Amount']
                project_receipts += row['Receipts']

            pdf.set_font("Arial", 'B', 10)
            pdf.cell(50, 8, "Project Total", border=1)
            pdf.cell(40, 8, str(project_receipts), border=1)
            pdf.cell(50, 8, f"Rs {project_amount:,.0f}", border=1)
            pdf.ln(10)

            total_amount += project_amount
            total_receipts += project_receipts

        pdf.set_font("Arial", 'B', 11)
        pdf.cell(50, 8, "Branch Total", border=1)
        pdf.cell(40, 8, str(total_receipts), border=1)
        pdf.cell(50, 8, f"Rs {total_amount:,.0f}", border=1)

        pdf_bytes = pdf.output(dest='S').encode('latin1')

        st.download_button(
            label=f"📥 Download PDF - Branch {branch}",
            data=pdf_bytes,
            file_name=f"Branch_{branch}.pdf",
            mime="application/pdf"
        )
import streamlit as st
import pandas as pd
import os
import io
import zipfile
from fpdf import FPDF
import plotly.express as px

st.title("🏦 Recovery & Reports App")

# ---------- PERMANENT STORAGE ----------
SAVE_DIR = "saved_files"
os.makedirs(SAVE_DIR, exist_ok=True)

DO_PATH = os.path.join(SAVE_DIR, "do.xlsx")
REC_PATH = os.path.join(SAVE_DIR, "recovery.xlsx")

# --------------------
# File Upload
# --------------------
do_file = st.file_uploader("Upload Do List", type=["xlsx", "xls"], key="uploader_do")
recovery_file = st.file_uploader("Upload Recovery File", type=["xlsx", "xls"], key="uploader_recovery")

# ---------- SAVE FILES ----------
if do_file:
    with open(DO_PATH, "wb") as f:
        f.write(do_file.getbuffer())

if recovery_file:
    with open(REC_PATH, "wb") as f:
        f.write(recovery_file.getbuffer())

# ---------- LOAD IF NOT UPLOADED ----------
if do_file is None and os.path.exists(DO_PATH):
    do_file = DO_PATH

if recovery_file is None and os.path.exists(REC_PATH):
    recovery_file = REC_PATH

# ---------------- MAIN LOGIC ----------------
if do_file and recovery_file:

    do_df = pd.read_excel(do_file)
    recovery_df = pd.read_excel(recovery_file)

    for df in [do_df, recovery_df]:
        df.columns = df.columns.str.strip()

    # ---------- OVERDUE ----------
    if 'Sanction No' not in do_df.columns or 'Sanction No' not in recovery_df.columns:
        st.error("Both files must contain 'Sanction No'")
    else:
        overdue_df = do_df[
            ~do_df['Sanction No'].astype(str).str.strip().isin(
                recovery_df['Sanction No'].astype(str).str.strip()
            )
        ].copy()

        st.subheader("🕒 Final Overdue List")
        st.dataframe(overdue_df)

    # ---------- MONTHLY RECOVERY ----------
    do_df['Sanction No'] = do_df['Sanction No'].astype(str).str.strip()
    recovery_df['Sanction No'] = recovery_df['Sanction No'].astype(str).str.strip()

    if 'recovery_date' in recovery_df.columns:
        recovery_df['recovery_date'] = pd.to_datetime(recovery_df['recovery_date'], errors='coerce')
    else:
        recovery_df['recovery_date'] = pd.NaT

    month = pd.Timestamp.now().month
    year = pd.Timestamp.now().year

    recovery_this_month = recovery_df[
        (recovery_df['recovery_date'].dt.month == month) &
        (recovery_df['recovery_date'].dt.year == year)
    ] if not recovery_df['recovery_date'].isna().all() else recovery_df.iloc[0:0]

    recovered = recovery_this_month[
        recovery_this_month['Sanction No'].isin(do_df['Sanction No'])
    ]

    if 'branch_id' not in do_df.columns:
        do_df['branch_id'] = do_df.get('Branch', '')

    if 'branch_id' not in recovery_df.columns:
        recovery_df['branch_id'] = recovery_df.get('Branch Code', '')

    due_summary = do_df.groupby('branch_id')['Sanction No'].count().reset_index()
    due_summary.columns = ['branch_id', 'total_due']

    recovered_summary = recovered.groupby('branch_id')['Sanction No'].count().reset_index()
    recovered_summary.columns = ['branch_id', 'recovered']

    summary = due_summary.merge(recovered_summary, on='branch_id', how='left').fillna(0)
    summary['remaining'] = summary['total_due'] - summary['recovered']
    summary['recovery_percent'] = (summary['recovered'] / summary['total_due'].replace(0, pd.NA)) * 100
    summary['recovery_percent'] = summary['recovery_percent'].fillna(0)

    st.subheader("📋 Branch-wise Recovery Summary (This Month)")
    st.dataframe(summary)

    # ---------- CHART ----------
    fig = px.bar(
        summary,
        x='branch_id',
        y='recovery_percent',
        text=summary['recovery_percent'].apply(lambda x: f"{x:.1f}%")
    )
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# ---------------- RECOVERY PDF ZIP + AREA FILTER ----------------
if recovery_file:

    rec_df = pd.read_excel(recovery_file)
    rec_df.columns = rec_df.columns.str.strip()

    for col in ["branch_id", "recovery_date", "amount", "Name", "Sanction No", "area_id"]:
        if col not in rec_df.columns:
            rec_df[col] = ""

    rec_df["Date"] = pd.to_datetime(rec_df["recovery_date"], errors='coerce').dt.strftime("%d-%m-%y")

    # ---------- AREA FILTER FOR RECOVERY ----------
    if rec_df["area_id"].nunique() > 0:
        areas = sorted(rec_df["area_id"].astype(str).unique())
        selected_area = st.selectbox(
            "Select Area for Recovery PDFs",
            ["All Areas"] + areas,
            key="recovery_area_select"
        )
        if selected_area != "All Areas":
            rec_df_filtered = rec_df[rec_df["area_id"].astype(str) == selected_area]
        else:
            rec_df_filtered = rec_df.copy()
    else:
        rec_df_filtered = rec_df.copy()

    if st.button("Generate Recovery PDFs", key="gen_recovery_pdfs_btn"):
        branches = rec_df_filtered["branch_id"].astype(str).unique()
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED) as zf:
            for branch in branches:
                branch_data = rec_df_filtered[rec_df_filtered["branch_id"].astype(str) == str(branch)]

                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(0, 10, f"Branch: {branch}", ln=True)

                pdf.set_font("Arial", "B", 10)
                pdf.cell(12,8,"Sr#",1)
                pdf.cell(50,8,"Date",1)
                pdf.cell(40,8,"Amount",1)
                pdf.cell(60,8,"Name",1)
                pdf.cell(40,8,"Sanction",1)
                pdf.ln()

                pdf.set_font("Arial","",9)
                total=0

                for i,(_,row) in enumerate(branch_data.iterrows(),1):
                    pdf.cell(12,8,str(i),1)
                    pdf.cell(50,8,str(row["Date"]),1)
                    pdf.cell(40,8,str(row["amount"]),1)
                    pdf.cell(60,8,str(row["Name"])[:25],1)
                    pdf.cell(40,8,str(row["Sanction No"]),1)
                    pdf.ln()
                    try:
                        total+=float(row["amount"])
                    except:
                        pass

                pdf.cell(62,8,"Total",1)
                pdf.cell(40,8,f"{total:,.2f}",1)

                zf.writestr(f"{branch}.pdf", pdf.output(dest="S").encode("latin1"))

        zip_buffer.seek(0)
        st.download_button(
            "Download Recovery PDFs (ZIP)",
            zip_buffer.getvalue(),
            f"{selected_area}_Recovery.zip",
            "application/zip"
        )

# ---------------- OVERDUE PDF AREA & BRANCH ----------------
if do_file and recovery_file:
    if 'overdue_df' in locals() and not overdue_df.empty:

        # ---------- FIX AREA COLUMN AUTO DETECT ----------
        area_col = None
        for col in overdue_df.columns:
            if "area" in col.lower():
                area_col = col
                break

        if area_col:
            overdue_df["area_id"] = overdue_df[area_col].astype(str)
        else:
            overdue_df["area_id"] = "Unknown"

        # ---------- BRANCH COLUMN ----------
        if "branch_id" not in overdue_df.columns:
            for col in overdue_df.columns:
                if "branch" in col.lower():
                    overdue_df["branch_id"] = overdue_df[col]
                    break
            else:
                overdue_df["branch_id"] = "Unknown"

        # ---------- AREA DROPDOWN ----------
        overdue_areas = sorted(overdue_df["area_id"].dropna().unique())

        selected_overdue_area = st.selectbox(
            "Select Area for Overdue PDFs",
            ["All Areas"] + list(overdue_areas),
            key="overdue_area_select"
        )

        if selected_overdue_area != "All Areas":
            overdue_df_filtered = overdue_df[overdue_df["area_id"] == selected_overdue_area]
        else:
            overdue_df_filtered = overdue_df

        # ---------- BRANCH DROPDOWN ----------
        branches_overdue = sorted(overdue_df_filtered["branch_id"].dropna().unique())

        selected_branch_overdue = st.selectbox(
            "Select Branch for Overdue PDF",
            ["All Branches"] + list(branches_overdue),
            key="overdue_branch_select"
        )

        # ---------- GENERATE PDF ----------
        if st.button("Generate Overdue PDF", key="gen_overdue_pdfs_btn"):

            if selected_branch_overdue != "All Branches":
                df_branch = overdue_df_filtered[
                    overdue_df_filtered["branch_id"] == selected_branch_overdue
                ]
            else:
                df_branch = overdue_df_filtered

            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, f"Overdue List - {selected_branch_overdue}", ln=True)

            pdf.set_font("Arial", "B", 10)
            for col in df_branch.columns[:5]:
                pdf.cell(38,8,str(col),1)
            pdf.ln()

            pdf.set_font("Arial","",9)
            for _,row in df_branch.iterrows():
                for col in df_branch.columns[:5]:
                    pdf.cell(38,8,str(row[col]),1)
                pdf.ln()

            st.download_button(
                "Download Overdue PDF",
                pdf.output(dest="S").encode("latin1"),
                f"{selected_branch_overdue}_Overdue.pdf",
                "application/pdf",
                key="download_overdue_pdf"
            )
import streamlit as st
import pandas as pd
import re

st.header("📂 Merge CSV Files (Skip first 2 rows)")

def clean_colname(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower())

# --- Users select multiple CSV files ---
uploaded_files = st.file_uploader(
    "Upload your CSV files",
    type="csv",
    accept_multiple_files=True
)

merged_data = []
missing_sanction_files = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            # Skip first 2 rows
            df = pd.read_csv(uploaded_file, skiprows=2)

            # Clean columns
            df.columns = [clean_colname(col) for col in df.columns]

            # Check for Sanction No column
            possible_names = ["sanctionno", "sanctionnumber", "sactionno"]
            sanction_col = next((col for col in df.columns if col in possible_names), None)

            if sanction_col:
                merged_data.append(df)
            else:
                missing_sanction_files.append(uploaded_file.name)

        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")

    # --- Show warning for files without Sanction No ---
    if missing_sanction_files:
        st.warning("No 'Sanction No' column found in these files:")
        for f in missing_sanction_files:
            st.write(f"- {f}")

    # --- Merge and allow download ---
    if merged_data:
        final_df = pd.concat(merged_data, ignore_index=True)
        st.success(f"Merged {len(merged_data)} CSV files! Total rows: {len(final_df)}")

        csv_download = final_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇ Download Merged CSV",
            data=csv_download,
            file_name="merged_due_list.csv",
            mime="text/csv"
        )
else:
    st.info("Please upload at least one CSV file to merge.")
import streamlit as st
import pandas as pd
import re

st.header("📂 Merge CSV / Excel Files (No Row Skip)")

def clean_colname(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower())

# --- Upload CSV + Excel ---
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

merged_data = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            # --- Read file (NO skiprows) ---
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            # --- Clean column names ---
            df.columns = [clean_colname(col) for col in df.columns]

            # --- Add all files ---
            merged_data.append(df)

        except Exception as e:
            st.error(f"Error reading {uploaded_file.name}: {e}")

    # --- Merge all ---
    if merged_data:
        final_df = pd.concat(merged_data, ignore_index=True)

        st.success(f"✅ Merged {len(merged_data)} files | Total rows: {len(final_df)}")

        # --- Download ---
        csv_download = final_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇ Download Merged File",
            data=csv_download,
            file_name="merged_file.csv",
            mime="text/csv"
        )

else:
    st.info("Please upload at least one file.")
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from zipfile import ZipFile

st.header("📑 Cheque-wise Analysis")

uploaded_cheque = st.file_uploader("Upload Cheque-wise List", type=["xlsx", "csv"])

if uploaded_cheque:

    if uploaded_cheque.name.endswith(".csv"):
        cheque_df = pd.read_csv(uploaded_cheque)
    else:
        cheque_df = pd.read_excel(uploaded_cheque)

    cheque_df.columns = [str(c).strip() for c in cheque_df.columns]

    required_cols = ["branch_id","date_disbursed","sanction_no","tranch_no","member_name","member_cnic"]
    cheque_df = cheque_df[[c for c in required_cols if c in cheque_df.columns]]

    cheque_df["Name"] = cheque_df["member_name"]
    cheque_df.drop(columns=["member_name"], inplace=True)

    cheque_df["date_disbursed"] = pd.to_datetime(cheque_df["date_disbursed"], errors="coerce")

    today = datetime.today()

    cheque_df["Months Passed"] = cheque_df["date_disbursed"].apply(
        lambda x: relativedelta(today, x).months + relativedelta(today, x).years*12 if pd.notnull(x) else ""
    )

    cheque_df["Days Passed"] = cheque_df["date_disbursed"].apply(
        lambda x: (today-x).days if pd.notnull(x) else ""
    )

    for col in ["House Complete","Shifted","Design"]:
        if col not in cheque_df.columns:
            cheque_df[col] = ""

    cheque_df["2nd Tranch Status"] = ""

    second_map = cheque_df[cheque_df["tranch_no"]==2].groupby("sanction_no").size().to_dict()

    first_df = cheque_df[cheque_df["tranch_no"]==1].copy()
    first_df["2nd Tranch Status"] = first_df["sanction_no"].apply(lambda x:"OK" if x in second_map else "")

    display_cols = ["branch_id","sanction_no","tranch_no","Name","member_cnic",
                    "date_disbursed","Months Passed","2nd Tranch Status",
                    "House Complete","Shifted","Design"]

    editable_df = first_df[display_cols]

    # -------- Editable Table --------
    edited_df = st.experimental_data_editor(editable_df, use_container_width=True)

    # -------- CSV Download --------
    csv_data = edited_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Download Edited CSV",
        csv_data,
        "cheque_analysis.csv",
        "text/csv"
    )

    # -------- Save Flags --------
    if st.button("💾 Save Flags"):
        edited_df[["sanction_no","tranch_no","House Complete","Shifted","Design"]].to_csv(
            "cheque_flags.csv", index=False
        )
        st.success("Saved")

    # -------- ZIP PDFs --------
    if st.button("⬇️ Download All Branch PDFs (ZIP)"):

        zip_buffer = BytesIO()

        with ZipFile(zip_buffer,"w") as zipf:

            for branch in edited_df["branch_id"].unique():

                bdf = edited_df[edited_df["branch_id"]==branch]

                pdf = BytesIO()
                doc = SimpleDocTemplate(pdf, pagesize=landscape(A4))
                styles = getSampleStyleSheet()
                elements=[]

                elements.append(Paragraph(f"Branch {branch}",styles["Heading1"]))
                elements.append(Spacer(1,10))

                table_df = bdf.drop(columns=["branch_id","tranch_no"],errors="ignore")
                table_df.insert(0,"S.No",range(1,len(table_df)+1))

                data=[table_df.columns.tolist()]+table_df.astype(str).values.tolist()

                table=Table(data,repeatRows=1)
                table.setStyle(TableStyle([
                    ("GRID",(0,0),(-1,-1),0.5,colors.black),
                    ("ALIGN",(0,0),(-1,-1),"CENTER")
                ]))

                elements.append(table)
                doc.build(elements)
                pdf.seek(0)

                zipf.writestr(f"branch_{branch}.pdf",pdf.getvalue())

        zip_buffer.seek(0)

        st.download_button(
            "Download ZIP",
            zip_buffer.getvalue(),
            "branches.zip",
            "application/zip"
        )

import streamlit as st
import pandas as pd
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from fpdf import FPDF
from io import BytesIO

# ================= PAGE =================
st.title("💰 Smart Expense Tracker")

# ================= SAFE RERUN =================
def safe_rerun():
    try:
        st.rerun()
    except:
        st.experimental_rerun()

# ================= FIREBASE =================
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["gcp_service_account"])
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= FUNCTIONS =================
def add_expense(data):
    db.collection("expenses").add(data)

def delete_expense(doc_id):
    db.collection("expenses").document(doc_id).delete()

def load_data():
    docs = db.collection("expenses").stream()
    data = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        data.append(d)
    return pd.DataFrame(data)

# ================= LOAD DATA =================
df = load_data()

if df.empty:
    df = pd.DataFrame(columns=["Date", "Item", "Amount"])

df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
df["Month"] = df["Date"].dt.strftime("%B")

# ================= MONTH FILTER =================
if not df.empty:
    selected_month = st.selectbox("📅 Select Month", df["Month"].dropna().unique())
    df = df[df["Month"] == selected_month]

# ================= SIDEBAR =================
st.sidebar.header("➕ Add Expense")

budget = st.sidebar.number_input("💵 Budget", min_value=0.0, value=9000.0)

with st.sidebar.form("expense_form"):
    date = datetime.now().strftime("%Y-%m-%d")
    item = st.text_input("Item Name")
    amount = st.number_input("Amount", min_value=0.0)
    submit = st.form_submit_button("Add Expense")

if submit:
    if item:
        add_expense({
            "Date": date,
            "Item": item,
            "Amount": amount
        })

        st.success("Saved ✅")
        safe_rerun()

# ================= CALCULATIONS =================
total = df["Amount"].sum()
remaining = budget - total

# ================= METRICS =================
c1, c2, c3 = st.columns(3)
c1.metric("💰 Budget", budget)
c2.metric("💸 Total Expense", total)
c3.metric("📊 Remaining", remaining)

st.markdown("---")

# ================= TABLE =================
st.subheader("📋 Expense List")

running_total = 0

if not df.empty:

    h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 2, 1])
    h1.write("Date")
    h2.write("Item")
    h3.write("Amount")
    h4.write("Running Total")
    h5.write("Delete")

    st.markdown("---")

    for _, row in df.iterrows():
        running_total += row["Amount"]

        c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 1])

        c1.write(row["Date"])
        c2.write(row["Item"])
        c3.write(row["Amount"])
        c4.write(running_total)

        if c5.button("❌", key=row["id"]):
            delete_expense(row["id"])
            safe_rerun()

else:
    st.info("No expenses yet")

# ================= TOTAL =================
st.markdown("---")
st.success(f"💰 Total Expense: {total}")
st.info(f"📉 Remaining Budget: {remaining}")

# ================= DOWNLOAD =================
st.markdown("## 📥 Download Reports")

summary = df.groupby("Item")["Amount"].sum().reset_index()

# -------- PDF --------
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Expense Summary Report", ln=True, align="C")

pdf = PDF()
pdf.add_page()

pdf.set_font("Arial", "B", 12)
pdf.cell(60, 10, "Item", border=1)
pdf.cell(60, 10, "Amount", border=1)
pdf.ln()

pdf.set_font("Arial", "", 11)

for _, row in summary.iterrows():
    pdf.cell(60, 10, str(row["Item"]), border=1)
    pdf.cell(60, 10, f"{row['Amount']:.0f}", border=1)
    pdf.ln()

pdf.cell(60, 10, "Total", border=1)
pdf.cell(60, 10, f"{summary['Amount'].sum():.0f}", border=1)

pdf_bytes = pdf.output(dest='S').encode('latin1')

st.download_button("📄 Download PDF", pdf_bytes, "expense_summary.pdf")

# -------- EXCEL --------
output = BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df.to_excel(writer, index=False, sheet_name="Data")
    summary.to_excel(writer, index=False, sheet_name="Summary")

st.download_button(
    "📊 Download Excel",
    data=output.getvalue(),
    file_name="expense_report.xlsx"
)

# ================= FOOTER =================
st.caption("Smart Expense App • Streamlit + Firebase 🚀")
