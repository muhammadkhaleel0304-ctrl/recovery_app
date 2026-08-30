import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="MDP Comparison",
    page_icon="📊",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.mdp-title {
    background: linear-gradient(135deg,#063b66,#0876b9);
    color:white;
    padding:18px;
    border-radius:12px;
    text-align:center;
    font-size:27px;
    font-weight:800;
    margin-bottom:20px;
}

</style>
""", unsafe_allow_html=True)


st.markdown(
    '<div class="mdp-title">📊 MDP MONTH-WISE COMPARISON REPORT</div>',
    unsafe_allow_html=True
)


# =========================================================
# UPLOAD
# =========================================================

st.subheader("📤 Upload MDP Excel")

uploaded_file = st.file_uploader(
    "Upload MDP Excel File",
    type=["xlsx", "xls"],
    key="mdp_comparison_upload"
)

if uploaded_file is None:

    st.info(
        "Please upload your MDP Excel file."
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

    st.error(
        f"Excel file read نہیں ہو سکی: {e}"
    )

    st.stop()


# =========================================================
# CLEAN COLUMN NAMES
# =========================================================

raw_df.columns = (
    raw_df.columns
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(" ", "_", regex=False)
    .str.replace("-", "_", regex=False)
)


# =========================================================
# FIND COLUMN
# =========================================================

def find_column(df, possible_names):

    for col in possible_names:

        if col in df.columns:
            return col

    return None


# =========================================================
# AUTO DETECT COLUMNS
# =========================================================

area_col = find_column(
    raw_df,
    [
        "area",
        "area_name",
        "region",
        "zone"
    ]
)


branch_col = find_column(
    raw_df,
    [
        "branch_name",
        "branchname",
        "branch_title",
        "branch"
    ]
)


date_col = find_column(
    raw_df,
    [
        "date",
        "mdp_date",
        "recovery_date",
        "transaction_date",
        "disbursement_date"
    ]
)


amount_col = find_column(
    raw_df,
    [
        "amount",
        "mdp_amount",
        "total_amount",
        "given_amount",
        "paid_amount",
        "recovery_amount"
    ]
)


receipt_col = find_column(
    raw_df,
    [
        "receipts",
        "receipt",
        "receipt_count",
        "receipt_no",
        "slips",
        "slip_count",
        "total_receipts"
    ]
)


# =========================================================
# COLUMN MAPPING
# =========================================================

st.subheader("🔧 Column Mapping")

c1, c2, c3 = st.columns(3)


# ---------------------------------------------------------
# AREA
# ---------------------------------------------------------

with c1:

    if area_col is None:

        area_col = st.selectbox(
            "Area Column",
            ["None"] + list(raw_df.columns),
            key="mdp_area"
        )

        if area_col == "None":
            area_col = None

    else:

        st.success(
            f"Area: {area_col}"
        )


# ---------------------------------------------------------
# BRANCH
# ---------------------------------------------------------

with c2:

    if branch_col is None:

        branch_col = st.selectbox(
            "Branch Name Column",
            ["None"] + list(raw_df.columns),
            key="mdp_branch"
        )

        if branch_col == "None":
            branch_col = None

    else:

        st.success(
            f"Branch: {branch_col}"
        )


# ---------------------------------------------------------
# DATE
# ---------------------------------------------------------

with c3:

    if date_col is None:

        date_col = st.selectbox(
            "Month / Date Column",
            ["None"] + list(raw_df.columns),
            key="mdp_date"
        )

        if date_col == "None":
            date_col = None

    else:

        st.success(
            f"Date: {date_col}"
        )


c4, c5 = st.columns(2)


# ---------------------------------------------------------
# AMOUNT
# ---------------------------------------------------------

with c4:

    if amount_col is None:

        amount_col = st.selectbox(
            "Amount Column",
            ["None"] + list(raw_df.columns),
            key="mdp_amount"
        )

        if amount_col == "None":
            amount_col = None

    else:

        st.success(
            f"Amount: {amount_col}"
        )


# ---------------------------------------------------------
# RECEIPTS
# ---------------------------------------------------------

with c5:

    if receipt_col is None:

        receipt_col = st.selectbox(
            "Receipts Column",
            ["None"] + list(raw_df.columns),
            key="mdp_receipts"
        )

        if receipt_col == "None":
            receipt_col = None

    else:

        st.success(
            f"Receipts: {receipt_col}"
        )


# =========================================================
# REQUIRED CHECK
# =========================================================

missing = []

if area_col is None:
    missing.append("Area")

if branch_col is None:
    missing.append("Branch Name")

if date_col is None:
    missing.append("Date / Month")

if amount_col is None:
    missing.append("Amount")

if receipt_col is None:
    missing.append("Receipts")


if missing:

    st.error(
        "یہ columns ضروری ہیں: "
        + ", ".join(missing)
    )

    st.stop()


# =========================================================
# PREPARE DATA
# =========================================================

df = raw_df.copy()


df["_area"] = (
    df[area_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


df["_branch"] = (
    df[branch_col]
    .fillna("")
    .astype(str)
    .str.strip()
)


# =========================================================
# DATE
# =========================================================

df["_date"] = pd.to_datetime(
    df[date_col],
    errors="coerce",
    dayfirst=True
)


invalid_dates = df["_date"].isna().sum()


if invalid_dates:

    st.warning(
        f"{invalid_dates} rows میں valid date نہیں ملی۔ "
        "یہ rows شامل نہیں ہوں گی۔"
    )


df = df[
    df["_date"].notna()
].copy()


if df.empty:

    st.error(
        "کوئی valid date نہیں ملی۔"
    )

    st.stop()


# =========================================================
# AMOUNT
# =========================================================

df["_amount"] = pd.to_numeric(
    df[amount_col],
    errors="coerce"
).fillna(0)


# =========================================================
# RECEIPTS
# =========================================================

df["_receipts"] = pd.to_numeric(
    df[receipt_col],
    errors="coerce"
)


# If receipt column is numeric
# use numeric values.
# Otherwise count rows.

if df["_receipts"].isna().all():

    df["_receipts"] = 1

else:

    df["_receipts"] = (
        df["_receipts"]
        .fillna(0)
    )


# =========================================================
# MONTH
# =========================================================

df["_month"] = (
    df["_date"]
    .dt.to_period("M")
)


available_months = sorted(
    df["_month"]
    .unique()
)


if not available_months:

    st.error(
        "کوئی month data نہیں ملا۔"
    )

    st.stop()


# =========================================================
# MONTH NAMES
# =========================================================

month_names = [
    x.strftime("%b-%y")
    for x in available_months
]


st.success(
    f"{len(month_names)} months found: "
    + ", ".join(month_names)
)


# =========================================================
# MONTH REPORT FUNCTION
# =========================================================

def create_month_report(data, month_period):

    temp = data[
        data["_month"] == month_period
    ].copy()


    if temp.empty:

        return pd.DataFrame()


    result = []


    grouped = (
        temp
        .groupby(
            [
                "_area",
                "_branch"
            ],
            dropna=False
        )
        .agg(
            Amount=(
                "_amount",
                "sum"
            ),

            Receipts=(
                "_receipts",
                "sum"
            )
        )
        .reset_index()
    )


    grouped = grouped.sort_values(
        [
            "_area",
            "_branch"
        ]
    )


    for _, row in grouped.iterrows():

        result.append({

            "Area": row["_area"],

            "Branch Name": row["_branch"],

            "Amount": float(
                row["Amount"]
            ),

            "Receipts": float(
                row["Receipts"]
            )

        })


    return pd.DataFrame(result)


# =========================================================
# CREATE ALL MONTH REPORTS
# =========================================================

monthly_reports = {}


for month_period in available_months:

    monthly_reports[
        month_period
    ] = create_month_report(
        df,
        month_period
    )


# =========================================================
# ALL BRANCHES
# =========================================================

all_branches = pd.concat(

    [
        report[
            [
                "Area",
                "Branch Name"
            ]
        ]

        for report in monthly_reports.values()

        if not report.empty
    ],

    ignore_index=True

).drop_duplicates()


if all_branches.empty:

    st.error(
        "Area / Branch data نہیں ملا۔"
    )

    st.stop()


all_branches = (
    all_branches
    .sort_values(
        [
            "Area",
            "Branch Name"
        ]
    )
    .reset_index(drop=True)
)


# =========================================================
# BUILD DISPLAY TABLE
# =========================================================

display_df = all_branches.copy()


# ---------------------------------------------------------
# Keep due values in session
# ---------------------------------------------------------

if "mdp_due_values" not in st.session_state:

    st.session_state.mdp_due_values = {}


# =========================================================
# ADD MONTH COLUMNS
# =========================================================

for month_period in available_months:

    label = month_period.strftime(
        "%b-%y"
    )

    report = monthly_reports[
        month_period
    ]


    if report.empty:

        temp = all_branches.copy()

        temp[
            "Amount"
        ] = 0

        temp[
            "Receipts"
        ] = 0

    else:

        temp = all_branches.merge(

            report,

            on=[
                "Area",
                "Branch Name"
            ],

            how="left"

        )

        temp[
            "Amount"
        ] = temp[
            "Amount"
        ].fillna(0)

        temp[
            "Receipts"
        ] = temp[
            "Receipts"
        ].fillna(0)


    # -----------------------------------------------------
    # Amount
    # -----------------------------------------------------

    display_df[
        f"{label} | Amount"
    ] = temp[
        "Amount"
    ].values


    # -----------------------------------------------------
    # Receipts
    # -----------------------------------------------------

    display_df[
        f"{label} | Receipts"
    ] = temp[
        "Receipts"
    ].values


    # -----------------------------------------------------
    # Due
    # -----------------------------------------------------

    due_values = []


    for i in range(
        len(display_df)
    ):

        key = (
            str(
                display_df.iloc[i]["Area"]
            ),
            str(
                display_df.iloc[i]["Branch Name"]
            ),
            str(label)
        )


        due_values.append(
            st.session_state.mdp_due_values.get(
                key,
                0.0
            )
        )


    display_df[
        f"{label} | Due"
    ] = due_values


    # -----------------------------------------------------
    # MDP PER BOX
    # -----------------------------------------------------

    display_df[
        f"{label} | MDP Per Box"
    ] = np.where(

        display_df[
            f"{label} | Amount"
        ] != 0,

        display_df[
            f"{label} | Due"
        ]
        /
        display_df[
            f"{label} | Amount"
        ],

        0

    )


    # -----------------------------------------------------
    # NOT GIVEN
    # -----------------------------------------------------

    display_df[
        f"{label} | Not Given"
    ] = (

        display_df[
            f"{label} | Due"
        ]

        -

        display_df[
            f"{label} | Amount"
        ]

    )


# =========================================================
# SERIAL NUMBER
# =========================================================

display_df.insert(
    0,
    "Sr.",
    range(
        1,
        len(display_df) + 1
    )
)


# =========================================================
# MANUAL DUE ENTRY
# =========================================================

st.markdown("---")

st.subheader(
    "✏️ Enter Due Manually"
)

st.info(
    "صرف **Due** columns میں values enter کریں۔ "
    "MDP Per Box اور Not Given خود calculate ہوں گے۔"
)


# =========================================================
# EDITABLE DUE TABLE
# =========================================================

due_edit_df = display_df[
    [
        "Sr.",
        "Area",
        "Branch Name"
    ]
    +
    [
        f"{m.strftime('%b-%y')} | Due"
        for m in available_months
    ]
].copy()


# =========================================================
# MANUAL DUE ENTRY - STREAMLIT COMPATIBLE
# =========================================================

st.markdown("---")

st.subheader("✏️ Enter Due Manually")

st.info(
    "ہر Branch کے سامنے ہر Month کا Due enter کریں۔ "
    "MDP Per Box اور Not Given خود calculate ہوں گے۔"
)

edited_due = due_edit_df.copy()


# =========================================================
# HEADER
# =========================================================

header_cols = st.columns(
    3 + len(available_months)
)

with header_cols[0]:
    st.markdown("**Sr.**")

with header_cols[1]:
    st.markdown("**Area**")

with header_cols[2]:
    st.markdown("**Branch Name**")

for month_index, month_period in enumerate(
    available_months
):

    label = month_period.strftime("%b-%y")

    with header_cols[3 + month_index]:
        st.markdown(
            f"**{label} Due**"
        )


# =========================================================
# INPUT ROWS
# =========================================================

for i in range(len(edited_due)):

    row_cols = st.columns(
        3 + len(available_months)
    )

    # -----------------------------------------------------
    # SERIAL
    # -----------------------------------------------------

    with row_cols[0]:

        st.write(
            edited_due.loc[i, "Sr."]
        )


    # -----------------------------------------------------
    # AREA
    # -----------------------------------------------------

    with row_cols[1]:

        st.write(
            edited_due.loc[i, "Area"]
        )


    # -----------------------------------------------------
    # BRANCH
    # -----------------------------------------------------

    with row_cols[2]:

        st.write(
            edited_due.loc[i, "Branch Name"]
        )


    # -----------------------------------------------------
    # DUE INPUT
    # -----------------------------------------------------

    for month_index, month_period in enumerate(
        available_months
    ):

        label = month_period.strftime(
            "%b-%y"
        )

        due_col = (
            f"{label} | Due"
        )

        current_value = edited_due.loc[
            i,
            due_col
        ]

        if pd.isna(current_value):

            current_value = 0


        with row_cols[
            3 + month_index
        ]:

            new_value = st.number_input(
                f"Due {label}",
                min_value=0.0,
                value=float(
                    current_value
                ),
                step=1.0,
                key=f"mdp_due_{i}_{label}"
            )

            edited_due.loc[
                i,
                due_col
            ] = new_value


# =========================================================
# SAVE MANUAL DUE VALUES
# =========================================================

for i, row in edited_due.iterrows():

    area = str(
        row["Area"]
    )

    branch = str(
        row["Branch Name"]
    )


    for month_period in available_months:

        label = month_period.strftime(
            "%b-%y"
        )

        due_col = (
            f"{label} | Due"
        )

        value = row[due_col]


        if pd.isna(value):

            value = 0


        key = (
            area,
            branch,
            label
        )


        st.session_state.mdp_due_values[
            key
        ] = float(value)
# =========================================================
# REBUILD FINAL TABLE AFTER DUE ENTRY
# =========================================================

final_df = all_branches.copy()


# =========================================================
# MONTH DATA AGAIN
# =========================================================

for month_period in available_months:

    label = month_period.strftime(
        "%b-%y"
    )


    report = monthly_reports[
        month_period
    ]


    if report.empty:

        temp = all_branches.copy()

        temp["Amount"] = 0

        temp["Receipts"] = 0

    else:

        temp = all_branches.merge(

            report,

            on=[
                "Area",
                "Branch Name"
            ],

            how="left"

        )

        temp["Amount"] = (
            temp["Amount"]
            .fillna(0)
        )

        temp["Receipts"] = (
            temp["Receipts"]
            .fillna(0)
        )


    final_df[
        f"{label} | Amount"
    ] = temp[
        "Amount"
    ].values


    final_df[
        f"{label} | Receipts"
    ] = temp[
        "Receipts"
    ].values


    due_values = []


    for i in range(
        len(final_df)
    ):

        key = (

            str(
                final_df.iloc[i]["Area"]
            ),

            str(
                final_df.iloc[i]["Branch Name"]
            ),

            label

        )


        due_values.append(

            st.session_state.mdp_due_values.get(
                key,
                0.0
            )

        )


    final_df[
        f"{label} | Due"
    ] = due_values


    # -----------------------------------------------------
    # MDP PER BOX
    # -----------------------------------------------------

    final_df[
        f"{label} | MDP Per Box"
    ] = np.where(

        final_df[
            f"{label} | Amount"
        ] != 0,

        final_df[
            f"{label} | Due"
        ]
        /
        final_df[
            f"{label} | Amount"
        ],

        0

    )


    # -----------------------------------------------------
    # NOT GIVEN
    # -----------------------------------------------------

    final_df[
        f"{label} | Not Given"
    ] = (

        final_df[
            f"{label} | Due"
        ]

        -

        final_df[
            f"{label} | Amount"
        ]

    )


# =========================================================
# DIFFERENCE COLUMNS
# =========================================================

# Difference is made between consecutive months.

for i in range(
    1,
    len(available_months)
):

    previous_month = (
        available_months[i - 1]
    )

    current_month = (
        available_months[i]
    )


    previous_label = (
        previous_month.strftime(
            "%b-%y"
        )
    )


    current_label = (
        current_month.strftime(
            "%b-%y"
        )
    )


    # -----------------------------------------------------
    # Amount Difference
    # -----------------------------------------------------

    final_df[
        f"Diff {current_label}-{previous_label} | Amount"
    ] = (

        final_df[
            f"{current_label} | Amount"
        ]

        -

        final_df[
            f"{previous_label} | Amount"
        ]

    )


    # -----------------------------------------------------
    # Receipts Difference
    # -----------------------------------------------------

    final_df[
        f"Diff {current_label}-{previous_label} | Receipts"
    ] = (

        final_df[
            f"{current_label} | Receipts"
        ]

        -

        final_df[
            f"{previous_label} | Receipts"
        ]

    )


    # -----------------------------------------------------
    # Due Difference
    # -----------------------------------------------------

    final_df[
        f"Diff {current_label}-{previous_label} | Due"
    ] = (

        final_df[
            f"{current_label} | Due"
        ]

        -

        final_df[
            f"{previous_label} | Due"
        ]

    )


    # -----------------------------------------------------
    # MDP PER BOX DIFFERENCE
    # -----------------------------------------------------

    final_df[
        f"Diff {current_label}-{previous_label} | MDP Per Box"
    ] = (

        final_df[
            f"{current_label} | MDP Per Box"
        ]

        -

        final_df[
            f"{previous_label} | MDP Per Box"
        ]

    )


    # -----------------------------------------------------
    # NOT GIVEN DIFFERENCE
    # -----------------------------------------------------

    final_df[
        f"Diff {current_label}-{previous_label} | Not Given"
    ] = (

        final_df[
            f"{current_label} | Not Given"
        ]

        -

        final_df[
            f"{previous_label} | Not Given"
        ]

    )


# =========================================================
# SERIAL
# =========================================================

final_df.insert(
    0,
    "Sr.",
    range(
        1,
        len(final_df) + 1
    )
)


# =========================================================
# GRAND TOTAL
# =========================================================

grand_total = {}


for col in final_df.columns:

    if col == "Sr.":

        grand_total[col] = ""


    elif col == "Area":

        grand_total[col] = ""


    elif col == "Branch Name":

        grand_total[col] = "GRAND TOTAL"


    elif "MDP Per Box" in col:

        # Weighted / overall MDP per box
        # = Total Due / Total Amount

        parts = col.split("|")

        if len(parts) == 2:

            month_label = (
                parts[0].strip()
            )

            amount_col_name = (
                f"{month_label} | Amount"
            )

            due_col_name = (
                f"{month_label} | Due"
            )

            total_amount = (
                final_df[
                    amount_col_name
                ].sum()
            )

            total_due = (
                final_df[
                    due_col_name
                ].sum()
            )

            grand_total[col] = (

                total_due /
                total_amount

                if total_amount != 0

                else 0

            )

        else:

            grand_total[col] = (
                final_df[col].sum()
            )


    else:

        grand_total[col] = (
            final_df[col].sum()
        )


final_table = pd.concat(

    [
        final_df,

        pd.DataFrame(
            [grand_total]
        )

    ],

    ignore_index=True

)


# =========================================================
# DISPLAY
# =========================================================

st.markdown("---")

st.subheader(
    "📋 MDP Month-wise Comparison"
)


# =========================================================
# FORMAT DISPLAY COPY
# =========================================================

display_final = final_table.copy()


for col in display_final.columns:

    if col in [
        "Area",
        "Branch Name"
    ]:

        display_final[col] = (
            display_final[col]
            .astype(str)
        )

    elif col != "Sr.":

        display_final[col] = pd.to_numeric(
            display_final[col],
            errors="coerce"
        ).fillna(0)


# =========================================================
# SHOW TABLE
# =========================================================

st.dataframe(

    display_final,

    use_container_width=True,

    height=700
)


# =========================================================
# EXPLANATION
# =========================================================

st.markdown("---")

e1, e2 = st.columns(2)


with e1:

    st.markdown("### 📌 MDP Formula")

    st.info("""
**MDP Per Box = Due ÷ Amount**

مثال:

Due = 6,000  
Amount = 1,000  

**6,000 ÷ 1,000 = 6**

یعنی **MDP Per Box = 6**
""")


with e2:

    st.markdown("### 📌 Not Given")

    st.info("""
**Not Given = Due − Amount**

مثال:

Due = 1,000  
Amount = 500  

**1,000 − 500 = 500**

یعنی **500 Not Given**
""")


# =========================================================
# EXCEL DOWNLOAD
# =========================================================

st.markdown("---")

st.subheader(
    "📥 Download Excel"
)


wb = Workbook()

ws = wb.active

ws.title = "MDP Comparison"


# =========================================================
# HEADERS
# =========================================================

for col_num, header in enumerate(
    final_table.columns,
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
# DATA
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
# GRAND TOTAL STYLE
# =========================================================

grand_total_row = ws.max_row


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
# GREEN / RED DIFFERENCE
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


for col_num in range(
    1,
    ws.max_column + 1
):

    header = ws.cell(
        row=1,
        column=col_num
    ).value


    if header and str(
        header
    ).startswith("Diff"):

        col_letter = get_column_letter(
            col_num
        )


        if grand_total_row > 2:

            data_range = (
                f"{col_letter}2:"
                f"{col_letter}"
                f"{grand_total_row - 1}"
            )


            ws.conditional_formatting.add(

                data_range,

                CellIsRule(
                    operator="greaterThan",
                    formula=["0"],
                    fill=green_fill,
                    font=green_font
                )

            )


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
# NUMBER FORMAT
# =========================================================

for col_num in range(
    1,
    ws.max_column + 1
):

    header = ws.cell(
        row=1,
        column=col_num
    ).value


    if header and (
        "MDP Per Box" in str(header)
    ):

        for row_num in range(
            2,
            ws.max_row + 1
        ):

            ws.cell(
                row=row_num,
                column=col_num
            ).number_format = "0.00"


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

    header = ws.cell(
        row=1,
        column=col_num
    ).value


    if header == "Area":

        width = 20

    elif header == "Branch Name":

        width = 22

    else:

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


        width = min(
            max(
                max_length + 3,
                12
            ),
            22
        )


    ws.column_dimensions[
        get_column_letter(
            col_num
        )
    ].width = width


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
# FREEZE AREA ONLY
# =========================================================

ws.freeze_panes = "B2"


# =========================================================
# FILTER
# =========================================================

ws.auto_filter.ref = (
    ws.dimensions
)


# =========================================================
# SAVE
# =========================================================

excel_output = BytesIO()

wb.save(
    excel_output
)

excel_output.seek(0)


# =========================================================
# DOWNLOAD
# =========================================================

st.download_button(

    label="⬇️ Download MDP Comparison Excel",

    data=excel_output.getvalue(),

    file_name=(
        "MDP_Month_Wise_Comparison.xlsx"
    ),

    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),

    use_container_width=True

)
