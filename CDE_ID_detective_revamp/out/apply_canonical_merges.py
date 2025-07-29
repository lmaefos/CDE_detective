import os
import pandas as pd
import re

# === CONFIG ===
EXCEL_FILE    = "HDP00066_ACTNOWOBOE_DataDictionary_REDCap.vlmd_2025-07-29.xlsx"
SHEET_NAME    = "EnhancedDD"
CANONICAL_COL = "Canonical CRF Name"
MERGES_FILE   = "confirmed_merges.csv"
OUTPUT_FILE   = EXCEL_FILE   # overwrite same file

# Metadata columns
CRF_COL           = "section"
RATIONALE_COL     = "Rationale"
FULL_RESPONSE_COL = "Full Response"

def prettify_name(name):
    if not isinstance(name, str):
        return name
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

# --- load the main sheet ---
df = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_NAME)

# --- load merges if any ---
if os.path.exists(MERGES_FILE) and os.path.getsize(MERGES_FILE) > 0:
    merges = pd.read_csv(MERGES_FILE)
else:
    merges = pd.DataFrame()

# --- only do the replace step if merges.csv actually had rows ---
if not merges.empty:
    replace_map = {}
    for _, row in merges.iterrows():
        replace_map[row["Canonical1"]] = row["MergedName"]
        replace_map[row["Canonical2"]] = row["MergedName"]
    df[CANONICAL_COL] = df[CANONICAL_COL].replace(replace_map)
else:
    print("→ no merges to apply, skipping that step.")

# --- prettify names no matter what ---
df[CANONICAL_COL] = df[CANONICAL_COL].apply(prettify_name)

# --- rebuild your metadata sheet ---
metadata_df = (
    df[[CRF_COL, CANONICAL_COL, RATIONALE_COL, FULL_RESPONSE_COL]]
    .drop_duplicates(subset=[CRF_COL, CANONICAL_COL])
    .reset_index(drop=True)
)
metadata_df[CANONICAL_COL] = metadata_df[CANONICAL_COL].apply(prettify_name)

# --- write everything out with freeze + autofilter + autofit ---
with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
    df.to_excel(writer,      sheet_name="EnhancedDD", index=False)
    metadata_df.to_excel(writer, sheet_name="Metadata",  index=False)

    wb          = writer.book
    ws_dd       = writer.sheets["EnhancedDD"]
    ws_meta     = writer.sheets["Metadata"]

    # freeze
    ws_dd.freeze_panes(1, 0)
    ws_meta.freeze_panes(1, 0)

    # autofilter
    ws_dd.autofilter(0, 0, df.shape[0],         df.shape[1]-1)
    ws_meta.autofilter(0, 0, metadata_df.shape[0], metadata_df.shape[1]-1)

    # autofit cols
    for ws, data in ((ws_dd, df), (ws_meta, metadata_df)):
        for idx, col in enumerate(data.columns):
            max_len = max(
                data[col].astype(str).map(len).max(),
                len(str(col))
            ) + 2
            ws.set_column(idx, idx, max_len)

print(f"Saved prettified sheets to {OUTPUT_FILE}")