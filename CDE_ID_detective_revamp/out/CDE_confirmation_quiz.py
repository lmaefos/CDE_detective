import os
import pandas as pd

# === CONFIG ===
INPUT_FILE        = "ThePersistStudy_DataDictionary_2023-09-15_2025-08-07.xlsx"
SHEET_NAME        = "EnhancedDD"
MATCH_COL         = "HEAL Core CRF Match"
RATIONALE_COL     = "Rationale"
CANONICAL_COL     = "Canonical CRF Name"
CRF_COL           = "Form Name"
FULL_RESPONSE_COL = "Full Response"
OUTPUT_FILE       = "ThePersistStudy_DataDictionary_2023-09-15_2025-08-07_matches_confirmed.xlsx"

# Your approved CRF choices:
CRF_OPTIONS = [
    "Brief Pain Inventory (BPI)",
    "BPI Pain Interference",
    "BPI Pain Severity",
    "Demographics",
    "GAD2 Pain (Generalized Anxiety Disorder)",
    "GAD7",
    "NIDAL2 (NIDA Modified ASSIST L2)",
    "PCS6 (Pain Catastrophizing Scale)",
    "PCS13",
    "PCS Child",
    "PCS Parent",
    "PedsQL (Pediatric Quality of Life Inventory)",
    "PEG Pain",
    "PGIC Pain(Patient Global Impression of Change Pain)",
    "PGIS (Patient Global Impression of Severity)",
    "PHQ2 (Patient Health Questionnaire 2)",
    "PHQ8",
    "PHQ9",
    "PROMIS PF Pain (PROMIS Physical Function Pain)",
    "PROMIS PF Pain 6b (PROMIS Physical Function Pain 6b)",
    "PROMIS Sleep Disturbance 6a",
    "Sleep Duration Pain",
    "SleepASWS (Adolescent Sleep Wake Scale)",
    "TAPS Pain",
    "WHOQOL2"
]

def main():
    # 1) Load sheet
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    # 2) Interactive match-confirmation with list option
    to_check = df[df[MATCH_COL].fillna("No CRF match") != "No CRF match"].index.tolist()
    print(f"🔍 {len(to_check)} rows with proposed matches found.\n")

    decisions = {}

    for idx in to_check:
        canon = df.at[idx, CANONICAL_COL]
        orig  = df.at[idx, MATCH_COL]
        key   = (canon, orig)

        # auto-apply
        if key in decisions:
            choice = decisions[key]
            if choice is None:
                df.at[idx, MATCH_COL] = "No CRF match"
                print(f"↪ Auto-no for {canon} → {orig} (row {idx+2})\n")
            else:
                df.at[idx, MATCH_COL] = choice
                print(f"↪ Auto-set {canon} → '{choice}' (row {idx+2})\n")
            continue

        # prompt
        rationale = df.at[idx, RATIONALE_COL]
        print(f"Row {idx+2}:")
        print(f"  {CRF_COL.capitalize()}          → {df.at[idx, CRF_COL]}")
        print(f"  Canonical CRF Name → {canon}")
        print(f"  Proposed match     → {orig}")
        print(f"  Rationale          → {rationale}\n")

        ans = input("Keep? [y]es / [n]o / [l]ist / [c]ustom / [s]kip all: ").strip().lower()
        if ans == "s":
            print("⏭ Skipping the rest.")
            break
        elif ans == "y":
            choice = orig
        elif ans == "n":
            choice = None
        elif ans == "c":
            choice = input("Enter custom CRF name: ").strip()
        elif ans == "l":
            print("\nSelect from these CRF options:")
            for i, opt in enumerate(CRF_OPTIONS, 1):
                print(f"  {i}. {opt}")
            sel = input("Enter number (or 0 to cancel): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(CRF_OPTIONS):
                choice = CRF_OPTIONS[int(sel)-1]
            else:
                choice = None
        else:
            choice = None

        decisions[key] = choice
        if choice is None:
            df.at[idx, MATCH_COL] = "No CRF match"
            print("✖ Marked as 'No CRF match'.\n")
        else:
            df.at[idx, MATCH_COL] = choice
            print(f"✔ Set match to '{choice}'.\n")

    # 3) Build Metadata sheet
    metadata_df = (
        df[[CRF_COL, CANONICAL_COL, RATIONALE_COL, FULL_RESPONSE_COL]]
        .drop_duplicates(subset=[CRF_COL, CANONICAL_COL])
        .reset_index(drop=True)
    )

    # 4) Build “wide” report
    grouped = (
        df[df[MATCH_COL].fillna("No CRF match") != "No CRF match"]
        .groupby(MATCH_COL)[CRF_COL]
        .apply(lambda s: sorted(s.unique()))
        .to_dict()
    )
    max_len = max((len(v) for v in grouped.values()), default=0)
    report_data = {
        m: vals + [""]*(max_len - len(vals))
        for m, vals in grouped.items()
    }
    report_df = pd.DataFrame(report_data)

    # 5) Write all sheets (guarding Report)
    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        # Always write EnhancedDD & Metadata
        df.to_excel(writer,      sheet_name=SHEET_NAME, index=False)
        metadata_df.to_excel(writer, sheet_name="Metadata", index=False)

        wb      = writer.book
        ws_dd   = writer.sheets[SHEET_NAME]
        ws_meta = writer.sheets["Metadata"]

        # Format those two
        for ws, data in ((ws_dd, df), (ws_meta, metadata_df)):
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, data.shape[0], data.shape[1] - 1)
            for col_idx, col in enumerate(data.columns):
                width = max(data[col].astype(str).map(len).max(), len(col)) + 2
                ws.set_column(col_idx, col_idx, width)

        # Only write & format Report if it has at least one column
        if report_df.shape[1] > 0:
            ws_rep = report_df.to_excel(writer, sheet_name="Report", index=False)
            ws_rep = writer.sheets["Report"]
            ws_rep.freeze_panes(1, 0)
            ws_rep.autofilter(0, 0, report_df.shape[0], report_df.shape[1] - 1)
            for col_idx, col in enumerate(report_df.columns):
                width = max(report_df[col].astype(str).map(len).max(), len(col)) + 2
                ws_rep.set_column(col_idx, col_idx, width)
        else:
            print("→ No Report sheet (no confirmed matches)")

    print(f"🎉 Finished! Workbook saved as {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
