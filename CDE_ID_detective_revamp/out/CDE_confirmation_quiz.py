import os
import pandas as pd

# === CONFIG ===
INPUT_FILE            = "Testfile_2025-09-15_canonical_merge.xlsx"
SHEET_NAME            = "EnhancedDD"
MATCH_COL             = "HEAL Core CRF Match"
RATIONALE_COL         = "Rationale"
CANONICAL_COL         = "Canonical CRF Name"
CRF_COL               = "section"            # original CRF name
VARIABLE_NAME_COLUMN  = "name"               # original variable name
FULL_RESPONSE_COL     = "Full Response"
OUTPUT_FILE           = "Testfile_2025-09-15_canonical_merge_matches_confirmed.xlsx"

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

    decisions = {}          # (canon, orig) -> choice (str or None)
    decisions_meta = {}     # (canon, orig) -> {"choice": str|None, "decision_type": "y"|"n"|"l"}
    discrepancies = []      # list of full-row dicts with metadata

    # NEW: history stack so we can undo
    history = []  # each item: {"idx","prev_match","key","decision_type","discrepancy_added","auto_applied"}

    # Use an index pointer so we can step back on undo
    i = 0
    tip_shown = False
    while i < len(to_check):
        idx = to_check[i]
        canon = df.at[idx, CANONICAL_COL]
        orig  = df.at[idx, MATCH_COL]
        key   = (canon, orig)

        # auto-apply a previous decision for the same (canonical, proposed) pair
        if key in decisions:
            choice = decisions[key]
            meta   = decisions_meta.get(key, {})
            prev_match = df.at[idx, MATCH_COL]

            if choice is None:
                df.at[idx, MATCH_COL] = "No CRF match"
                print(f"↪ Auto-no for {canon} → {orig} (row {idx+2})\n")
            else:
                df.at[idx, MATCH_COL] = choice
                print(f"↪ Auto-set {canon} → '{choice}' (row {idx+2})\n")

            # Log auto-applied discrepancy if original manual decision was n or l
            discrepancy_added = False
            if meta.get("decision_type") in {"n", "l"}:
                row_dict = df.loc[idx].to_dict()
                row_dict.update({
                    "_RowNumber": idx + 2,
                    "Original Form (CRF)": df.at[idx, CRF_COL],
                    "Variable Name": df.at[idx, VARIABLE_NAME_COLUMN],
                    "Original Proposed Match": orig,
                    "New Match": df.at[idx, MATCH_COL],
                    "Decision Type": meta["decision_type"],
                    "Decision Source": "auto"
                })
                discrepancies.append(row_dict)
                discrepancy_added = True

            # Push to history so undo can revert auto-apply too
            history.append({
                "idx": idx,
                "prev_match": prev_match,
                "key": key,
                "decision_type": meta.get("decision_type"),
                "discrepancy_added": discrepancy_added,
                "auto_applied": True
            })
            i += 1
            continue

        # prompt the user
        rationale = df.at[idx, RATIONALE_COL]
        var_name  = df.at[idx, VARIABLE_NAME_COLUMN]
        orig_form = df.at[idx, CRF_COL]
        print(f"Row {idx+2}:")
        print(f"  Original Form (CRF) → {orig_form}")
        print(f"  Variable Name      → {var_name}")
        print(f"  Canonical CRF Name → {canon}")
        # 🔽🔽🔽 Emphasized proposed match with arrow pointers
        print(f">>> PROPOSED MATCH: {orig} <<<")
        # 🔼🔼🔼
        print(f"  Rationale          → {rationale}\n")
        if not tip_shown:
            print("Tip: [y] keep, [n] set to 'No CRF match', [l] choose from list, [u] undo last, [s] skip the rest.\n")
            tip_shown = True

        orig_match = orig  # keep original proposed match for logging
        ans = input("Keep? [y]es / [n]o / [l]ist / [u]ndo last / [s]kip all: ").strip().lower()
        decision_type = None

        # UNDO: revert the previous decision and re-ask that previous row
        if ans == "u":
            if not history:
                print("⟲ Nothing to undo.\n")
                continue
            last = history.pop()
            # Revert the dataframe cell
            df.at[last["idx"], MATCH_COL] = last["prev_match"]

            # If we added a discrepancy for that action, remove the last one
            if last.get("discrepancy_added") and len(discrepancies) > 0:
                discrepancies.pop()

            # Also clear memoized decision for that key so it won't auto-apply again
            if last.get("key") in decisions:
                decisions.pop(last["key"], None)
                decisions_meta.pop(last["key"], None)

            # Move pointer back to that row
            try:
                i = to_check.index(last["idx"])
            except ValueError:
                i = max(i - 1, 0)

            print(f"⟲ Undid last action. Returning to row {to_check[i]+2}.\n")
            continue

        if ans == "s":
            print("⏭ Skipping the rest.")
            break
        elif ans == "y":
            choice = orig
            decision_type = "y"
        elif ans == "n":
            choice = None
            decision_type = "n"
        elif ans == "l":
            print("\nSelect from these CRF options:")
            for j, opt in enumerate(CRF_OPTIONS, 1):
                print(f"  {j}. {opt}")
            sel = input("Enter number (or 0 to cancel): ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(CRF_OPTIONS):
                choice = CRF_OPTIONS[int(sel) - 1]
                decision_type = "l"
            else:
                choice = None
                decision_type = "n"  # treat cancel as 'no'
        else:
            choice = None
            decision_type = "n"      # treat unknown input as 'no'

        # remember decision + metadata for auto-apply later
        decisions[key] = choice
        decisions_meta[key] = {"choice": choice, "decision_type": decision_type}

        # apply to df and print
        prev_match = df.at[idx, MATCH_COL]
        if choice is None:
            df.at[idx, MATCH_COL] = "No CRF match"
            print("✖ Marked as 'No CRF match'.\n")
        else:
            df.at[idx, MATCH_COL] = choice
            print(f"✔ Set match to '{choice}'.\n")

        # LOG the discrepancy if decision was n or l (entire row after edit)
        discrepancy_added = False
        if decision_type in {"n", "l"}:
            row_dict = df.loc[idx].to_dict()
            row_dict.update({
                "_RowNumber": idx + 2,
                "Original Form (CRF)": df.at[idx, CRF_COL],
                "Variable Name": var_name,
                "Original Proposed Match": orig_match,
                "New Match": df.at[idx, MATCH_COL],
                "Decision Type": decision_type,
                "Decision Source": "manual"
            })
            discrepancies.append(row_dict)
            discrepancy_added = True

        # push action to history so we can undo it
        history.append({
            "idx": idx,
            "prev_match": prev_match,
            "key": key,
            "decision_type": decision_type,
            "discrepancy_added": discrepancy_added,
            "auto_applied": False
        })

        # advance to next row
        i += 1

    # 3) Build Metadata sheet
    metadata_df = (
        df[[CRF_COL, CANONICAL_COL, RATIONALE_COL, FULL_RESPONSE_COL]]
        .drop_duplicates(subset=[CRF_COL, CANONICAL_COL])
        .reset_index(drop=True)
    )

    # 4) Build “wide” report of confirmed matches → linked sections
    grouped = (
        df[df[MATCH_COL].fillna("No CRF match") != "No CRF match"]
        .groupby(MATCH_COL)[CRF_COL]
        .apply(lambda s: sorted(s.unique()))
        .to_dict()
    )
    max_len = max((len(v) for v in grouped.values()), default=0)
    report_data = {m: vals + [""] * (max_len - len(vals)) for m, vals in grouped.items()}
    report_df = pd.DataFrame(report_data)

    # 5) Write all sheets (guarding Report + adding Discrepancies)
    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        # Always write EnhancedDD & Metadata
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)
        metadata_df.to_excel(writer, sheet_name="Metadata", index=False)

        ws_dd   = writer.sheets[SHEET_NAME]
        ws_meta = writer.sheets["Metadata"]

        # Format those two
        for ws, data in ((ws_dd, df), (ws_meta, metadata_df)):
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, data.shape[0], data.shape[1] - 1)
            for col_idx, col in enumerate(data.columns):
                width = max(data[col].astype(str).map(len).max(), len(col)) + 2
                ws.set_column(col_idx, col_idx, width)

        # Discrepancies sheet if any
        if len(discrepancies) > 0:
            discrepancies_df = pd.DataFrame(discrepancies)
            discrepancies_df.to_excel(writer, sheet_name="Discrepancies", index=False)
            ws_disc = writer.sheets["Discrepancies"]
            ws_disc.freeze_panes(1, 0)
            ws_disc.autofilter(0, 0, discrepancies_df.shape[0], discrepancies_df.shape[1] - 1)
            for col_idx, col in enumerate(discrepancies_df.columns):
                width = max(discrepancies_df[col].astype(str).map(len).max(), len(col)) + 2
                ws_disc.set_column(col_idx, col_idx, width)
        else:
            print("→ No Discrepancies sheet (no n/l overrides)")

        # Only write & format Report if it has at least one column
        if report_df.shape[1] > 0:
            report_df.to_excel(writer, sheet_name="Report", index=False)
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
