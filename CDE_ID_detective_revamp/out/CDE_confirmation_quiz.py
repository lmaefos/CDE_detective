import os
import pandas as pd

# === CONFIG ===
INPUT_FILE      = "HDP01057_HRRN_baseline_survey.vlmd_2025-07-28.xlsx"
SHEET_NAME      = "EnhancedDD"
MATCH_COL       = "HEAL Core CRF Match"
RATIONALE_COL   = "Match Rationale"
CANONICAL_COL   = "Canonical CRF Name"
CRF_COL         = "section"
FULL_RESPONSE_COL = "Full Response"  # adjust if yours is named differently
OUTPUT_FILE     = "HDP01057_HRRN_baseline_survey.vlmd_2025-07-29_matches_confirmed.xlsx"

def main():
    # Load sheet
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    # Prepare interactive check list
    to_check = df[df[MATCH_COL].fillna("No CRF match") != "No CRF match"].index.tolist()
    print(f"🔍 {len(to_check)} rows with proposed matches found.\n")

    # Cache for auto‐applying your yes/no per unique (canonical, match) pair
    decisions = {}

    for idx in to_check:
        canon = df.at[idx, CANONICAL_COL]
        prop  = df.at[idx, MATCH_COL]
        key   = (canon, prop)

        # Auto‐apply if we’ve seen this combo
        if key in decisions:
            if not decisions[key]:
                df.at[idx, MATCH_COL] = "No CRF match"
                print(f"↪ Auto-no for {canon} → {prop} (row {idx+2})\n")
            else:
                print(f"↪ Auto-yes for {canon} → {prop} (row {idx+2})\n")
            continue

        # First time seeing this pair, prompt
        rationale = df.at[idx, RATIONALE_COL]
        print(f"Row {idx+2}:")
        print(f"  {CRF_COL.capitalize()}          → {df.at[idx, CRF_COL]}")
        print(f"  Canonical CRF Name → {canon}")
        print(f"  Proposed match     → {prop}")
        print(f"  Rationale          → {rationale}\n")

        ans = input("Keep this match? [y]es / [n]o / [s]kip all: ").strip().lower()
        if ans == "s":
            print("⏭ Skipping the rest.")
            break

        keep = (ans == "y")
        decisions[key] = keep

        if not keep:
            df.at[idx, MATCH_COL] = "No CRF match"
            print("✖ Marked as 'No CRF match'.\n")
        else:
            print("✔ Keeping it as is.\n")

    # Build Metadata sheet
    metadata_df = (
        df[[CRF_COL, CANONICAL_COL, RATIONALE_COL, FULL_RESPONSE_COL]]
        .drop_duplicates(subset=[CRF_COL, CANONICAL_COL])
        .reset_index(drop=True)
    )

    # Write both sheets with freeze, filter, and autofit
    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)
        metadata_df.to_excel(writer, sheet_name="Metadata", index=False)

        wb      = writer.book
        ws_dd   = writer.sheets[SHEET_NAME]
        ws_meta = writer.sheets["Metadata"]

        # Freeze top row
        ws_dd.freeze_panes(1, 0)
        ws_meta.freeze_panes(1, 0)

        # Apply autofilter
        ws_dd.autofilter(0, 0, df.shape[0],         df.shape[1]-1)
        ws_meta.autofilter(0, 0, metadata_df.shape[0], metadata_df.shape[1]-1)

        # Auto-fit column widths
        for ws, data in ((ws_dd, df), (ws_meta, metadata_df)):
            for col_idx, col in enumerate(data.columns):
                max_len = max(
                    data[col].astype(str).map(len).max(),
                    len(str(col))
                ) + 2
                ws.set_column(col_idx, col_idx, max_len)

    print(f"🎉 Finished! Updated workbook saved as {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
