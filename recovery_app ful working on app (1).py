import calendar
from datetime import datetime
import io
from io import BytesIO
import os
import re
import zipfile

from dateutil.relativedelta import relativedelta
from fpdf import FPDF
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
import plotly.express as px
import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st

# ==========================================
# 1. INITIAL CONFIG & DASHBOARD STYLING
# ==========================================
st.set_page_config(page_title="Recovery & Reports App", layout="wide")

# Custom UI CSS for Sidebar and Cards
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    [data-testid="stSidebar"] {
        background-color: #1e293b !important;
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    .report-card {
        background: white;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-left: 5px solid #0284c7;
    }
</style>
""", unsafe_allow_html=True)

# ---------- USERS & AUTH ----------
USERS = {
    "Khaleel": "11234",
    "user": "1111"
}

if "login" not in st.session_state:
    st.session_state.login = False

# ---------- SECURE LOGIN PAGE ----------
if not st.session_state.login:
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
    }
    h2, label { color: white !important; text-align: center; }
    .stButton>button {
        background: #00c6ff; color: white; border-radius: 10px; height: 40px; font-weight: bold;
    }
    .stButton>button:hover { background: #0072ff; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("## 🔐 Recovery Dashboard Login")
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        login_btn = st.button("Sign In", use_container_width=True)

        if login_btn:
            if USERS.get(user) == pwd:
                st.session_state.login = True
                st.success("Login successful ✔")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
    st.stop()


# ==========================================
# 2. SIDEBAR NAVIGATION (LEFT SIDE MENU)
# ==========================================
st.sidebar.image("https://img.icons8.com/fluent/96/000000/bank.png", width=80)
st.sidebar.title("Navigation Menu")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "Select System Module:",
    [
        "📸 CNIC QR Generator",
        "📊 Recovery Summaries",
        "📁 File Merge Utilities",
        "🕒 Overdue Tracker",
        "📑 Cheque-wise Analysis",
        "📄 Loan Disbursement PDF"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("👤 **Active User:** Khaleel")
if st.sidebar.button("Logout 🏃‍♂️"):
    st.session_state.login = False
    st.rerun()


# ---------- HELPER FUNCTIONS ----------
def safe_str(val):
    if pd.isna(val): return ""
    return str(val).strip()

def clean_colname(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower())


# ==========================================
# 3. MAIN CONTENT HEADERS
# ==========================================
st.write(f"## 🏦 Financial Recovery & Reporting Control Center")
st.write(f"Current Window: **{app_mode[2:]}**")
st.markdown("---")


# ==========================================
# MODULE 1: CNIC QR GENERATOR
# ==========================================
if app_mode == "📸 CNIC QR Generator":
    st.markdown('<div class="report-card"><h3>📷 CNIC Quick Response Code Generator</h3><p>Enter 13-digit CNIC number to build verified standard high-definition barcodes.</p></div>', unsafe_allow_html=True)
    
    cnic = st.text_input("Enter 13-digit CNIC Number (Without dashes)", max_chars=13)

    if st.button("Generate QR Code Matrix", type="primary"):
        if cnic and len(cnic) == 13 and cnic.isdigit():
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4
            )
            qr.add_data(cnic)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buf = BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()

            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(img_bytes, width=220, caption=f"CNIC: {cnic}")
            with col2:
                st.success("QR Code rendered successfully!")
                st.download_button(
                    "💾 Download PNG Format",
                    data=img_bytes,
                    file_name=f"QR_{cnic}.png",
                    mime="image/png"
                )
        else:
            st.error("Invalid Input! Please enter exactly 13 digits numeric values.")


# ==========================================
# MODULE 2: RECOVERY MONTH & BRANCH WISE SUMMARY
# ==========================================
elif app_mode == "📊 Recovery Summaries":
    st.markdown('<div class="report-card"><h3>📊 Recovery Analytics (Terabyte Processing Engine)</h3><p>Upload raw systemic datasets to evaluate performance metric loops across active branch channels.</p></div>', unsafe_allow_html=True)
    
    os.makedirs("data", exist_ok=True)
    LOCAL_FILE = "data/recovery.xlsx"

    uploaded = st.file_uploader("Upload Recovery Ledger Sheet", type=["xlsx", "csv"])
    
    df = None
    if uploaded:
        df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.session_state["df"] = df
        df.to_excel(LOCAL_FILE, index=False)
    elif "df" in st.session_state:
        df = st.session_state["df"]
    elif os.path.exists(LOCAL_FILE):
        df = pd.read_excel(LOCAL_FILE)
        st.session_state["df"] = df

    if df is not None:
        df.columns = [c.strip() for c in df.columns]
        col_mapping = {clean_colname(c): c for c in df.columns}
        
        req_mapped = {}
        for target in ["branch_id", "recovery_date", "receipt_no", "credit_amount"]:
            clean_tgt = target.replace("_", "")
            if clean_tgt in col_mapping:
                req_mapped[target] = col_mapping[clean_tgt]

        if len(req_mapped) < 3:
            st.error("Uploaded file columns must contain clear variants of: branch_id, recovery_date, receipt_no, credit_amount")
        else:
            b_col = req_mapped.get("branch_id")
            d_col = req_mapped.get("recovery_date")
            r_col = req_mapped.get("receipt_no")
            amt_col = req_mapped.get("credit_amount", df.columns[-1])

            df[d_col] = pd.to_datetime(df[d_col], errors="coerce")
            df = df.dropna(subset=[d_col])
            
            df["Month"] = df[d_col].dt.to_period("M")
            df["Day"] = df[d_col].dt.day
            df["Range"] = pd.cut(df["Day"], bins=[0, 10, 20, 31], labels=["1-10", "11-20", "21-31"])

            summary_rows = []
            for branch in sorted(df[b_col].unique()):
                branch_df = df[df[b_col] == branch]
                for month in sorted(branch_df["Month"].unique()):
                    month_df = branch_df[branch_df["Month"] == month]
                    
                    rec_1_10 = len(month_df[month_df["Range"] == "1-10"])
                    rec_11_20 = len(month_df[month_df["Range"] == "11-20"])
                    rec_21_31 = len(month_df[month_df["Range"] == "21-31"])
                    total_slips = len(month_df)
                    total_amt = month_df[amt_col].sum() if amt_col in month_df.columns else 0

                    if total_slips == 0: continue

                    last_date = month_df[d_col].max()
                    month_last_day = calendar.monthrange(last_date.year, last_date.month)[1]

                    summary_rows.append({
                        "Branch": branch, 
                        "Month": str(month),
                        "Total Recovered Amount": total_amt,
                        "Slips (1-10)": rec_1_10, "Pct (1-10)": f"{round(rec_1_10 / total_slips * 100, 1)}%",
                        "Slips (11-20)": rec_11_20, "Pct (11-20)": f"{round(rec_11_20 / total_slips * 100, 1)}%",
                        "Slips (21-31)": rec_21_31, "Pct (21-31)": f"{round(rec_21_31 / total_slips * 100, 1)}%",
                        "Total Slips Count": total_slips, 
                        "Last Entry Transacted": last_date.strftime("%Y-%b-%d"),
                        "Reporting Close Pct": f"{round(last_date.day / month_last_day * 100, 1)}%"
                    })

            summary_df = pd.DataFrame(summary_rows)
            if not summary_df.empty:
                st.dataframe(summary_df, use_container_width=True)

                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    summary_df.to_excel(writer, sheet_name="Recovery Summary Matrix", index=False)
                
                st.download_button(
                    label="📥 Export Dynamic Summary to Excel",
                    data=excel_buffer.getvalue(),
                    file_name="Branch_Recovery_Metrics.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("System awaiting secure file upload.")
        # ==========================================
# MODULE 3: FILE MERGING UTILITIES
# ==========================================
elif app_mode == "📁 File Merge Utilities":
    st.markdown('<div class="report-card"><h3>📁 Relational Matrix Merging Utility</h3><p>Join structural tracking files together by extracting and mapping codes automatically.</p></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        merge_file = st.file_uploader("Upload Core Tracking File (With Sanction Identifiers)", type=["xlsx","xls","csv"], key="m_u")
    with col2:
        branch_file = st.file_uploader("Upload Branch Mapping Key File", type=["xlsx","xls","csv"], key="b_u")

    if merge_file and branch_file:
        df_merge = pd.read_csv(merge_file) if merge_file.name.endswith(".csv") else pd.read_excel(merge_file)
        df_branch = pd.read_csv(branch_file) if branch_file.name.endswith(".csv") else pd.read_excel(branch_file)

        df_merge.columns = df_merge.columns.str.strip()
        df_branch.columns = df_branch.columns.str.strip()

        # Find variants of sanction/branch codes automatically
        s_col = next((c for c in df_merge.columns if "sanction" in c.lower()), None)
        b_col = next((c for c in df_branch.columns if "branch" in c.lower() or "code" in c.lower()), None)

        if s_col and b_col:
            df_merge['Extractor_Key'] = df_merge[s_col].astype(str).str[:4]
            df_branch['Extractor_Key'] = df_branch[b_col].astype(str)

            merged_df = pd.merge(df_merge, df_branch, on='Extractor_Key', how='left').drop(columns=['Extractor_Key'])
            st.success("Files compiled and integrated successfully! Preview:")
            st.dataframe(merged_df, use_container_width=True)
            
            out_buf = BytesIO()
            merged_df.to_excel(out_buf, index=False)
            st.download_button("Download Unified Master Sheet", data=out_buf.getvalue(), file_name="Merged_Output_Master.xlsx")
        else:
            st.error("Could not trace clean identity keys 'Sanction No' or 'Branch Code' fields automatically.")


# ==========================================
# MODULE 4: OVERDUE DETECTION TRACKER
# ==========================================
elif app_mode == "🕒 Overdue Tracker":
    st.markdown('<div class="report-card"><h3>🕒 Chrono-Overdue Defaulter Track Engine</h3><p>Cross-references expected portfolios against received tallies to generate active missing accounts list.</p></div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        do_file = st.file_uploader("Upload Target Allocation Matrix (Do List)", type=["xlsx", "xls"])
    with c2:
        recovery_file = st.file_uploader("Upload Real-Time Clearing Ledger", type=["xlsx", "xls"])

    if do_file and recovery_file:
        do_df = pd.read_excel(do_file)
        rec_df = pd.read_excel(recovery_file)

        do_df.columns = [c.strip() for c in do_df.columns]
        rec_df.columns = [c.strip() for c in rec_df.columns]

        do_key = next((c for c in do_df.columns if "sanction" in c.lower() or "no" in c.lower()), None)
        rec_key = next((c for c in rec_df.columns if "sanction" in c.lower() or "no" in c.lower()), None)

        if do_key and rec_key:
            do_df["Clean_Key"] = do_df[do_key].astype(str).str.strip()
            rec_df["Clean_Key"] = rec_df[rec_key].astype(str).str.strip()

            overdue_df = do_df[~do_df["Clean_Key"].isin(rec_df["Clean_Key"])].drop(columns=["Clean_Key"])
            
            # Summary Metrics Layout
            cc1, cc2 = st.columns(2)
            cc1.metric("Expected Targeted Accounts", len(do_df))
            cc2.metric("⚠️ Total Identified Overdue Defaulters", len(overdue_df), delta_color="inverse")
            
            st.dataframe(overdue_df, use_container_width=True)
            
            out_ov = BytesIO()
            overdue_df.to_excel(out_ov, index=False)
            st.download_button("📥 Download Overdue Tracker Report", data=out_ov.getvalue(), file_name="Overdue_Defaulters_List.xlsx")
        else:
            st.error("Mapping requires matching tracking ID columns across both uploaded excel spreadsheets.")


# ==========================================
# MODULE 5: CHEQUE-WISE ANALYSIS
# ==========================================
elif app_mode == "📑 Cheque-wise Analysis":
    st.markdown('<div class="report-card"><h3>📑 Editable Cheque Portfolio Grid</h3><p>Upload data to dynamically change values, correct inline inconsistencies on the fly, and view summaries instantly.</p></div>', unsafe_allow_html=True)
    
    uploaded_cheque = st.file_uploader("Upload Bank Clearings Master File", type=["xlsx", "csv"])

    if uploaded_cheque:
        chq_df = pd.read_csv(uploaded_cheque) if uploaded_cheque.name.endswith(".csv") else pd.read_excel(uploaded_cheque)
        chq_df.columns = [str(c).strip() for c in chq_df.columns]

        st.subheader("Interactive System Cell Grid Architecture")
        # Secure, editable spreadsheet matrix view
        edited_df = st.data_editor(chq_df, use_container_width=True)
        
        # Quick inline metrics calculation based on updates
        st.markdown("---")
        st.markdown("#### 📈 Quick Grid Analysis")
        col_summary, col_rows = st.columns(2)
        col_summary.info(f"**Total Tracked Records:** {len(edited_df)}")
        if len(edited_df) > 0:
            numeric_cols = edited_df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                col_rows.success(f"**Sum Total (Primary Value Column):** {edited_df[numeric_cols[0]].sum():,}")


# ==========================================
# MODULE 6: LOAN DISBURSEMENT PDF
# ==========================================
elif app_mode == "📄 Loan Disbursement PDF":
    st.markdown('<div class="report-card"><h3>📄 Automated Structural PDF Engine</h3><p>Converts operational transactional excel variables straight into cleanly typeset printable ledger layout books.</p></div>', unsafe_allow_html=True)
    
    uploaded_loan = st.file_uploader("Upload Verified Disbursement Master Excel", type=["xlsx"])

    if uploaded_loan:
        loan_df = pd.read_excel(uploaded_loan)
        st.success("Dataset loaded successfully! Generation preview matches formatting bounds.")
        st.dataframe(loan_df.head(5), use_container_width=True)

        # PDF Compilation Engine Blueprint
        if st.button("🏗️ Construct Report Files", type="primary"):
            buf = BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            story.append(Paragraph("<b>LOAN DISBURSEMENT SYSTEM EXECUTIVE REPORT</b>", styles['Title']))
            story.append(Spacer(1, 15))

            # Build structural data grid array for PDF rendering
            data_matrix = [list(loan_df.columns)[:5]]  # Header boundaries
            for idx, row in loan_df.head(20).iterrows():
                data_matrix.append([str(val)[:20] for val in row[:5]])

            pdf_table = Table(data_matrix)
            pdf_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.navy),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('GRID', (0,0), (-1,-1), 1, colors.grey),
            ]))
            story.append(pdf_table)
            doc.build(story)

            st.download_button(
                "📥 Download Compiled Report PDF",
                data=buf.getvalue(),
                file_name=f"Disbursement_Report_{datetime.now().strftime('%d_%b')}.pdf",
                mime="application/pdf"
            )
