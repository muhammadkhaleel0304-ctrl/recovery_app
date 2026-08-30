import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="MDP Month Wise Comparison",
    layout="wide"
)


# =========================================================
# CSS
# =========================================================

st.markdown("""
<style>

.mdp-title {
    background: linear-gradient(135deg,#063b66,#0876b9);
    color: white;
    padding: 18px;
    border-radius: 12px;
    text-align: center;
    font-size: 28px;
    font-weight: 800;
    margin-bottom: 20px;
}

.block-title {
    background: #063b66;
    color: white;
    padding: 10px;
    border-radius: 8px;
    font-size: 20px;
    font-weight: 700;
    margin-top: 20px;
}

</style>
""", unsafe_allow_html=True)


st.markdown(
    '<div class="mdp-title">📊 MDP MONTH-WISE COMPARISON REPORT</div>',
    unsafe_allow_html=True
)


# =========================================================
# SESSION STATE
# =========================================================

if "mdp_due_values" not in st.session_state:
    st.session_state.mdp_due_values = {}


# =========================================================
# COLUMN FINDER
# =========================================================

def find_column(df, possible_names):

    for col in possible_names:

        if col in df.columns:
            return col

    return None


# =========================================================
# CLEAN COLUMNS
# =========================================================

def clean_columns(df):

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace("/", "_", regex=False)
    )

    return df


# =========================================================
# FIND AMOUNT / RECEIPT COLUMNS
# =========================================================

def detect_columns(df):

    branch_code = find_column(
        df,
        [
            "branch_id",
            "branch_code",
            "branchcode",
            "branch_no",
            "branch_number"
        ]
    )

    branch_name = find_column(
        df,
        [
            "branch_name",
            "branchname",
            "branch_title",
            "branch"
        ]
    )

    area = find_column(
        df,
        [
            "area",
            "area_name",
            "region",
            "zone"
        ]
    )

    amount = find_column(
        df,
        [
            "amount",
            "recovery_amount",
            "total_amount",
            "recovery",
            "recovery_amount_"
        ]
    )

    receipts = find_column(
        df,
        [
            "receipts",
            "receipt",
            "receipt_no",
            "total_receipts",
            "slips",
            "no_of_receipts",
            "number_of_receipts"
        ]
    )

    return (
        branch_code,
        branch_name,
        area,
        amount,
        receipts
    )


# =========================================================
# UPLOAD
# =========================================================

st.subheader("📤 Upload MDP Month Files")

uploaded_files = st.file_uploader(
    "Upload one or more MDP Excel files",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
    key="mdp_month_upload"
)

if not uploaded_files:

    st.info(
        "Please upload MDP Excel files for the months "
        "you want to compare."
    )

    st.stop()


# =========================================================
# READ ALL FILES
# =========================================================

month_data = []


for file in uploaded_files:

    try:

        excel = pd.ExcelFile(file)

        sheet = st.selectbox(
            f"Select Sheet - {file.name}",
            excel.sheet_names,
            key=f"sheet_{file.name}"
        )

        temp = pd.read_excel(
            file,
            sheet_name=sheet
        )

        temp = clean_columns(temp)

        (
            branch_code_col,
            branch_name_col,
            area_col,
            amount_col,
            receipts_col
        ) = detect_columns(temp)


        # -------------------------------------------------
        # Manual column selection
        # -------------------------------------------------

        st.markdown(
            f"### 🔧 Column Mapping — {file.name}"
        )

        available = list(temp.columns)

        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:

            if branch_code_col is None:

                branch_code_col = st.selectbox(
                    "Branch Code",
                    ["None"] + available,
                    key=f"bc_{file.name}"
                )

                if branch_code_col == "None":
                    branch_code_col = None

        with c2:

            if branch_name_col is None:

                branch_name_col = st.selectbox(
                    "Branch Name",
                    ["None"] + available,
                    key=f"bn_{file.name}"
                )

                if branch_name_col == "None":
                    branch_name_col = None

        with c3:

            if area_col is None:

                area_col = st.selectbox(
                    "Area",
                    ["None"] + available,
                    key=f"area_{file.name}"
                )

                if area_col == "None":
                    area_col = None

        with c4:

            if amount_col is None:

                amount_col = st.selectbox(
                    "Amount",
                    ["None"] + available,
                    key=f"amount_{file.name}"
                )

                if amount_col == "None":
                    amount_col = None

        with c5:

            if receipts_col is None:

                receipts_col = st.selectbox(
                    "Receipts",
                    ["None"] + available,
                    key=f"receipt_{file.name}"
                )

                if receipts_col == "None":
                    receipts_col = None


        if branch_name_col is None:
            st.error(
                f"{file.name}: Branch Name column is required."
            )
            st.stop()

        if amount_col is None:
            st.error(
                f"{file.name}: Amount column is required."
            )
            st.stop()

        if receipts_col is None:
            st.error(
                f"{file.name}: Receipts column is required."
            )
            st.stop()


        # -------------------------------------------------
        # MONTH NAME
        # -------------------------------------------------

        default_month = (
            file.name
            .replace(".xlsx", "")
            .replace(".xls", "")
        )

        month_label = st.text_input(
            "Month Name",
            value=default_month,
            key=f"month_{file.name}"
        )


        # -------------------------------------------------
        # STANDARD DATA
        # -------------------------------------------------

        work = pd.DataFrame()

        if branch_code_col:

            work["Branch Code"] = (
                temp[branch_code_col]
                .astype(str)
                .str.strip()
            )

        else:

            work["Branch Code"] = ""


        if area_col:

            work["Area"] = (
                temp[area_col]
                .astype(str)
                .str.strip()
            )

        else:

            work["Area"] = ""


        work["Branch Name"] = (
            temp[branch_name_col]
            .astype(str)
            .str.strip()
        )


        work["Amount"] = pd.to_numeric(
            temp[amount_col],
            errors="coerce"
        ).fillna(0)


        work["Receipts"] = pd.to_numeric(
            temp[receipts_col],
            errors="coerce"
        ).fillna(0)


        # -------------------------------------------------
        # GROUP BRANCH
        # -------------------------------------------------

        work = (
            work
            .groupby(
                [
                    "Branch Code",
                    "Area",
                    "Branch Name"
                ],
                as_index=False
            )
            .agg(
                {
                    "Amount": "sum",
                    "Receipts": "sum"
                }
            )
        )


        month_data.append(
            {
                "month": month_label,
                "data": work
            }
        )


    except Exception as e:

        st.error(
            f"Error reading {file.name}: {e}"
        )

        st.stop()


# =========================================================
# SORT MONTHS
# =========================================================

if len(month_data) == 0:

    st.error("No month data found.")

    st.stop()


# =========================================================
# MONTH NAMES
# =========================================================

month_names = [
    x["month"]
    for x in month_data
]


# =========================================================
# BUILD MASTER BRANCH LIST
# =========================================================

all_parts = []

for item in month_data:

    temp = item["data"][
        [
            "Branch Code",
            "Area",
            "Branch Name"
        ]
    ].copy()

    all_parts.append(temp)


all_branches = (
    pd.concat(
        all_parts,
        ignore_index=True
    )
    .drop_duplicates()
)


all_branches = (
    all_branches
    .sort_values(
        [
            "Area",
            "Branch Code",
            "Branch Name"
        ]
    )
    .reset_index(drop=True)
)


all_branches.insert(
    0,
    "Sr.",
    range(
        1,
        len(all_branches) + 1
    )
)


# =========================================================
# MANUAL DUE ENTRY
# =========================================================

st.markdown("---")

st.subheader("✏️ Enter Due Manually")

st.info(
    "Due آپ خود enter کریں۔ "
    "MDP Per Box اور Not Given automatically calculate ہوں گے۔"
)


# =========================================================
# DUE INPUT
# =========================================================

due_data = {}


for month_item in month_data:

    month = month_item["month"]

    st.markdown(
        f'<div class="block-title">📅 {month} — Due Entry</div>',
        unsafe_allow_html=True
    )


    # Header
    h = st.columns(4)

    with h[0]:
        st.markdown("**Sr.**")

    with h[1]:
        st.markdown("**Area**")

    with h[2]:
        st.markdown("**Branch Name**")

    with h[3]:
        st.markdown("**Due**")


    month_due = {}


    for idx, branch in all_branches.iterrows():

        branch_code = str(
            branch["Branch Code"]
        )

        area = str(
            branch["Area"]
        )

        branch_name = str(
            branch["Branch Name"]
        )


        key = (
            month,
            branch_code,
            branch_name
        )


        old_value = st.session_state.mdp_due_values.get(
            key,
            0.0
        )


        cols = st.columns(4)


        with cols[0]:

            st.write(
                int(branch["Sr."])
            )


        with cols[1]:

            st.write(area)


        with cols[2]:

            st.write(branch_name)


        with cols[3]:

            due_value = st.number_input(
                f"Due - {month} - {branch_name}",
                min_value=0.0,
                value=float(old_value),
                step=1.0,
                key=f"due_input_{month}_{idx}_{branch_code}"
            )


            month_due[
                key
            ] = due_value


            st.session_state.mdp_due_values[
                key
            ] = due_value


    due_data[month] = month_due


# =========================================================
# CREATE MONTH REPORT
# =========================================================

reports = {}


for item in month_data:

    month = item["month"]

    source = item["data"].copy()


    result = all_branches.copy()


    result = result.merge(
        source,
        on=[
            "Branch Code",
            "Area",
            "Branch Name"
        ],
        how="left"
    )


    result["Amount"] = (
        result["Amount"]
        .fillna(0)
    )


    result["Receipts"] = (
        result["Receipts"]
        .fillna(0)
    )


    # -----------------------------------------------------
    # Due
    # -----------------------------------------------------

    due_values = []


    for _, row in result.iterrows():

        key = (
            month,
            str(row["Branch Code"]),
            str(row["Branch Name"])
        )


        due_values.append(
            st.session_state.mdp_due_values.get(
                key,
                0.0
            )
        )


    result["Due"] = due_values


    # -----------------------------------------------------
    # MDP PER BOX
    #
    # IMPORTANT:
    # Amount / Due
    # -----------------------------------------------------

    result["MDP Per Box"] = np.where(
        result["Due"] == 0,
        0,
        result["Amount"] / result["Due"]
    )


    # -----------------------------------------------------
    # NOT GIVEN
    #
    # IMPORTANT:
    # Due - Receipts
    # -----------------------------------------------------

    result["Not Given"] = (
        result["Due"]
        -
        result["Receipts"]
    )


    reports[month] = result


# =========================================================
# DISPLAY MONTH REPORTS
# =========================================================

st.markdown("---")

st.subheader("📋 MDP Month-wise Reports")


for month in month_names:

    report = reports[month].copy()


    display = report[
        [
            "Sr.",
            "Area",
            "Branch Name",
            "Amount",
            "Receipts",
            "Due",
            "MDP Per Box",
            "Not Given"
        ]
    ].copy()


    # Grand Total
    total_row = {
        "Sr.": "",
        "Area": "",
        "Branch Name": "GRAND TOTAL",
        "Amount": display["Amount"].sum(),
        "Receipts": display["Receipts"].sum(),
        "Due": display["Due"].sum(),
        "MDP Per Box": (
            display["Amount"].sum()
            /
            display["Due"].sum()
            if display["Due"].sum() != 0
            else 0
        ),
        "Not Given": (
            display["Due"].sum()
            -
            display["Receipts"].sum()
        )
    }


    display = pd.concat(
        [
            display,
            pd.DataFrame([total_row])
        ],
        ignore_index=True
    )


    st.markdown(
        f'<div class="block-title">📅 {month}</div>',
        unsafe_allow_html=True
    )


    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        height=350
    )


# =========================================================
# DIFFERENCE REPORT
# =========================================================

if len(month_names) >= 2:

    st.markdown("---")

    st.subheader("📊 Month-wise Difference")


    # -----------------------------------------------------
    # Base = First Month
    # Latest = Last Month
    # -----------------------------------------------------

    old_month = month_names[0]
    new_month = month_names[-1]


    old_df = reports[old_month].copy()
    new_df = reports[new_month].copy()


    comparison = all_branches.copy()


    comparison = comparison.merge(
        old_df[
            [
                "Branch Code",
                "Area",
                "Branch Name",
                "Amount",
                "Receipts",
                "Due",
                "MDP Per Box",
                "Not Given"
            ]
        ],
        on=[
            "Branch Code",
            "Area",
            "Branch Name"
        ],
        how="left",
        suffixes=(
            "",
            f" {old_month}"
        )
    )


    comparison = comparison.merge(
        new_df[
            [
                "Branch Code",
                "Area",
                "Branch Name",
                "Amount",
                "Receipts",
                "Due",
                "MDP Per Box",
                "Not Given"
            ]
        ],
        on=[
            "Branch Code",
            "Area",
            "Branch Name"
        ],
        how="left",
        suffixes=(
            f" {old_month}",
            f" {new_month}"
        )
    )


    # -----------------------------------------------------
    # Rename duplicate columns safely
    # -----------------------------------------------------

    old_amount = f"Amount {old_month}"
    old_receipts = f"Receipts {old_month}"
    old_due = f"Due {old_month}"
    old_mdp = f"MDP Per Box {old_month}"
    old_not_given = f"Not Given {old_month}"


    new_amount = f"Amount {new_month}"
    new_receipts = f"Receipts {new_month}"
    new_due = f"Due {new_month}"
    new_mdp = f"MDP Per Box {new_month}"
    new_not_given = f"Not Given {new_month}"


    # In case pandas generated alternate names
    if old_amount not in comparison.columns:

        old_amount = "Amount_x"

    if new_amount not in comparison.columns:

        new_amount = "Amount_y"


    if old_receipts not in comparison.columns:

        old_receipts = "Receipts_x"

    if new_receipts not in comparison.columns:

        new_receipts = "Receipts_y"


    if old_due not in comparison.columns:

        old_due = "Due_x"

    if new_due not in comparison.columns:

        new_due = "Due_y"


    if old_mdp not in comparison.columns:

        old_mdp = "MDP Per Box_x"

    if new_mdp not in comparison.columns:

        new_mdp = "MDP Per Box_y"


    if old_not_given not in comparison.columns:

        old_not_given = "Not Given_x"

    if new_not_given not in comparison.columns:

        new_not_given = "Not Given_y"


    # -----------------------------------------------------
    # DIFFERENCE
    # -----------------------------------------------------

    comparison[
        f"Diff {new_month}-{old_month} | Amount"
    ] = (
        comparison[new_amount]
        -
        comparison[old_amount]
    )


    comparison[
        f"Diff {new_month}-{old_month} | Receipts"
    ] = (
        comparison[new_receipts]
        -
        comparison[old_receipts]
    )


    comparison[
        f"Diff {new_month}-{old_month} | Due"
    ] = (
        comparison[new_due]
        -
        comparison[old_due]
    )


    comparison[
        f"Diff {new_month}-{old_month} | MDP Per Box"
    ] = (
        comparison[new_mdp]
        -
        comparison[old_mdp]
    )


    comparison[
        f"Diff {new_month}-{old_month} | Not Given"
    ] = (
        comparison[new_not_given]
        -
        comparison[old_not_given]
    )


    # -----------------------------------------------------
    # FINAL DIFFERENCE TABLE
    # -----------------------------------------------------

    diff_columns = [
        "Sr.",
        "Area",
        "Branch Name",
        f"Diff {new_month}-{old_month} | Amount",
        f"Diff {new_month}-{old_month} | Receipts",
        f"Diff {new_month}-{old_month} | Due",
        f"Diff {new_month}-{old_month} | MDP Per Box",
        f"Diff {new_month}-{old_month} | Not Given"
    ]


    diff_display = comparison[
        diff_columns
    ].copy()


    # -----------------------------------------------------
    # GRAND TOTAL DIFFERENCE
    # -----------------------------------------------------

    diff_total = {
        "Sr.": "",
        "Area": "",
        "Branch Name": "GRAND TOTAL"
    }


    for col in diff_columns[3:]:

        diff_total[col] = (
            diff_display[col]
            .sum()
        )


    diff_display = pd.concat(
        [
            diff_display,
            pd.DataFrame([diff_total])
        ],
        ignore_index=True
    )


    st.markdown(
        f'<div class="block-title">📈 Diff {new_month} - {old_month}</div>',
        unsafe_allow_html=True
    )


    st.dataframe(
        diff_display,
        use_container_width=True,
        hide_index=True,
        height=400
    )


# =========================================================
# EXCEL EXPORT
# =========================================================

st.markdown("---")

st.subheader("⬇️ Download Excel")


wb = Workbook()

# Remove default sheet later
default_ws = wb.active
default_ws.title = "MDP Comparison"


# =========================================================
# STYLES
# =========================================================

header_fill = PatternFill(
    fill_type="solid",
    fgColor="063B66"
)

header_font = Font(
    bold=True,
    color="FFFFFF"
)

grand_fill = PatternFill(
    fill_type="solid",
    fgColor="063B66"
)

grand_font = Font(
    bold=True,
    color="FFFFFF"
)

green_fill = PatternFill(
    fill_type="solid",
    fgColor="C6EFCE"
)

green_font = Font(
    bold=True,
    color="006100"
)

red_fill = PatternFill(
    fill_type="solid",
    fgColor="FFC7CE"
)

red_font = Font(
    bold=True,
    color="9C0006"
)

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


# =========================================================
# WRITE MONTH BLOCKS
# =========================================================

for month in month_names:

    report = reports[month].copy()


    ws = wb.create_sheet(
        title=month[:31]
    )


    headers = [
        "Sr.",
        "Area",
        "Branch Name",
        f"{month} | Amount",
        f"{month} | Receipts",
        f"{month} | Due",
        f"{month} | MDP Per Box",
        f"{month} | Not Given"
    ]


    for col_num, header in enumerate(
        headers,
        start=1
    ):

        cell = ws.cell(
            row=1,
            column=col_num,
            value=header
        )

        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )
        cell.border = thin_border


    # -----------------------------------------------------
    # DATA
    # -----------------------------------------------------

    for row_num, (_, row) in enumerate(
        report.iterrows(),
        start=2
    ):

        values = [
            row["Sr."],
            row["Area"],
            row["Branch Name"],
            row["Amount"],
            row["Receipts"],
            row["Due"],
            row["MDP Per Box"],
            row["Not Given"]
        ]


        for col_num, value in enumerate(
            values,
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

            cell.border = thin_border


    # -----------------------------------------------------
    # GRAND TOTAL
    # -----------------------------------------------------

    gt_row = ws.max_row + 1


    gt_values = [
        "",
        "",
        "GRAND TOTAL",
        report["Amount"].sum(),
        report["Receipts"].sum(),
        report["Due"].sum(),
        (
            report["Amount"].sum()
            /
            report["Due"].sum()
            if report["Due"].sum() != 0
            else 0
        ),
        (
            report["Due"].sum()
            -
            report["Receipts"].sum()
        )
    ]


    for col_num, value in enumerate(
        gt_values,
        start=1
    ):

        cell = ws.cell(
            row=gt_row,
            column=col_num,
            value=value
        )

        cell.fill = grand_fill
        cell.font = grand_font

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

        cell.border = thin_border


    # -----------------------------------------------------
    # FORMATS
    # -----------------------------------------------------

    for row_num in range(
        2,
        ws.max_row + 1
    ):

        for col_num in [
            4,
            5,
            6,
            7,
            8
        ]:

            ws.cell(
                row=row_num,
                column=col_num
            ).number_format = '#,##0.00'


    # -----------------------------------------------------
    # WIDTH
    # -----------------------------------------------------

    widths = {
        1: 8,
        2: 20,
        3: 25,
        4: 18,
        5: 18,
        6: 18,
        7: 20,
        8: 18
    }


    for col_num, width in widths.items():

        ws.column_dimensions[
            get_column_letter(col_num)
        ].width = width


    ws.row_dimensions[1].height = 30


    # -----------------------------------------------------
    # FREEZE AREA + BRANCH
    # -----------------------------------------------------

    ws.freeze_panes = "D2"


    # -----------------------------------------------------
    # FILTER
    # -----------------------------------------------------

    ws.auto_filter.ref = ws.dimensions


# =========================================================
# DIFFERENCE SHEET
# =========================================================

if len(month_names) >= 2:

    old_month = month_names[0]
    new_month = month_names[-1]


    ws = wb.create_sheet(
        title="MDP Comparison"
    )


    diff_columns = [
        "Sr.",
        "Area",
        "Branch Name",
        f"Diff {new_month}-{old_month} | Amount",
        f"Diff {new_month}-{old_month} | Receipts",
        f"Diff {new_month}-{old_month} | Due",
        f"Diff {new_month}-{old_month} | MDP Per Box",
        f"Diff {new_month}-{old_month} | Not Given"
    ]


    for col_num, header in enumerate(
        diff_columns,
        start=1
    ):

        cell = ws.cell(
            row=1,
            column=col_num,
            value=header
        )

        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

        cell.border = thin_border


    # -----------------------------------------------------
    # DATA
    # -----------------------------------------------------

    for row_num, (_, row) in enumerate(
        comparison.iterrows(),
        start=2
    ):

        values = [
            row["Sr."],
            row["Area"],
            row["Branch Name"],
            row[
                f"Diff {new_month}-{old_month} | Amount"
            ],
            row[
                f"Diff {new_month}-{old_month} | Receipts"
            ],
            row[
                f"Diff {new_month}-{old_month} | Due"
            ],
            row[
                f"Diff {new_month}-{old_month} | MDP Per Box"
            ],
            row[
                f"Diff {new_month}-{old_month} | Not Given"
            ]
        ]


        for col_num, value in enumerate(
            values,
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

            cell.border = thin_border


    # -----------------------------------------------------
    # GRAND TOTAL
    # -----------------------------------------------------

    gt_row = ws.max_row + 1


    ws.cell(
        row=gt_row,
        column=3,
        value="GRAND TOTAL"
    )


    for col_num in range(
        4,
        9
    ):

        ws.cell(
            row=gt_row,
            column=col_num,
            value=ws.cell(
                row=2,
                column=col_num
            ).value
            if ws.max_row == 2
            else f"=SUM({get_column_letter(col_num)}2:{get_column_letter(col_num)}{gt_row-1})"
        )


    for col_num in range(
        1,
        9
    ):

        cell = ws.cell(
            row=gt_row,
            column=col_num
        )

        cell.fill = grand_fill
        cell.font = grand_font
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )
        cell.border = thin_border


    # -----------------------------------------------------
    # CONDITIONAL FORMATTING
    # -----------------------------------------------------

    first_data = 2
    last_data = gt_row - 1


    for col_num in range(
        4,
        9
    ):

        letter = get_column_letter(
            col_num
        )


        data_range = (
            f"{letter}{first_data}:"
            f"{letter}{last_data}"
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


    # -----------------------------------------------------
    # WIDTH
    # -----------------------------------------------------

    widths = {
        1: 8,
        2: 20,
        3: 25,
        4: 25,
        5: 25,
        6: 25,
        7: 28,
        8: 28
    }


    for col_num, width in widths.items():

        ws.column_dimensions[
            get_column_letter(col_num)
        ].width = width


    ws.freeze_panes = "D2"

    ws.auto_filter.ref = ws.dimensions


# =========================================================
# REMOVE EMPTY DEFAULT SHEET
# =========================================================

if (
    "Sheet" in wb.sheetnames
    and len(wb.sheetnames) > 1
):

    del wb["Sheet"]


# =========================================================
# SAVE
# =========================================================

output = BytesIO()

wb.save(output)

output.seek(0)


# =========================================================
# DOWNLOAD
# =========================================================

st.download_button(
    label="⬇️ Download MDP Month Wise Comparison Excel",
    data=output.getvalue(),
    file_name="MDP_Month_Wise_Comparison.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
    use_container_width=True
)
