import os
import ast
import pandas as pd

# ===== CONFIG =====
input_file = r"C:\Users\lmaefos\Code Stuffs\CDE_detective\CDE_ID_detective_revamp\gen3_human_subject_info.xlsx"
sheet_name = 0  # or a sheet name string

AGE_COL    = "cedar_study_metadata.human_subject_applicability.age_applicability"
GENDER_COL = "cedar_study_metadata.human_subject_applicability.gender_applicability"

# ===== Helpers =====
def _parse_list_cell(x):
    """Safely turn a cell into a Python list; return [] for blanks/NaN."""
    if isinstance(x, list):
        return x
    if pd.isna(x):
        return []
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return []
        try:
            return ast.literal_eval(s)
        except Exception:
            s = s.strip("[]")
            parts = [p.strip().strip("'\"") for p in s.split(",")]
            return [p for p in parts if p]
    return []

def expand_list_column(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """
    For a column containing stringified lists like
    "['Adult (19 to 44 years)', 'Adolescent (13 to 18 years)']",
    create one column per unique value, marking 'Yes' or ''.
    New columns are inserted immediately after the source column.
    """
    if col_name not in df.columns:
        print(f"⚠️  Column not found: {col_name} (skipping)")
        return df

    parsed = df[col_name].apply(_parse_list_cell)
    uniques = sorted({val for sub in parsed for val in sub})

    new_cols = {}
    for val in uniques:
        new_cols[val] = parsed.apply(lambda values: "Yes" if val in values else "")

    insert_at = df.columns.get_loc(col_name) + 1
    left = df.iloc[:, :insert_at]
    right = df.iloc[:, insert_at:]
    expanded_block = pd.DataFrame(new_cols, index=df.index)
    df = pd.concat([left, expanded_block, right], axis=1)

    return df

# ===== Run =====
df = pd.read_excel(input_file, sheet_name=sheet_name)

# Expand both Age and Gender
df = expand_list_column(df, AGE_COL)
df = expand_list_column(df, GENDER_COL)

# Always save to target folder
output_folder = r"C:\Users\lmaefos\Code Stuffs\CDE_detective\CDE_ID_detective_revamp"
os.makedirs(output_folder, exist_ok=True)

base_name = os.path.splitext(os.path.basename(input_file))[0]
output_file = os.path.join(output_folder, f"{base_name}_expanded.xlsx")

df.to_excel(output_file, index=False)
print(f"✅ Saved expanded file to: {output_file}")
