import streamlit as st
import pandas as pd
import numpy as np

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Range-Wise Recovery Comparison",
    page_icon="📊",
    layout="wide"
)

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>

.main {
    background: #f4f7fb;
}

.block-container {
    padding-top: 1rem;
    padding-left: 1rem;
    padding-right: 1rem;
}

/* Header */
.report-header {
    background: linear-gradient(135deg, #063b66, #0876b9);
    color: white;
    padding: 18px;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 15px;
    box-shadow: 0 4px 12px rgba(0,0,0,.15);
}

.report-header h1 {
    margin: 0;
    font-size: 28px;
}

/* KPI Cards */
.kpi-container {
    display: flex;
    gap: 12px;
    margin-bottom: 15px;
}

.kpi {
    flex: 1;
    background: white;
    border-radius: 12px;
    padding: 15px;
    text-align: center;
    border: 1px solid #d9e2ec;
    box-shadow: 0 2px 8px rgba(0,0,0,.07);
}

.kpi-title {
    font-size: 14px;
    font-weight: 600;
    color: #52616b;
}

.kpi-value {
    font-size: 24px;
    font-weight: 800;
    margin-top: 5px;
    color: #063b66;
}

/* Table */
.dataframe {
    font-size: 13px !important;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# HEADER
# =========================================================
st.markdown("""
<div class="report-header">
    <h1>📊 RANGE-WISE RECOVERY COMPARISON REPORT</h1>
</div>
""", unsafe_allow_html=True)


# =========================================================
# FILTERS
# =========================================================
c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 1])

with c1:
    from_month = st.selectbox(
        "From Month",
        ["Jul-25", "Aug-25", "Sep-25", "Oct-25"]
    )

with c2:
    to_month = st.selectbox(
        "To Month",
        ["Aug-25", "Sep-25", "Oct-25", "Nov-25"]
    )

with c3:
    area = st.selectbox(
        "Area",
        ["All", "Chakwal", "Talagang", "Kallar Kahar"]
    )

with c4:
    st.write("")
    st.write("")
    generate = st.button(
        "📊 Generate Report",
        use_container_width=True
    )


# =========================================================
# SAMPLE BRANCH DATA
# =========================================================
branches = [
    ("2901", "Head Office"),
    ("2902", "Bhau"),
    ("2903", "Kallar Kahar"),
    ("2904", "Chakwal"),
    ("2905", "Lawa"),
    ("2906", "Talagang"),
    ("2907", "Choa Saidan Shah"),
    ("2908", "Gujar Khan"),
    ("2909", "Miani"),
    ("2910", "Dalelpur"),
    ("2911", "Branch 11"),
    ("2912", "Branch 12"),
    ("2913", "Branch 13"),
    ("2914", "Branch 14"),
    ("2915", "Branch 15"),
    ("2916", "Branch 16"),
    ("2917", "Branch 17"),
    ("2918", "Branch 18"),
    ("2919", "Branch 19"),
    ("2920", "Branch 20"),
    ("2921", "Branch 21"),
    ("2922", "Branch 22"),
    ("2923", "Branch 23"),
    ("2924", "Branch 24"),
    ("2925", "Branch 25")
]


# =========================================================
# CREATE SAMPLE DATA
# =========================================================
np.random.seed(10)

rows = []

for code, name in branches:

    july = np.random.randint(1, 50, 5)
    august = np.random.randint(1, 55, 5)

    rows.append({
        "Branch Code": code,
        "Branch Name": name,

        "Jul 1-5": july[0],
        "Jul 6-10": july[1],
        "Jul 11-15": july[2],
        "Jul 16-25": july[3],
        "Jul >25": july[4],

        "Aug 1-5": august[0],
        "Aug 6-10": august[1],
        "Aug 11-15": august[2],
        "Aug 16-25": august[3],
        "Aug >25": august[4],
    })


df = pd.DataFrame(rows)


# =========================================================
# TOTALS
# =========================================================
df["Jul Total"] = (
    df["Jul 1-5"] +
    df["Jul 6-10"] +
    df["Jul 11-15"] +
    df["Jul 16-25"] +
    df["Jul >25"]
)

df["Aug Total"] = (
    df["Aug 1-5"] +
    df["Aug 6-10"] +
    df["Aug 11-15"] +
    df["Aug 16-25"] +
    df["Aug >25"]
)

# Differences
df["Diff 1-5"] = df["Aug 1-5"] - df["Jul 1-5"]
df["Diff 6-10"] = df["Aug 6-10"] - df["Jul 6-10"]
df["Diff 11-15"] = df["Aug 11-15"] - df["Jul 11-15"]
df["Diff 16-25"] = df["Aug 16-25"] - df["Jul 16-25"]
df["Diff >25"] = df["Aug >25"] - df["Jul >25"]

df["Total Difference"] = df["Aug Total"] - df["Jul Total"]

df["% Difference"] = np.where(
    df["Jul Total"] == 0,
    0,
    (df["Total Difference"] / df["Jul Total"]) * 100
)


# =========================================================
# KPI VALUES
# =========================================================
july_total = df["Jul Total"].sum()
aug_total = df["Aug Total"].sum()
difference = aug_total - july_total

growth = (
    (difference / july_total) * 100
    if july_total != 0 else 0
)


# =========================================================
# KPI CARDS
# =========================================================
st.markdown(f"""
<div class="kpi-container">

<div class="kpi">
<div class="kpi-title">🏢 Total Branches</div>
<div class="kpi-value">{len(df)}</div>
</div>

<div class="kpi">
<div class="kpi-title">📅 Total Recovery ({from_month})</div>
<div class="kpi-value">{july_total:,}</div>
</div>

<div class="kpi">
<div class="kpi-title">📅 Total Recovery ({to_month})</div>
<div class="kpi-value">{aug_total:,}</div>
</div>

<div class="kpi">
<div class="kpi-title">↕ Total Difference</div>
<div class="kpi-value">{difference:,}</div>
</div>

<div class="kpi">
<div class="kpi-title">📈 Overall Growth</div>
<div class="kpi-value">{growth:.2f}%</div>
</div>

</div>
""", unsafe_allow_html=True)


# =========================================================
# CREATE DISPLAY TABLE
# =========================================================

display_df = pd.DataFrame()

display_df["Sr."] = range(1, len(df) + 1)
display_df["Branch Code"] = df["Branch Code"]
display_df["Branch Name"] = df["Branch Name"]


# July
display_df[f"{from_month} | 1-5"] = df["Jul 1-5"]
display_df[f"{from_month} | 6-10"] = df["Jul 6-10"]
display_df[f"{from_month} | 11-15"] = df["Jul 11-15"]
display_df[f"{from_month} | 16-25"] = df["Jul 16-25"]
display_df[f"{from_month} | >25"] = df["Jul >25"]
display_df[f"{from_month} | Total"] = df["Jul Total"]


# August
display_df[f"{to_month} | 1-5"] = df["Aug 1-5"]
display_df[f"{to_month} | 6-10"] = df["Aug 6-10"]
display_df[f"{to_month} | 11-15"] = df["Aug 11-15"]
display_df[f"{to_month} | 16-25"] = df["Aug 16-25"]
display_df[f"{to_month} | >25"] = df["Aug >25"]
display_df[f"{to_month} | Total"] = df["Aug Total"]


# Difference
display_df["Diff | 1-5"] = df["Diff 1-5"]
display_df["Diff | 6-10"] = df["Diff 6-10"]
display_df["Diff | 11-15"] = df["Diff 11-15"]
display_df["Diff | 16-25"] = df["Diff 16-25"]
display_df["Diff | >25"] = df["Diff >25"]
display_df["Diff | Total"] = df["Total Difference"]
display_df["% Diff"] = df["% Difference"].round(2)


# =========================================================
# GRAND TOTAL ROW
# =========================================================
total_row = {}

for col in display_df.columns:

    if col in ["Sr.", "Branch Code"]:
        total_row[col] = ""

    elif col == "Branch Name":
        total_row[col] = "GRAND TOTAL"

    elif col == "% Diff":
        total_row[col] = round(
            (difference / july_total) * 100
            if july_total else 0,
            2
        )

    else:
        total_row[col] = display_df[col].sum()


display_df = pd.concat(
    [
        display_df,
        pd.DataFrame([total_row])
    ],
    ignore_index=True
)


# =========================================================
# FORMAT TABLE
# =========================================================
def highlight_total(row):

    if row["Branch Name"] == "GRAND TOTAL":
        return [
            "background-color: #063b66; color: white; font-weight: bold;"
            for _ in row
        ]

    return [""] * len(row)


styled = (
    display_df.style
    .apply(highlight_total, axis=1)
    .format({
        "% Diff": "{:.2f}%"
    })
)


# =========================================================
# SHOW TABLE
# =========================================================
st.subheader("📋 Branch-wise Range Comparison")

st.dataframe(
    styled,
    use_container_width=True,
    height=720,
    hide_index=True
)


# =========================================================
# RANGE EXPLANATION
# =========================================================
st.markdown("---")

c1, c2 = st.columns(2)

with c1:

    st.markdown("### 📌 Recovery Range")

    st.markdown("""
    | Range | Meaning |
    |---|---|
    | **1 – 5** | 1 to 5 Days |
    | **6 – 10** | 6 to 10 Days |
    | **11 – 15** | 11 to 15 Days |
    | **16 – 25** | 16 to 25 Days |
    | **>25** | More than 25 Days |
    """)


with c2:

    st.markdown("### 📊 Comparison Logic")

    st.info("""
    **Difference = August − July**

    **% Difference = (August − July) ÷ July × 100**

    इस तरह हर Branch की range-wise performance और
    overall increase/decrease एक ही table में दिखाई देगी।
    """)


# =========================================================
# DOWNLOAD EXCEL
# =========================================================
from io import BytesIO

output = BytesIO()

with pd.ExcelWriter(output, engine="openpyxl") as writer:
    display_df.to_excel(
        writer,
        index=False,
        sheet_name="Range Wise Comparison"
    )

output.seek(0)

st.download_button(
    "⬇️ Download Excel Report",
    data=output,
    file_name="Range_Wise_Recovery_Comparison.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)
