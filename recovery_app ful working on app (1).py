import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter


# =========================================================
# RANGE-WISE RECOVERY COMPARISON
# =========================================================

st.markdown("""
<style>
.range-title {
    background: linear-gradient(135deg,#063b66,#0876b9);
    color:white;
    padding:18px;
    border-radius:12px;
    text-align:center;
    font-size:26px;
    font-weight:800;
    margin-bottom:18px;
}

.info-box {
    background:#f5f9ff;
    border:1px solid #cbdff5;
    border-radius:10px;
    padding:12px;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="range-title">📊 RANGE-WISE RECOVERY COMPARISON REPORT</div>',
    unsafe_allow_html=True
)


# =========================================================
# EXCEL UPLOAD
# =========================================================

st.subheader("📤 Upload Recovery Excel")

uploaded_file = st.file_uploader(
    "Upload your Recovery Excel File",
    type=["xlsx", "xls"],
    key="range_recovery_upload"
)

if uploaded_file is None:

    st.info(
        "Please upload your Recovery Excel file. "
        "The report will be generated automatically after upload."
    )

    st.stop()


# =========================================================
# READ EXCEL
# =========================================================

try:

    excel_file = pd.ExcelFile(uploaded_file)

    sheet_name = st.selectbox(
        "Select Sheet",
        excel_file.sheet_names
    )

    raw_df = pd.read_excel(
        uploaded_file,
        sheet_name=sheet_name
    )

except Exception as e:

    st.error(f"Excel file read نہیں ہو سکی: {e}")
    st.stop()


# =========================================================
# CLEAN COLUMN NAMES
# =========================================================

raw_df.columns = (
    raw_df.columns
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("-", "_")
)


# =========================================================
# FIND COLUMNS AUTOMATICALLY
# =========================================================

def find_column(df, possible_names):

    for col in possible_names:

        if col in df.columns:
            return col

    return None


# ---------------------------------------------------------
# AREA COLUMN
# ---------------------------------------------------------

area_col = find_column(
    raw_df,
    [
        "area",
        "area_name",
        "region",
        "zone"
    ]
)


# ---------------------------------------------------------
# BRANCH NAME COLUMN
# ---------------------------------------------------------

branch_name_col = find_column(
    raw_df,
    [
        "branch_name",
        "branchname",
        "branch_title",
        "branch"
    ]
)


# ---------------------------------------------------------
# DATE COLUMN
# ---------------------------------------------------------

date_col = find_column(
    raw_df,
    [
        "recovery_date",
        "recoverydate",
        "date",
        "recovery_date_",
        "receipt_date",
        "transaction_date"
    ]
)


# =========================================================
# MANUAL COLUMN SELECTION
# =========================================================

st.subheader("🔧 Column Mapping")

col1, col2, col3 = st.columns(3)


# ---------------------------------------------------------
# AREA
# ---------------------------------------------------------

with col1:

    if area_col is None:

        area_col = st.selectbox(
            "Area Column",
            ["None"] + list(raw_df.columns),
            key="area_mapping"
        )

        if area_col == "None":
            area_col = None

    else:

        st.success(
            f"Area: {area_col}"
        )


# ---------------------------------------------------------
# BRANCH NAME
# ---------------------------------------------------------

with col2:

    if branch_name_col is None:

        branch_name_col = st.selectbox(
            "Branch Name Column",
            ["None"] + list(raw_df.columns),
            key="branch_name_mapping"
        )

        if branch_name_col == "None":
            branch_name_col = None

    else:

        st.success(
            f"Branch Name: {branch_name_col}"
        )


# ---------------------------------------------------------
# RECOVERY DATE
# ---------------------------------------------------------

with col3:

    if date_col is None:

        date_col = st.selectbox(
            "Recovery Date Column",
            ["None"] + list(raw_df.columns),
            key="date_mapping"
        )

        if date_col == "None":
            date_col = None

    else:

        st.success(
            f"Recovery Date: {date_col}"
        )


# =========================================================
# REQUIRED COLUMN CHECK
# =========================================================

if date_col is None:

    st.error(
        "Recovery Date column نہیں ملی۔ "
        "براہ کرم اوپر سے Recovery Date والی column select کریں۔"
    )

    st.stop()


if area_col is None:

    st.error(
        "Area column نہیں ملی۔ "
        "براہ کرم Area والی column select کریں۔"
    )

    st.stop()


if branch_name_col is None:

    st.error(
        "Branch Name column نہیں ملی۔ "
        "براہ کرم Branch Name والی column select کریں۔"
    )

    st.stop()


# =========================================================
# DATE CONVERSION
# =========================================================

df = raw_df.copy()

df["_recovery_date"] = pd.to_datetime(
    df[date_col],
    errors="coerce",
    dayfirst=True
)

invalid_dates = df["_recovery_date"].isna().sum()

if invalid_dates > 0:

    st.warning(
        f"{invalid_dates} rows میں valid recovery date نہیں ملی۔ "
        "یہ rows report میں شامل نہیں ہوں گی۔"
    )

df = df[
    df["_recovery_date"].notna()
].copy()


if len(df) == 0:

    st.error(
        "کوئی valid Recovery Date نہیں ملی۔"
    )

    st.stop()


# =========================================================
# AREA INFORMATION
# =========================================================

df["_area"] = (
    df[area_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


# =========================================================
# BRANCH INFORMATION
# =========================================================

df["_branch_name"] = (
    df[branch_name_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


# =========================================================
# REMOVE EMPTY AREA / BRANCH
# =========================================================

df = df[
    (df["_area"] != "") &
    (df["_branch_name"] != "")
].copy()


if df.empty:

    st.error(
        "Area یا Branch Name میں کوئی valid data نہیں ملا۔"
    )

    st.stop()


# =========================================================
# MONTH
# =========================================================

df["_month"] = (
    df["_recovery_date"]
    .dt.to_period("M")
)


available_months = sorted(
    df["_month"]
    .dropna()
    .unique()
)


if len(available_months) == 0:

    st.error(
        "کوئی month data نہیں ملا۔"
    )

    st.stop()


month_names = [
    x.strftime("%b-%y")
    for x in available_months
]


# =========================================================
# MONTH SELECTION
# =========================================================

m1, m2 = st.columns(2)


with m1:

    from_month_label = st.selectbox(
        "From Month",
        month_names,
        index=max(0, len(month_names) - 2)
    )


with m2:

    to_month_label = st.selectbox(
        "To Month",
        month_names,
        index=len(month_names) - 1
    )


# =========================================================
# CONVERT MONTH LABEL TO PERIOD
# =========================================================

try:

    from_month = pd.Period(
        pd.to_datetime(
            "01-" + from_month_label,
            format="%d-%b-%y"
        ),
        freq="M"
    )

    to_month = pd.Period(
        pd.to_datetime(
            "01-" + to_month_label,
            format="%d-%b-%y"
        ),
        freq="M"
    )

except Exception as e:

    st.error(
        f"Month selection error: {e}"
    )

    st.stop()


# =========================================================
# OPTIONAL AREA FILTER
# =========================================================

area_filter_values = [
    "All"
] + sorted(
    df["_area"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


selected_area = st.selectbox(
    "📍 Area Filter",
    area_filter_values
)


if selected_area != "All":

    df = df[
        df["_area"] == selected_area
    ].copy()


# =========================================================
# RANGE FUNCTION
# =========================================================

def get_range(day):

    if 1 <= day <= 5:
        return "1-5"

    elif 6 <= day <= 10:
        return "6-10"

    elif 11 <= day <= 15:
        return "11-15"

    elif 16 <= day <= 25:
        return "16-25"

    else:
        return ">25"


df["_day"] = (
    df["_recovery_date"]
    .dt.day
)

df["_range"] = (
    df["_day"]
    .apply(get_range)
)


# =========================================================
# REPORT FUNCTION
# =========================================================

def create_month_report(data, month_period):

    temp = data[
        data["_month"] == month_period
    ].copy()


    ranges = [
        "1-5",
        "6-10",
        "11-15",
        "16-25",
        ">25"
    ]


    if temp.empty:

        return pd.DataFrame()


    result = []


    # -----------------------------------------------------
    # AREA + BRANCH LIST
    # -----------------------------------------------------

    branch_list = (
        temp[
            [
                "_area",
                "_branch_name"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "_area",
                "_branch_name"
            ]
        )
    )


    # -----------------------------------------------------
    # LOOP AREA + BRANCH
    # -----------------------------------------------------

    for _, branch in branch_list.iterrows():

        area = branch["_area"]

        name = branch["_branch_name"]


        branch_data = temp[
            (temp["_area"] == area) &
            (temp["_branch_name"] == name)
        ]


        row = {

            "Area": area,

            "Branch Name": name

        }


        total = 0


        for r in ranges:

            count = (
                branch_data["_range"] == r
            ).sum()


            row[r] = int(count)


            total += count


        row["Total"] = int(total)


        result.append(row)


    return pd.DataFrame(result)


# =========================================================
# CREATE REPORTS
# =========================================================

month1_df = create_month_report(
    df,
    from_month
)


month2_df = create_month_report(
    df,
    to_month
)


# =========================================================
# EMPTY CHECK
# =========================================================

if month1_df.empty:

    st.warning(
        f"{from_month_label} میں کوئی recovery record نہیں ملا۔"
    )


if month2_df.empty:

    st.warning(
        f"{to_month_label} میں کوئی recovery record نہیں ملا۔"
    )


# =========================================================
# MERGE AREAS + BRANCHES
# =========================================================

all_branches = pd.concat(
    [
        month1_df[
            [
                "Area",
                "Branch Name"
            ]
        ]
        if not month1_df.empty
        else pd.DataFrame(),

        month2_df[
            [
                "Area",
                "Branch Name"
            ]
        ]
        if not month2_df.empty
        else pd.DataFrame()
    ],
    ignore_index=True
).drop_duplicates()


if all_branches.empty:

    st.error(
        "Area / Branch data نہیں ملا۔"
    )

    st.stop()


# =========================================================
# RANGES
# =========================================================

ranges = [
    "1-5",
    "6-10",
    "11-15",
    "16-25",
    ">25"
]


# =========================================================
# MONTH 1
# =========================================================

if not month1_df.empty:

    month1_df = month1_df.rename(
        columns={
            r: f"{from_month_label} | {r}"
            for r in ranges
        }
        |
        {
            "Total":
            f"{from_month_label} | Total"
        }
    )


else:

    month1_df = all_branches.copy()


    for r in ranges:

        month1_df[
            f"{from_month_label} | {r}"
        ] = 0


    month1_df[
        f"{from_month_label} | Total"
    ] = 0


# =========================================================
# MONTH 2
# =========================================================

if not month2_df.empty:

    month2_df = month2_df.rename(
        columns={
            r: f"{to_month_label} | {r}"
            for r in ranges
        }
        |
        {
            "Total":
            f"{to_month_label} | Total"
        }
    )


else:

    month2_df = all_branches.copy()


    for r in ranges:

        month2_df[
            f"{to_month_label} | {r}"
        ] = 0


    month2_df[
        f"{to_month_label} | Total"
    ] = 0


# =========================================================
# MERGE MONTHS
# =========================================================

comparison = all_branches.merge(
    month1_df,
    on=[
        "Area",
        "Branch Name"
    ],
    how="left"
)


comparison = comparison.merge(
    month2_df,
    on=[
        "Area",
        "Branch Name"
    ],
    how="left"
)


comparison = comparison.fillna(0)


# =========================================================
# DIFFERENCE COLUMNS
# =========================================================

for r in ranges:

    comparison[
        f"Diff | {r}"
    ] = (
        comparison[
            f"{to_month_label} | {r}"
        ]
        -
        comparison[
            f"{from_month_label} | {r}"
        ]
    )


# ---------------------------------------------------------
# TOTAL DIFFERENCE
# ---------------------------------------------------------

comparison[
    "Diff | Total"
] = (
    comparison[
        f"{to_month_label} | Total"
    ]
    -
    comparison[
        f"{from_month_label} | Total"
    ]
)


# ---------------------------------------------------------
# PERCENTAGE DIFFERENCE
# ---------------------------------------------------------

comparison[
    "% Diff"
] = np.where(

    comparison[
        f"{from_month_label} | Total"
    ] == 0,

    0,

    (
        comparison["Diff | Total"]
        /
        comparison[
            f"{from_month_label} | Total"
        ]
    ) * 100
)


# =========================================================
# SERIAL NUMBER
# =========================================================

comparison.insert(
    0,
    "Sr.",
    range(
        1,
        len(comparison) + 1
    )
)


# =========================================================
# GRAND TOTAL
# =========================================================

grand_total = {}


for col in comparison.columns:

    if col == "Sr.":

        grand_total[col] = ""


    elif col == "Area":

        grand_total[col] = ""


    elif col == "Branch Name":

        grand_total[col] = "GRAND TOTAL"


    elif col == "% Diff":

        old_total = comparison[
            f"{from_month_label} | Total"
        ].sum()


        new_total = comparison[
            f"{to_month_label} | Total"
        ].sum()


        grand_total[col] = (

            (
                (new_total - old_total)
                /
                old_total
            ) * 100

            if old_total != 0

            else 0
        )


    else:

        grand_total[col] = (
            comparison[col].sum()
        )


# =========================================================
# FINAL DISPLAY TABLE
# =========================================================

final_table = pd.concat(
    [
        comparison,

        pd.DataFrame(
            [grand_total]
        )
    ],
    ignore_index=True
)


# =========================================================
# KPI
# =========================================================

month1_total = comparison[
    f"{from_month_label} | Total"
].sum()


month2_total = comparison[
    f"{to_month_label} | Total"
].sum()


total_difference = (
    month2_total -
    month1_total
)


overall_growth = (

    (
        total_difference
        /
        month1_total
    ) * 100

    if month1_total != 0

    else 0
)


# =========================================================
# KPI CARDS
# =========================================================

k1, k2, k3, k4, k5 = st.columns(5)


with k1:

    st.metric(
        "🏢 Total Branches",
        len(comparison)
    )


with k2:

    st.metric(
        f"📅 {from_month_label}",
        f"{int(month1_total):,}"
    )


with k3:

    st.metric(
        f"📅 {to_month_label}",
        f"{int(month2_total):,}"
    )


with k4:

    st.metric(
        "↕ Difference",
        f"{int(total_difference):,}"
    )


with k5:

    st.metric(
        "📈 Growth",
        f"{overall_growth:.2f}%"
    )


# =========================================================
# MAIN TABLE
# =========================================================

st.subheader(
    "📋 Area-wise / Branch-wise Range Comparison"
)


try:

    # -----------------------------------------------------
    # Convert column names to strings
    # -----------------------------------------------------

    final_table.columns = (
        final_table.columns
        .astype(str)
    )


    # -----------------------------------------------------
    # Safe object columns
    # -----------------------------------------------------

    for col in final_table.columns:

        if final_table[col].dtype == "object":

            final_table[col] = (
                final_table[col]
                .fillna("")
                .astype(str)
            )


    st.dataframe(
        final_table,
        use_container_width=True,
        height=700
    )


except Exception:

    st.error(
        "Table display error occurred."
    )


    st.table(
        final_table
    )


# =========================================================
# RANGE EXPLANATION
# =========================================================

st.markdown("---")


c1, c2 = st.columns(2)


with c1:

    st.markdown(
        "### 📌 Recovery Ranges"
    )


    st.markdown("""
    **1–5** → Day 1 to Day 5  

    **6–10** → Day 6 to Day 10  

    **11–15** → Day 11 to Day 15  

    **16–25** → Day 16 to Day 25  

    **>25** → More than 25 Days
    """)


with c2:

    st.markdown(
        "### 📊 Comparison Formula"
    )


    st.info(
        f"""
        **Difference = {to_month_label} − {from_month_label}**

        **Growth % = Difference ÷ {from_month_label} × 100**

        ہر Area اور Branch کی recovery range-wise compare کی جا رہی ہے۔
        """
    )


# =========================================================
# DOWNLOAD EXCEL
# GREEN / RED DIFFERENCE REPORT
# =========================================================

# ---------------------------------------------------------
# CREATE WORKBOOK
# ---------------------------------------------------------

wb = Workbook()


ws = wb.active

ws.title = (
    "Range Wise Comparison"
)

ws.sheet_state = "visible"


# =========================================================
# WRITE HEADERS
# =========================================================

headers = list(
    final_table.columns
)


for col_num, header in enumerate(
    headers,
    start=1
):

    cell = ws.cell(
        row=1,
        column=col_num,
        value=header
    )


    cell.font = Font(
        bold=True,
        color="FFFFFF"
    )


    cell.fill = PatternFill(
        fill_type="solid",
        fgColor="063B66"
    )


    cell.alignment = Alignment(
        horizontal="center",
        vertical="center"
    )


# =========================================================
# WRITE DATA
# =========================================================

for row_num, row_data in enumerate(

    final_table.itertuples(
        index=False
    ),

    start=2
):

    for col_num, value in enumerate(

        row_data,

        start=1

    ):

        cell = ws.cell(
            row=row_num,
            column=col_num,
            value=value
        )


        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )


# =========================================================
# FIND DIFFERENCE COLUMNS
# =========================================================

difference_columns = []


for col_num in range(
    1,
    ws.max_column + 1
):

    header = ws.cell(
        row=1,
        column=col_num
    ).value


    if header:

        header_text = str(
            header
        )


        if (
            header_text.startswith(
                "Diff |"
            )
            or
            header_text == "% Diff"
        ):

            difference_columns.append(
                col_num
            )


# =========================================================
# GREEN / RED COLORS
# =========================================================

green_fill = PatternFill(
    fill_type="solid",
    fgColor="C6EFCE"
)


green_font = Font(
    color="006100",
    bold=True
)


red_fill = PatternFill(
    fill_type="solid",
    fgColor="FFC7CE"
)


red_font = Font(
    color="9C0006",
    bold=True
)


# =========================================================
# CONDITIONAL FORMATTING
# =========================================================

grand_total_row = ws.max_row

first_data_row = 2

last_data_row = (
    grand_total_row - 1
)


if last_data_row >= first_data_row:

    for col_num in difference_columns:

        col_letter = (
            get_column_letter(
                col_num
            )
        )


        data_range = (
            f"{col_letter}"
            f"{first_data_row}:"
            f"{col_letter}"
            f"{last_data_row}"
        )


        # -------------------------------------------------
        # POSITIVE = GREEN
        # -------------------------------------------------

        ws.conditional_formatting.add(

            data_range,

            CellIsRule(
                operator="greaterThan",
                formula=["0"],
                fill=green_fill,
                font=green_font
            )

        )


        # -------------------------------------------------
        # NEGATIVE = RED
        # -------------------------------------------------

        ws.conditional_formatting.add(

            data_range,

            CellIsRule(
                operator="lessThan",
                formula=["0"],
                fill=red_fill,
                font=red_font
            )

        )


# =========================================================
# GRAND TOTAL ROW
# =========================================================

grand_fill = PatternFill(
    fill_type="solid",
    fgColor="063B66"
)


grand_font = Font(
    bold=True,
    color="FFFFFF"
)


for col_num in range(
    1,
    ws.max_column + 1
):

    cell = ws.cell(
        row=grand_total_row,
        column=col_num
    )


    cell.fill = grand_fill

    cell.font = grand_font


    cell.alignment = Alignment(
        horizontal="center",
        vertical="center"
    )


# =========================================================
# % DIFFERENCE FORMAT
# =========================================================

for col_num in range(
    1,
    ws.max_column + 1
):

    header = ws.cell(
        row=1,
        column=col_num
    ).value


    if header == "% Diff":

        for row_num in range(
            2,
            ws.max_row + 1
        ):

            ws.cell(
                row=row_num,
                column=col_num
            ).number_format = (
                '0.00"%"'
            )


# =========================================================
# BORDERS
# =========================================================

thin_border = Border(

    left=Side(
        style="thin",
        color="D9E1F2"
    ),

    right=Side(
        style="thin",
        color="D9E1F2"
    ),

    top=Side(
        style="thin",
        color="D9E1F2"
    ),

    bottom=Side(
        style="thin",
        color="D9E1F2"
    )
)


for row in ws.iter_rows():

    for cell in row:

        cell.border = thin_border


# =========================================================
# COLUMN WIDTH
# =========================================================

for col_num in range(
    1,
    ws.max_column + 1
):

    max_length = 0


    for row_num in range(
        1,
        ws.max_row + 1
    ):

        value = ws.cell(
            row=row_num,
            column=col_num
        ).value


        if value is not None:

            max_length = max(
                max_length,
                len(str(value))
            )


    header = ws.cell(
        row=1,
        column=col_num
    ).value


    if header == "Branch Name":

        ws.column_dimensions[
            get_column_letter(
                col_num
            )
        ].width = 22


    elif header == "Area":

        ws.column_dimensions[
            get_column_letter(
                col_num
            )
        ].width = 20


    else:

        ws.column_dimensions[
            get_column_letter(
                col_num
            )
        ].width = min(
            max(
                max_length + 3,
                10
            ),
            18
        )


# =========================================================
# ROW HEIGHT
# =========================================================

ws.row_dimensions[1].height = 30


for row_num in range(
    2,
    ws.max_row + 1
):

    ws.row_dimensions[
        row_num
    ].height = 22


# =========================================================
# FREEZE PANES
# =========================================================

ws.freeze_panes = "C2"


# =========================================================
# AUTO FILTER
# =========================================================

ws.auto_filter.ref = (
    ws.dimensions
)


# =========================================================
# SAVE TO MEMORY
# =========================================================

excel_output = BytesIO()


wb.save(
    excel_output
)


excel_output.seek(0)


# =========================================================
# DOWNLOAD BUTTON
# =========================================================

st.download_button(

    label="⬇️ Download Range-Wise Excel Report",

    data=excel_output.getvalue(),

    file_name=(
        "Range_Wise_Recovery_Comparison.xlsx"
    ),

    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),

    use_container_width=True

)
