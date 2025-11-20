import os
import pandas as pd
import textwrap

# === CONFIG ===
INPUT_FILE            = "PRECICEV2_DataDictionary_2023-08-11_2025-11-20.xlsx"
SHEET_NAME            = "EnhancedDD"            # autopopulated from output
MATCH_COL             = "HEAL Core CRF Match"   # autopopulated from output
RATIONALE_COL         = "Rationale"             # autopopulated from output
CANONICAL_COL         = "Canonical CRF Name"    # autopopulated from output
FULL_RESPONSE_COL     = "Full Response"         # autopopulated from output
CRF_COL               = "Form Name"               # original CRF name
VARIABLE_NAME_COLUMN  = "Variable / Field Name"                  # original variable name
DESCRIPTION_COL       = "Field Label"           # original variable description column name
OUTPUT_FILE           = "PRECICEV2_DataDictionary_2023-08-11_2025-11-20_matches confirmed.xlsx"

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

def review_acronym_groups(df):
    """
    Human-in-the-loop step:
    - Groups rows by 'CDE Acronym Finder'
    - Lets the user choose the correct instrument version
    - If chosen, auto-applies that version to:
        - CDE Acronym Version
        - HEAL Core CRF Match  (!!! NEW !!!)
    - If 'not grouped', leave rows untouched for manual review
    - Returns:
        df, acronym_report_df
    """

    if "CDE Acronym Finder" not in df.columns:
        print("⚠️  No 'CDE Acronym Finder' column found. Skipping acronym review.\n")
        return df, None

    # Ensure columns exist
    if "CDE Acronym Version" not in df.columns:
        df["CDE Acronym Version"] = pd.NA
    if "HEAL Core CRF Match" not in df.columns:
        df["HEAL Core CRF Match"] = "No CRF match"

    acronym_report_rows = []

    grouped = df.groupby("CDE Acronym Finder", dropna=True)

    for acronym, sub in grouped:

        if not isinstance(acronym, str) or acronym.strip() == "":
            continue
        if len(sub) <= 1:
            continue

        print("\n" + "=" * 55)
        print(f"ACRONYM GROUP: {acronym}   ({len(sub)} rows)")
        print("=" * 55)

        # Show group
        for idx in sub.index:
            row_num = idx + 2
            var_name = df.at[idx, VARIABLE_NAME_COLUMN]
            desc = str(df.at[idx, DESCRIPTION_COL])
            desc_snippet = desc[:80] + "..." if len(desc) > 80 else desc
            print(f"Row {row_num:<4} | {var_name:<20} | {desc_snippet}")

        # Find matching options for this acronym
        matching_opts = [opt for opt in CRF_OPTIONS if acronym.lower() in opt.lower()]

        if matching_opts:
            print(f"\nPossible HEAL CDE versions for acronym '{acronym}':")
            for j, opt in enumerate(matching_opts, 1):
                print(f"  {j}. {opt}")
            print("  0. These are NOT all from the same questionnaire")

            # Input loop
            while True:
                sel = input(f"\nEnter choice [0-{len(matching_opts)}]: ").strip()
                if sel == "":
                    sel = "0"
                if sel.isdigit() and 0 <= int(sel) <= len(matching_opts):
                    sel_int = int(sel)
                    break
                print("Invalid choice. Try again.")

            # NEW: When a version is chosen
            if sel_int != 0:
                chosen_version = matching_opts[sel_int - 1]
                print(f"\n🌟 Applying version '{chosen_version}' to this entire group.\n")

                # NEW — update both fields:
                df.loc[sub.index, "CDE Acronym Version"] = chosen_version
                df.loc[sub.index, MATCH_COL] = chosen_version  # <- THIS SETS HEAL CORE CRF MATCH

                # add to report
                for idx in sub.index:
                    acronym_report_rows.append({
                        "Acronym": acronym,
                        "RowNumber": idx + 2,
                        "Variable Name": df.at[idx, VARIABLE_NAME_COLUMN],
                        "Description": df.at[idx, DESCRIPTION_COL],
                        "Applied Version": chosen_version
                    })

                input("Press Enter to continue...\n")
                continue

            # NOT grouped
            else:
                print(f"→ '{acronym}' group marked as NOT grouped.\n")
                for idx in sub.index:
                    acronym_report_rows.append({
                        "Acronym": acronym,
                        "RowNumber": idx + 2,
                        "Variable Name": df.at[idx, VARIABLE_NAME_COLUMN],
                        "Description": df.at[idx, DESCRIPTION_COL],
                        "Applied Version": None
                    })
                input("Press Enter to continue...\n")

        else:
            print(f"⚠️ No HEAL CDE mapping options found for {acronym}.\n")
            for idx in sub.index:
                acronym_report_rows.append({
                    "Acronym": acronym,
                    "RowNumber": idx + 2,
                    "Variable Name": df.at[idx, VARIABLE_NAME_COLUMN],
                    "Description": df.at[idx, DESCRIPTION_COL],
                    "Applied Version": None
                })
            input("Press Enter to continue...\n")

    acronym_report_df = pd.DataFrame(acronym_report_rows) if acronym_report_rows else None
    return df, acronym_report_df

def main():
    # 1) Load sheet
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    # ----------------------------------------------------
    # STEP 1: Human-in-the-loop acronym group review
    # ----------------------------------------------------
    df, acronym_report_df = review_acronym_groups(df)

    # ----------------------------------------------------
    # STEP 2: Build the list of rows needing manual review
    # (Skip auto-confirmed rows from Step 1)
    # ----------------------------------------------------
    if "CDE Acronym Version" not in df.columns:
        df["CDE Acronym Version"] = pd.NA  # ensure column exists

    to_check = df[
        (df[MATCH_COL].fillna("No CRF match") != "No CRF match") &
        (df["CDE Acronym Version"].isna())   # skip rows auto-confirmed in Step 1
    ].index.tolist()

    decisions = {}          # (canon, orig) -> choice (str or None)
    decisions_meta = {}     # (canon, orig) -> {"choice": str|None, "decision_type": "y"|"n"|"l"}
    discrepancies = []      # list of full-row dicts with metadata

    history = []            # undo stack

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

        rationale   = df.at[idx, RATIONALE_COL]
        description = df.at[idx, DESCRIPTION_COL]
        var_name    = df.at[idx, VARIABLE_NAME_COLUMN]
        orig_form   = df.at[idx, CRF_COL]

        wrapped_desc = "\n       ".join(textwrap.wrap(str(description), width=90))
        wrapped_rat  = "\n       ".join(textwrap.wrap(str(rationale),   width=90))

        print(f"Row {idx+2}:")
        print(f"  Original Form (CRF) → {orig_form}")
        print(f"  Variable Name      → {var_name}")
        print(f"  Description        → {wrapped_desc}")
        print(f"  Canonical CRF Name → {canon}")
        print(f">>> PROPOSED MATCH: {orig} <<<")
        print(f"  Rationale          → {wrapped_rat}\n")

        if not tip_shown:
            print("Tip: [y] keep, [n] set to 'No CRF match', [l] choose from list, [u] undo last, [s] skip the rest.\n")
            tip_shown = True

        orig_match = orig
        ans = input("Keep? [y]es / [n]o / [l]ist / [u]ndo last / [s]kip all: ").strip().lower()
        decision_type = None

        # UNDO
        if ans == "u":
            if not history:
                print("⟲ Nothing to undo.\n")
                continue
            last = history.pop()
            df.at[last["idx"], MATCH_COL] = last["prev_match"]

            if last.get("discrepancy_added") and len(discrepancies) > 0:
                discrepancies.pop()

            if last.get("key") in decisions:
                decisions.pop(last["key"], None)
                decisions_meta.pop(last["key"], None)

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
                decision_type = "n"
        else:
            choice = None
            decision_type = "n"

        decisions[key] = choice
        decisions_meta[key] = {"choice": choice, "decision_type": decision_type}

        prev_match = df.at[idx, MATCH_COL]
        if choice is None:
            df.at[idx, MATCH_COL] = "No CRF match"
            print("✖ Marked as 'No CRF match'.\n")
        else:
            df.at[idx, MATCH_COL] = choice
            print(f"✔ Set match to '{choice}'.\n")

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

        history.append({
            "idx": idx,
            "prev_match": prev_match,
            "key": key,
            "decision_type": decision_type,
            "discrepancy_added": discrepancy_added,
            "auto_applied": False
        })

        i += 1

    # 3) Build Metadata sheet
    metadata_df = (
        df[[CRF_COL, CANONICAL_COL, RATIONALE_COL, FULL_RESPONSE_COL]]
        .drop_duplicates(subset=[CRF_COL, CANONICAL_COL])
        .reset_index(drop=True)
    )

    # 4) Build wide Report
    grouped = (
        df[df[MATCH_COL].fillna("No CRF match") != "No CRF match"]
        .groupby(MATCH_COL)[CRF_COL]
        .apply(lambda s: sorted(s.unique()))
        .to_dict()
    )
    max_len = max((len(v) for v in grouped.values()), default=0)
    report_data = {m: vals + [""] * (max_len - len(vals)) for m, vals in grouped.items()}
    report_df = pd.DataFrame(report_data)

    # 5) Write all sheets
    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)
        metadata_df.to_excel(writer, sheet_name="Metadata", index=False)

        ws_dd   = writer.sheets[SHEET_NAME]
        ws_meta = writer.sheets["Metadata"]

        for ws, data in ((ws_dd, df), (ws_meta, metadata_df)):
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, data.shape[0], data.shape[1] - 1)
            for col_idx, col in enumerate(data.columns):
                width = max(data[col].astype(str).map(len).max(), len(col)) + 2
                ws.set_column(col_idx, col_idx, width)

        # NEW: AcronymGroups sheet, if we built one
        if acronym_report_df is not None and not acronym_report_df.empty:
            acronym_report_df.to_excel(writer, sheet_name="AcronymGroups", index=False)
            ws_acr = writer.sheets["AcronymGroups"]
            ws_acr.freeze_panes(1, 0)
            ws_acr.autofilter(0, 0, acronym_report_df.shape[0], acronym_report_df.shape[1] - 1)
            for col_idx, col in enumerate(acronym_report_df.columns):
                width = max(acronym_report_df[col].astype(str).map(len).max(), len(col)) + 2
                ws_acr.set_column(col_idx, col_idx, width)

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
