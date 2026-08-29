import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import qrcode
from io import BytesIO
import os
import io
import zipfile
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fpdf import FPDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- 1. PAGE CONFIG (Must be the VERY FIRST Streamlit command) ----------------
st.set_page_config(
    page_title="CNIC QR & Recovery Summary App",
    page_icon="📊",
    layout="wide"
)

# ---------------- 2. USERS & LOGIN ----------------
USERS = {"Khaleel": "1.2341", "user": "1111"}

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] {background: linear-gradient(135deg,#0f2027,#203a43,#2c5364); }
        h2, label {color: white !important; text-align: center; }
        .stButton>button {background: #00c6ff; color: white; border-radius: 10px; height: 40px; font-weight: bold; }
        .stButton>button:hover {background: #0072ff; }
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

# FIXED FIRST 12 DIGITS FOR CNIC QR GENERATOR
FIXED_FIRST_12 = "421011234567"

st.markdown("""
<div style="background: linear-gradient(135deg, #1e293b, #0f172a); padding: 25px; border-radius: 16px; border: 1px solid #334155; text-align: center; margin-bottom: 25px;">
    <h2 style="color: #ffffff; margin-bottom: 6px;">🪪 CNIC QR & Recovery Reports Manager</h2>
</div>
""", unsafe_allow_html=True)

# ---------------- 3. SECTION: CNIC QR GENERATOR ----------------
st.subheader("🪪 CNIC QR Generator")
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    user_13_digit = st.text_input("Just Enter CNIC NO", placeholder="مثال: 3720388692193", max_chars=13)
    generate_btn = st.button("✨ QR Code بنائیں", type="primary", use_container_width=True)

    if generate_btn:
        if user_13_digit:
            clean_13 = user_13_digit.replace("-", "").strip()
            full_cnic = FIXED_FIRST_12 + clean_13
            if clean_13.isdigit() and len(full_cnic) == 25:
                qr = qrcode.QRCode(
                    version=None,
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=5,
                    border=4,
                )
                qr.add_data(full_cnic)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                buf = BytesIO()
                img.save(buf, format="PNG")
                img_bytes = buf.getvalue()

                st.markdown("---")
                st.image(img_bytes, caption="QR Code Ready", use_column_width=True)
                st.download_button(
                    "📥 QR Code ڈاؤنلوڈ کریں",
                    data=img_bytes,
                    file_name="cnic_qr.png",
                    mime="image/png",
                    use_container_width=True
                )
            else:
                st.error("❌ Invalid! Must Enter 13 Digit")
        else:
            st.warning("Please Enter CNIC NO Without Dashes")

# ---------------- 4. SECTION: MERGE SANCTION & BRANCH FILE ----------------
st.markdown("---")
st.subheader("📁 Merge Sanction & Branch File")
col1, col2 = st.columns(2)
with col1:
    merge_file = st.file_uploader("Upload Merge File (Sanction No)", type=["xlsx", "xls", "csv"], key="merge_file")
with col2:
    branch_file = st.file_uploader("Upload Branch File (Branch Code)", type=["xlsx", "xls", "csv"], key="branch_file")

if merge_file and branch_file:
    try:
        df_merge = pd.read_csv(merge_file) if merge_file.name.endswith(".csv") else pd.read_excel(merge_file)
        df_branch = pd.read_csv(branch_file) if branch_file.name.endswith(".csv") else pd.read_excel(branch_file)

        df_merge.columns = df_merge.columns.str.strip()
        df_branch.columns = df_branch.columns.str.strip()

        if 'sanctionno' in df_merge.columns and 'branch code' in df_branch.columns:
            df_merge['Sanction_Prefix'] = df_merge['sanctionno'].astype(str).str[:4]
            df_branch['branch code'] = df_branch['branch code'].astype(str)

            merged_df = pd.merge(
                df_merge,
                df_branch.rename(columns={'branch code': 'Sanction_Prefix'}),
                on='Sanction_Prefix',
                how='left'
            )

            if 'branch_name' in merged_df.columns and 'area_name' in merged_df.columns:
                b_col = merged_df.pop('branch_name')
                a_col = merged_df.pop('area_name')
                merged_df.insert(2, 'Branch Name', b_col)
                merged_df.insert(3, 'Area Name', a_col)

            st.dataframe(merged_df, use_container_width=True)

            out_buf = BytesIO()
            with pd.ExcelWriter(out_buf, engine='openpyxl') as writer:
                merged_df.to_excel(writer, index=False, sheet_name='Merged_Report')
            
            st.download_button(
                "📥 Download Merged File",
                data=out_buf.getvalue(),
                file_name="Merged_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Required columns ('sanctionno' in Merge File, 'branch code' in Branch File) missing.")
    except Exception as e:
        st.error(f"Error processing files: {e}")

# ---------------- 5. SECTION: RECOVERY SUMMARY & COMPARISON ----------------
st.markdown("---")
st.subheader("📊 Recovery Date Range & Monthly Summary")

LOCAL_FILE = "data/recovery.xlsx"
os.makedirs("data", exist_ok=True)

uploaded = st.file_uploader("Upload Recovery Excel / CSV", type=["xlsx", "csv"], key="recovery_main")

if uploaded:
    df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
    st.session_state["df"] = df
    df.to_excel(LOCAL_FILE, index=False)
    st.success("File uploaded and saved locally!")
elif "df" in st.session_state:
    df = st.session_state["df"]
elif os.path.exists(LOCAL_FILE):
    df = pd.read_excel(LOCAL_FILE)
    st.session_state["df"] = df
else:
    st.info("Please upload recovery file to view details.")
    st.stop()

# --- Dynamic Column Select ---
st.write("#### Available Columns Selection")
col1, col2 = st.columns(2)
with col1:
    date_col = st.selectbox("Select Date Column", df.columns, index=0)
with col2:
    branch_col = st.selectbox("Select Branch Column (branch_id)", df.columns, index=min(1, len(df.columns)-1))

area_col = 'area_id' if 'area_id' in df.columns else None

# Safe Date Conversion
df[date_col] = pd.to_datetime(df[date_col].astype(str).str.strip(), errors="coerce")
df = df.dropna(subset=[date_col, branch_col])

if df.empty:
    st.error("Selected Date column me valid data nahi hai.")
    st.stop()

df["Day"] = df[date_col].dt.day
df["Month_Name"] = df[date_col].dt.strftime('%b')
df["Month_Num"] = df[date_col].dt.month

df["Range"] = pd.cut(df["Day"], bins=[0, 5, 10, 15, 31], labels=["1-5", "6-10", "11-15", "16-31"])

# --- Summary Pivot ---
pivot = pd.pivot_table(df, index=[branch_col], columns="Range", aggfunc="size", fill_value=0)
for c in ["1-5", "6-10", "11-15", "16-31"]:
    if c not in pivot.columns:
        pivot[c] = 0

pivot["Total"] = pivot[["1-5", "6-10", "11-15", "16-31"]].sum(axis=1)
pivot["1-5 %"] = (pivot["1-5"] / pivot["Total"] * 100).round(2)
pivot["6-10 %"] = (pivot["6-10"] / pivot["Total"] * 100).round(2)
pivot["11-15 %"] = (pivot["11-15"] / pivot["Total"] * 100).round(2)
pivot["16-31 %"] = (pivot["16-31"] / pivot["Total"] * 100).round(2)

pivot.rename(columns={
    "1-5": "Recovery 1-5",
    "6-10": "Recovery 6-10",
    "11-15": "Recovery 16-15",
    "16-31": "Recovery 16-31"
}, inplace=True)

result_df = pivot.reset_index()

if area_col:
    branch_area_df = df[[branch_col, area_col]].drop_duplicates()
    result_df = result_df.merge(branch_area_df, on=branch_col, how='left')
    cols = result_df.columns.tolist()
    branch_idx = cols.index(branch_col)
    cols.insert(branch_idx, cols.pop(cols.index(area_col)))
    result_df = result_df[cols]

# Grand Total Row
numeric_cols = ["Recovery 1-5", "Recovery 6-10", "Recovery 16-15", "Recovery 16-31", "Total"]
grand_total_counts = result_df[numeric_cols].sum()
grand_total_percent = (grand_total_counts[["Recovery 1-5", "Recovery 6-10", "Recovery 16-15", "Recovery 16-31"]] / grand_total_counts["Total"] * 100).round(2)

grand_values = {}
for col in result_df.columns:
    if col == branch_col:
        grand_values[col] = "Grand Total"
    elif col == area_col:
        grand_values[col] = ""
    elif col in numeric_cols:
        grand_values[col] = grand_total_counts[col]
    elif col in ["1-5 %", "6-10 %", "11-15 %", "16-31 %"]:
        pct_map = {
            "1-5 %": "Recovery 1-5", 
            "6-10 %": "Recovery 6-10", 
            "11-15 %": "Recovery 16-15", 
            "16-31 %": "Recovery 16-31"
        }
    # ---------------- 5. SECTION: RECOVERY SUMMARY & COMPARISON ----------------
st.markdown("---")
st.subheader("📊 Recovery Date Range & Monthly Summary")

LOCAL_FILE = "data/recovery.xlsx"
os.makedirs("data", exist_ok=True)

uploaded = st.file_uploader("Upload Recovery Excel / CSV - 1 یا 2-3 مہینے ایک ساتھ", type=["xlsx", "csv"], key="recovery_main", accept_multiple_files=True)

if uploaded:
    dfs = []
    for file in uploaded:
        df_temp = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
        df_temp["Source_File"] = file.name # کونسی فائل سے ہے یہ ٹریک کرنے کے لیے
        dfs.append(df_temp)
    df = pd.concat(dfs, ignore_index=True)
    st.session_state["df"] = df
    df.to_excel(LOCAL_FILE, index=False)
    st.success(f"{len(uploaded)} فائل(یں) Upload ہو گئیں اور Merge کر دی گئیں!")
    st.rerun()
elif "df" in st.session_state:
    df = st.session_state["df"]
elif os.path.exists(LOCAL_FILE):
    df = pd.read_excel(LOCAL_FILE)
    st.session_state["df"] = df
else:
    st.info("Please upload recovery file to view details.")
    st.stop()

st.write("#### Available Columns Selection")
col1, col2 = st.columns(2)
with col1:
    date_col = st.selectbox("Select Date Column", df.columns, index=0)
with col2:
    branch_col = st.selectbox("Select Branch Column", df.columns, index=min(1, len(df.columns)-1))

area_col = 'area_id' if 'area_id' in df.columns else None

# Safe Date Conversion
df[date_col] = pd.to_datetime(df[date_col].astype(str).str.strip(), errors="coerce")
df = df.dropna(subset=[date_col, branch_col])

if df.empty:
    st.error("Selected Date column me valid data nahi hai.")
    st.stop()

df["Day"] = df[date_col].dt.day
df["Month_Name"] = df[date_col].dt.strftime('%b-%Y') # Year بھی شامل کر دیا تاکہ Jan-2025 vs Jan-2026 کا فرق ہو
df["Month_Num"] = df[date_col].dt.month
df["Range"] = pd.cut(df["Day"], bins=[0, 5, 10, 15, 31], labels=["1-5", "6-10", "11-15", "16-31"])

# --- SMART TABLE LOGIC ---
unique_areas = df[area_col].nunique() if area_col else 0

if unique_areas > 1:
    st.info(f"✅ {unique_areas} Areas ملے۔ Table اب Area Wise بنے گا۔")
    group_cols = [area_col, "Month_Name", "Range"]
    index_col = area_col
    display_name = "Area Wise Recovery Summary"
else:
    st.info("✅ صرف 1 Area ملا۔ Table اب Branch Wise بنے گا۔")
    group_cols = [branch_col, "Month_Name", "Range"]
    index_col = branch_col
    display_name = "Branch Wise Recovery Summary"

st.subheader(f"📈 {display_name}")

# Pivot بنائیں: Index = Area/Branch, Columns = Month + Range, Values = Count
pivot = pd.pivot_table(
    df,
    index=group_cols,
    aggfunc="size",
    fill_value=0
).unstack(["Month_Name", "Range"])

# Column names صاف کریں
pivot.columns = [f'{month} - {rng}' for month, rng in pivot.columns]
pivot = pivot.reset_index()

# ہر مہینے کا Total اور % نکالیں
months = df["Month_Name"].unique()
for month in months:
    month_cols = [col for col in pivot.columns if month in col]
    if month_cols:
        pivot[f'{month} - Total'] = pivot[month_cols].sum(axis=1)
        for rng in ["1-5", "6-10", "11-15", "16-31"]:
            rng_col = f'{month} - {rng}'
            pct_col = f'{month} - {rng} %'
            if rng_col in pivot.columns:
                pivot[pct_col] = (pivot[rng_col] / pivot[f'{month} - Total'] * 100).round(2)

# Grand Total Row
numeric_cols = [col for col in pivot.columns if col not in [index_col]]
grand_values = {}
for col in pivot.columns:
    if col == index_col:
        grand_values[col] = "Grand Total"
    elif "%" in col:
        # % کا Grand Total الگ سے نہیں بنے گا
        grand_values[col] = ""
    else:
        grand_values[col] = pivot[col].sum()

pivot = pd.concat([pivot, pd.DataFrame([grand_values])], ignore_index=True)

st.dataframe(pivot, use_container_width=True)

# Download
out_buf = BytesIO()
with pd.ExcelWriter(out_buf, engine='openpyxl') as writer:
    pivot.to_excel(writer, index=False, sheet_name='Recovery_Summary')
st.download_button("📥 Download Summary Excel", data=out_buf.getvalue(), file_name="Recovery_Summary.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# --- Month-over-Month Comparison Heatmap ---
st.markdown("---")
st.subheader("📅 Month-over-Month Comparison Chart")
if len(months) > 1:
    chart_df = df.groupby([index_col, "Month_Name"]).size().reset_index(name="Total")
    fig = px.bar(chart_df, x=index_col, y="Total", color="Month_Name", barmode="group", title=f"{display_name} - Month Comparison")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Comparison کے لیے کم از کم 2 مہینے کی ڈیٹا Upload کریں۔")
