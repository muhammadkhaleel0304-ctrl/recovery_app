import io
import os
import zipfile
import calendar
from io import BytesIO
from datetime import datetime

import qrcode
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import matplotlib.pyplot as plt
from fpdf import FPDF
from dateutil.relativedelta import relativedelta

# ReportLab Elements
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ==========================================
# 1. PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(page_title="🏦 Recovery & Reports App", layout="wide")

# ---------- USERS ----------
USERS = {"Khaleel": "11234", "user": "1111"}

# ---------- SESSION STATE ----------
if "login" not in st.session_state:
    st.session_state.login = False

# ---------- LOGIN PAGE ----------
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
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 🔐 Login")
        user = st.text_input("Username")
        pwd = st.text_input("Password", type="password")
        login_btn = st.button("Login", use_container_width=True)
        
        if login_btn:
            if USERS.get(user) == pwd:
                st.session_state.login = True
                st.success("Login successful ✔")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
        st.stop()

# ==========================================
# MAIN APPLICATION (AFTER SUCCESSFUL LOGIN)
# ==========================================
st.title("🏦 Recovery & Reports App")

# Create a clean sidebar or tabs for better UX navigation
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 CNIC QR Generator", 
    "📊 Recovery Month Summary", 
    "📁 Merge Files", 
    "🕒 Overdue Detection & Reports"
])

# ------------------------------------------
# TAB 1: CNIC QR GENERATOR
# ------------------------------------------
with tab1:
    st.subheader("CNIC QR Generator")
    cnic = st.text_input("Enter 13-digit CNIC")
    if st.button("Generate QR"):
        if cnic:
            data = str(cnic).strip()
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4
            )
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()
            
            st.image(img_bytes)
            st.download_button(
                "Download QR", data=img_bytes, file_name="cnic_qr.png", mime="image/png"
            )
        else:
            st.warning("Enter CNIC")

# ------------------------------------------
# TAB 2: RECOVERY MONTH WISE SUMMARY
# ------------------------------------------
with tab2:
    st.subheader("📊 Recovery Month Wise & Branch Wise Summary")
    
    os.makedirs("data", exist_ok=True)
    LOCAL_FILE = "data/recovery.xlsx"
    
    uploaded = st.file_uploader("Upload Recovery File", type=["xlsx", "csv"], key="recovery_month_file")
    
    if uploaded:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)
        st.session_state["df"] = df
        df.to_excel(LOCAL_FILE, index=False)
    elif "df" in st.session_state:
        df = st.session_state["df"]
    elif os.path.exists(LOCAL_FILE):
        df = pd.read_excel(LOCAL_FILE)
        st.session_state["df"] = df
    else:
        st.info("Upload file first")
        df = None

    if df is not None:
        required_cols = ["branch_id", "recovery_date", "receipt_no"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"Missing Columns: {missing}")
        else:
            df["recovery_date"] = pd.to_datetime(df["recovery_date"], errors="coerce")
            df = df.dropna(subset=["recovery_date"])
            
            df["Month"] = df["recovery_date"].dt.to_period("M")
            df["Day"] = df["recovery_date"].dt.day
            
            def get_range(day):
                if day <= 10: return "1-10"
                elif day <= 20: return "11-20"
                else: return "21-31"
            
            df["Range"] = df["Day"].apply(get_range)
            
            summary_rows = []
            for branch in sorted(df["branch_id"].unique()):
                branch_df = df[df["branch_id"] == branch]
                for month in sorted(branch_df["Month"].unique()):
                    month_df = branch_df[branch_df["Month"] == month]
                    rec_1_10 = len(month_df[month_df["Range"] == "1-10"])
                    rec_11_20 = len(month_df[month_df["Range"] == "11-20"])
                    rec_21_31 = len(month_df[month_df["Range"] == "21-31"])
                    total = len(month_df)
                    
                    if total == 0: continue
                    
                    pct_1_10 = round(rec_1_10 / total * 100, 2)
                    pct_11_20 = round(rec_11_20 / total * 100, 2)
                    pct_21_31 = round(rec_21_31 / total * 100, 2)
                    
                    last_date = month_df["recovery_date"].max()
                    last_day = last_date.day
                    year = last_date.year
                    month_no = last_date.month
                    month_last_day = calendar.monthrange(year, month_no)[1]
                    close_rate = round(last_day / month_last_day * 100, 2)
                    
                    summary_rows.append({
                        "Branch": branch, "Month": month, "Recovery 1-10": rec_1_10, "1-10 %": pct_1_10,
                        "Recovery 11-20": rec_11_20, "11-20 %": pct_11_20, "Recovery 21-31": rec_21_31, "21-31 %": pct_21_31,
                        "Total Slips": total, "Last Recovery Date": last_date.strftime("%Y-%b-%d"), "Close Rate %": close_rate
                    })
            
            summary_df = pd.DataFrame(summary_rows)
            summary_df = summary_df.sort_values(["Branch", "Month"]).reset_index(drop=True)
            summary_df["Month"] = pd.to_datetime(summary_df["Month"].astype(str)).dt.strftime("%b-%Y")
            
            st.subheader("Month Wise Branch Summary")
            st.dataframe(summary_df, use_container_width=True)
            
            branch_month_summary = df.groupby(["Month", "branch_id"]).size().reset_index(name="Total Slips")
            branch_month_summary = branch_month_summary.sort_values(["Month", "branch_id"])
            st.subheader("📌 Branch Wise Month Summary")
            st.dataframe(branch_month_summary, use_container_width=True)
            
            if not summary_df.empty:
                grand_row = {
                    "Branch": "Grand Total", "Month": "", "Recovery 1-10": summary_df["Recovery 1-10"].sum(),
                    "1-10 %": round(summary_df["Recovery 1-10"].sum() / summary_df["Total Slips"].sum() * 100, 2),
                    "Recovery 11-20": summary_df["Recovery 11-20"].sum(),
                    "11-20 %": round(summary_df["Recovery 11-20"].sum() / summary_df["Total Slips"].sum() * 100, 2),
                    "Recovery 21-31": summary_df["Recovery 21-31"].sum(),
                    "21-31 %": round(summary_df["Recovery 21-31"].sum() / summary_df["Total Slips"].sum() * 100, 2),
                    "Total Slips": summary_df["Total Slips"].sum(), "Last Recovery Date": "",
                    "Close Rate %": round(summary_df["Close Rate %"].mean(), 2)
                }
                summary_df = pd.concat([summary_df, pd.DataFrame([grand_row])], ignore_index=True)
            
            # --- Downloads ---
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    summary_df.to_excel(writer, sheet_name="Month_Wise_Summary", index=False)
                    branch_month_summary.to_excel(writer, sheet_name="Branch_Month_Summary", index=False)
                st.download_button(label="📊 Download Excel", data=excel_buffer.getvalue(), file_name="Recovery_Month_Wise.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            with col_d2:
                pdf_buffer = BytesIO()
                doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4))
                table_data = ([summary_df.columns.tolist()] + summary_df.values.tolist())
                pdf_table = Table(table_data)
                pdf_table.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 1, colors.black),
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTSIZE', (0,0), (-1,-1), 8)
                ]))
                doc.build([pdf_table])
                st.download_button(label="📄 Download PDF", data=pdf_buffer.getvalue(), file_name="Recovery_Month_Wise.pdf", mime="application/pdf")
            
            with col_d3:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                    branches = summary_df["Branch"].dropna().unique()
                    for branch in branches:
                        if branch == "Grand Total": continue
                        branch_df = summary_df[summary_df["Branch"] == branch]
                        branch_pdf = BytesIO()
                        doc = SimpleDocTemplate(branch_pdf, pagesize=landscape(A4))
                        data = ([branch_df.columns.tolist()] + branch_df.values.tolist())
                        tbl = Table(data)
                        tbl.setStyle(TableStyle([
                            ('GRID',(0,0),(-1,-1),1,colors.black),
                            ('BACKGROUND',(0,0),(-1,0),colors.lightgrey),
                            ('ALIGN',(0,0),(-1,-1),'CENTER'),
                            ('FONTSIZE',(0,0),(-1,-1),8),
                        ]))
                        doc.build([tbl])
                        zipf.writestr(f"{branch}.pdf", branch_pdf.getvalue())
                st.download_button(label="📦 Download Branch PDFs ZIP", data=zip_buffer.getvalue(), file_name="Branch_Wise_PDFs.zip", mime="application/zip")
            
            st.subheader("Final Recovery Summary")
            st.dataframe(summary_df, use_container_width=True)

# ------------------------------------------
# TAB 3: MERGE SANCTION & BRANCH FILE
# ------------------------------------------
with tab3:
    st.subheader("📁 Merge Sanction & Branch File")
    col1, col2 = st.columns(2)
    with col1:
        merge_file = st.file_uploader("Upload Merge File (Sanction No)", type=["xlsx","xls","csv"], key="merge_file")
    with col2:
        branch_file = st.file_uploader("Upload Branch File (Branch Code)", type=["xlsx","xls","csv"], key="branch_file")
        
    merge_table_placeholder = st.empty()
    merge_download_placeholder = st.empty()
    
    if merge_file and branch_file:
        try:
            df_merge = pd.read_csv(merge_file) if merge_file.name.endswith(".csv") else pd.read_excel(merge_file)
            df_branch = pd.read_csv(branch_file) if branch_file.name.endswith(".csv") else pd.read_excel(branch_file)
            
            df_merge.columns = df_merge.columns.str.strip()
            df_branch.columns = df_branch.columns.str.strip()
            
            if 'sanctionno' not in df_merge.columns:
                st.error("Merge File must have column 'sanctionno'")
            elif 'branch code' not in df_branch.columns or 'branch_name' not in df_branch.columns or 'area_name' not in df_branch.columns:
                st.error("Branch File must have columns 'branch code', 'branch_name', 'area_name'")
            else:
                df_merge['Sanction_Prefix'] = df_merge['sanctionno'].astype(str).str[:4]
                df_branch['branch code'] = df_branch['branch code'].astype(str)
                
                merged_df = pd.merge(df_merge, df_branch.rename(columns={'branch code':'Sanction_Prefix'}), on='Sanction_Prefix', how='left')
                
                if 'branch_name' in merged_df.columns and 'area_name' in merged_df.columns:
                    branch_col = merged_df.pop('branch_name')
                    area_col = merged_df.pop('area_name')
                    merged_df.insert(2, 'Branch Name', branch_col)
                    merged_df.insert(3, 'Area Name', area_col)
                
                merge_table_placeholder.dataframe(merged_df)
                
                def to_excel(df):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Merged_Report')
                    return output.getvalue()
                
                excel_data = to_excel(merged_df)
                merge_download_placeholder.download_button(
                    label="📥 Download Merged File", data=excel_data, file_name="Merged_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="merge_download"
                )
        except Exception as e:
            merge_table_placeholder.error(f"Error processing files: {e}")
    else:
        merge_table_placeholder.info("Upload both Merge File and Branch File to generate merged report.")

# ------------------------------------------
# TAB 4: DUE LIST & OVERDUE DETECTION
# ------------------------------------------
with tab4:
    st.subheader("📥 Upload Due List and Recovery File for Overdue Detection")
    
    do_file = st.file_uploader("📄 Due List Upload", type=["xlsx", "xls"], key="uploader_do")
    recovery_file = st.file_uploader("📄 Recovery File Upload", type=["xlsx", "xls"], key="uploader_recovery")
    terabyte_file = st.file_uploader("📄 Terabyte File Upload (Optional)", type=["xlsx", "xls"], key="uploader_terabyte")
    
    if do_file and recovery_file:
        do_df = pd.read_excel(do_file)
        recovery_df = pd.read_excel(recovery_file)
        
        do_df.columns = do_df.columns.str.strip()
        recovery_df.columns = recovery_df.columns.str.strip()
        
        if 'Sanction No' not in do_df.columns or 'Sanction No' not in recovery_df.columns:
            st.error("Both Do List and Recovery File must contain 'Sanction No' column.")
        else:
            do_df['Sanction No'] = do_df['Sanction No'].astype(str).str.strip()
            recovery_df['Sanction No'] = recovery_df['Sanction No'].astype(str).str.strip()
            
            overdue_df = do_df[~do_df['Sanction No'].isin(recovery_df['Sanction No'])].copy()
            
            st.subheader("🕒 Final Overdue List")
            st.write(f"🔢 Total Overdue: {len(overdue_df)}")
            st.dataframe(overdue_df)
            
            # Final Overdue via Terabyte logic
            final_overdue_df = overdue_df.copy()
            if terabyte_file and not overdue_df.empty:
                terabyte_df = pd.read_excel(terabyte_file)
                terabyte_df.columns = terabyte_df.columns.str.strip()
                if 'Sanction No' in terabyte_df.columns:
                    terabyte_df['Sanction No'] = terabyte_df['Sanction No'].astype(str).str.strip()
                    final_overdue_df = overdue_df[~overdue_df['Sanction No'].isin(terabyte_df['Sanction No'])]
                    st.subheader("🚨 Final Overdue Cases (After Terabyte)")
                    st.write(f"🔢 Total Final Overdue: {len(final_overdue_df)}")
                    st.dataframe(final_overdue_df)
            
            # PDF Processing Class
            class PDF(FPDF):
                def header(self): pass
                def footer(self): pass

            if 'branch_id' not in final_overdue_df.columns:
                final_overdue_df['branch_id'] = 'Unknown'
                
            # Full PDF Download
            if not final_overdue_df.empty:
                full_pdf = FPDF()
                full_pdf.set_auto_page_break(auto=True, margin=15)
                for branch in final_overdue_df['branch_id'].unique():
                    data = final_overdue_df[final_overdue_df['branch_id'] == branch]
                    full_pdf.add_page()
                    full_pdf.set_font("Arial", 'B', 12)
                    full_pdf.cell(200, 10, txt=f"Branch: {branch}", ln=True, align='C')
                    full_pdf.set_font("Arial", size=10)
                    full_pdf.cell(10, 10, "Sr#", 1)
                    full_pdf.cell(70, 10, "Name", 1)
                    full_pdf.cell(60, 10, "Sanction No", 1)
                    full_pdf.ln()
                    for i, (_, row) in enumerate(data.iterrows(), start=1):
                        full_pdf.cell(10, 10, str(i), 1)
                        full_pdf.cell(70, 10, str(row.get('Name', '')), 1)
                        full_pdf.cell(60, 10, str(row.get('Sanction No', '')), 1)
                        full_pdf.ln()
                
                full_pdf_output = full_pdf.output(dest='S').encode('latin1')
                st.download_button("📥 Download Final Overdue PDF (Branch-wise)", full_pdf_output, "final_overdue.pdf", "application/pdf")
            
                # ZIP Download for separate branches
                st.subheader("📁 Download Branch-wise Final Overdue (ZIP)")
                branches = final_overdue_df['branch_id'].astype(str).unique()
                zip_buf_overdue = io.BytesIO()
                with zipfile.ZipFile(zip_buf_overdue, "a", zipfile.ZIP_DEFLATED) as zf:
                    for branch in branches:
                        branch_data = final_overdue_df[final_overdue_df['branch_id'].astype(str) == str(branch)]
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.set_font("Arial", size=10)
                        pdf.cell(0, 10, f"Branch: {branch}", ln=True)
                        pdf.set_font("Arial", "B", 10)
                        pdf.cell(10, 10, "Sr#", 1)
                        pdf.cell(60, 10, "Name", 1)
                        pdf.cell(50, 10, "Sanction No", 1)
                        if "Mobile No" in branch_data.columns:
                            pdf.cell(50, 10, "Mobile No", 1)
                        pdf.ln()
                        pdf.set_font("Arial", size=9)
                        for i, (_, row) in enumerate(branch_data.iterrows(), start=1):
                            pdf.cell(10, 10, str(i), 1)
                            pdf.cell(60, 10, str(row.get("Name", ""))[:25], 1)
                            pdf.cell(50, 10, str(row.get("Sanction No", "")), 1)
                            if "Mobile No" in branch_data.columns:
                                pdf.cell(50, 10, str(row.get("Mobile No", "")), 1)
                            pdf.ln()
                        zf.writestr(f"{branch}_Final_Overdue.pdf", pdf.output(dest="S").encode("latin1"))
                
                st.download_button(label="⬇️ Download Branch-wise Overdue ZIP", data=zip_buf_overdue.getvalue(), file_name="Final_Overdue_BranchWise.zip", mime="application/zip", key="download_overdue_zip")

            # --- Month Summary Analytics Inside Overdue ---
            if 'recovery_date' in recovery_df.columns:
                recovery_df['recovery_date'] = pd.to_datetime(recovery_df['recovery_date'], errors='coerce')
                current_month = pd.Timestamp.now().month
                current_year = pd.Timestamp.now().year
                recovery_this_month = recovery_df[(recovery_df['recovery_date'].dt.month == current_month) & (recovery_df['recovery_date'].dt.year == current_year)]
                recovered = recovery_this_month[recovery_this_month['Sanction No'].isin(do_df['Sanction No'])]
                
                if 'branch_id' not in do_df.columns: do_df['branch_id'] = do_df.get('Branch', '')
                if 'branch_id' not in recovery_df.columns: recovery_df['branch_id'] = recovery_df.get('Branch Code', '')
                
                due_summary = do_df.groupby('branch_id')['Sanction No'].count().reset_index().rename(columns={'Sanction No': 'total_due'})
                recovered_summary = recovered.groupby('branch_id')['Sanction No'].count().reset_index().rename(columns={'Sanction No': 'recovered'})
                
                summary = due_summary.merge(recovered_summary, on='branch_id', how='left').fillna(0)
                summary['remaining'] = summary['total_due'] - summary['recovered']
                summary['recovery_percent'] = (summary['recovered'] / summary['total_due'].replace(0, pd.NA)) * 100
                summary['recovery_percent'] = summary['recovery_percent'].fillna(0)
                
                st.subheader("📋 Branch-wise Recovery Summary (This Month)")
                st.dataframe(summary.style.format({'total_due': '{:,.0f}', 'recovered': '{:,.0f}', 'remaining': '{:,.0f}', 'recovery_percent': '{:.2f} %'}))
                
                try:
                    fig = px.bar(summary, x='branch_id', y='recovery_percent', text=summary['recovery_percent'].apply(lambda x: f"{x:.1f}%"),
                                 labels={'branch_id': 'Branch', 'recovery_percent': 'Recovery %'}, title='📈 Recovery % by Branch (This Month)')
                    fig.update_traces(textposition='outside')
                    st.plotly_chart(fig, use_container_width=True)
                except Exception:
                    pass
