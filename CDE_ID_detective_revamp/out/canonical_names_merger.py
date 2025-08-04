import os
import re
import pandas as pd
from rapidfuzz import fuzz
from xlsxwriter.utility import xl_rowcol_to_cell

# === CONFIG ===
INPUT_FILE           = "Testfile_2025-08-04.xlsx"
SHEET_NAME           = "EnhancedDD"
MATCH_COL            = "HEAL Core CRF Match"
DESCRIPTION_COL      = "description"
CANONICAL_COL        = "Canonical CRF Name"
RATIONALE_COL        = "Rationale"
CRF_COL              = "section"
FULL_RESPONSE_COL    = "Full Response"
MERGES_FILE          = "confirmed_merges.csv"  # optional CSV output
OUTPUT_FILE          = "Testfile_2025-08-04.xlsx"
SIMILARITY_THRESHOLD = 90


def normalize_crf_name(name: str) -> str:
    """Lowercase, strip punctuation/underscores, collapse spaces for fuzzy matching."""
    if not isinstance(name, str):
        return ""
    name = name.lower()
    name = re.sub(r"[_\-]", " ", name)
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def prettify_name(name: str) -> str:
    """Replace underscores/dashes with spaces, collapse double spaces, strip."""
    if not isinstance(name, str):
        return name
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def run_quiz(df: pd.DataFrame) -> pd.DataFrame:
    """
    Interactive merge quiz on unique canonical names.
    Returns a DataFrame of confirmed merges with columns:
      Canonical1, Canonical2, MergedName
    """
    # 1) unique canonicals
    canonicals = df[CANONICAL_COL].dropna().unique()
    # 2) normalize & map
    norm = [normalize_crf_name(c) for c in canonicals]
    norm_map = dict(zip(norm, canonicals))
    # 3) fuzzy-match pairs
    matches = []
    seen = set()
    for i, a in enumerate(norm):
        for j, b in enumerate(norm):
            if i >= j:
                continue
            pair = tuple(sorted([a, b]))
            if pair in seen:
                continue
            score = fuzz.token_sort_ratio(a, b)
            if score >= SIMILARITY_THRESHOLD:
                c1, c2 = norm_map[a], norm_map[b]
                matches.append((c1, c2, score))
            seen.add(pair)

    # 4) interactive quiz
    confirmed = []
    decisions = {}  # (c1, c2) -> merged_name or None
    print(f"\n--- Canonical-name Merge Quiz (Threshold: {SIMILARITY_THRESHOLD}) ---\n")
    for c1, c2, score in matches:
        key = (c1, c2)
        # auto-apply
        if key in decisions:
            merged = decisions[key]
            if merged:
                confirmed.append((c1, c2, merged))
                print(f"↪ Auto-merge {c1} ←→ {c2} → '{merged}'")
            else:
                print(f"↪ Auto-skip  {c1} ←→ {c2}")
            continue

        # prompt
        row1 = df[df[CANONICAL_COL] == c1].iloc[0]
        row2 = df[df[CANONICAL_COL] == c2].iloc[0]
        print(f"\nPotential match (Score: {score})")
        print(f"  1) Canonical: {c1}")
        print(f"     Description: {row1[DESCRIPTION_COL]}")
        print(f"     Rationale:   {row1[RATIONALE_COL]}")
        print(f"  2) Canonical: {c2}")
        print(f"     Description: {row2[DESCRIPTION_COL]}")
        print(f"     Rationale:   {row2[RATIONALE_COL]}")
        ans = input("\n[y]es / [n]o / [c]ustom / [s]kip all: ").strip().lower()
        if ans == "s":
            print("⏭ Skipping all remaining.")
            break
        if ans == "y":
            merged_name = c1
        elif ans == "c":
            merged_name = input("Enter custom merged name: ").strip()
        else:
            merged_name = None

        decisions[key] = merged_name
        if merged_name:
            confirmed.append((c1, c2, merged_name))
            print(f"✔ Scheduled merge as '{merged_name}'")
        else:
            print("✖ Skipping this pair")

    # build DataFrame
    merges_df = (
        pd.DataFrame(confirmed, columns=["Canonical1", "Canonical2", "MergedName"])
    )
    # optional CSV dump
    if not merges_df.empty:
        merges_df.to_csv(MERGES_FILE, index=False)
        print(f"\nSaved merge decisions to {MERGES_FILE}")
    else:
        print("\nNo merges confirmed.")

    return merges_df


def apply_merges(df: pd.DataFrame, merges_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply confirmed merges to df[CANONICAL_COL], prettify names,
    and return the updated DataFrame.
    """
    if not merges_df.empty:
        replace_map = {}
        for _, row in merges_df.iterrows():
            replace_map[row["Canonical1"]] = row["MergedName"]
            replace_map[row["Canonical2"]] = row["MergedName"]
        df[CANONICAL_COL] = df[CANONICAL_COL].replace(replace_map)
    else:
        print("→ No merges to apply, skipping replace step.")

    # prettify
    df[CANONICAL_COL] = df[CANONICAL_COL].apply(prettify_name)
    return df


def build_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Build the Metadata sheet (deduplicated)."""
    metadata_df = (
        df[[CRF_COL, CANONICAL_COL, RATIONALE_COL, FULL_RESPONSE_COL]]
        .drop_duplicates(subset=[CRF_COL, CANONICAL_COL])
        .reset_index(drop=True)
    )
    metadata_df[CANONICAL_COL] = metadata_df[CANONICAL_COL].apply(prettify_name)
    return metadata_df


def build_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a wide report: columns are HEAL Core CRF Match,
    rows list all 'section' values that match.
    """
    # group by match, list unique sections
    grouped = (
        df[df[MATCH_COL].fillna("No CRF match") != "No CRF match"]
        .groupby(MATCH_COL)[CRF_COL]
        .apply(lambda s: sorted(s.unique()))
        .to_dict()
    )

    # pad lists for uniform length
    max_len = max((len(v) for v in grouped.values()), default=0)
    report_data = {
        match: vals + [""] * (max_len - len(vals))
        for match, vals in grouped.items()
    }

    return pd.DataFrame(report_data)


def write_all(df: pd.DataFrame, metadata_df: pd.DataFrame, report_df: pd.DataFrame):
    """
    Write EnhancedDD, Metadata, and (optionally) Report sheets into one workbook,
    applying freeze panes, autofilter, and autofit.
    """
    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        # 1) Dump the two always-present sheets
        df.to_excel(writer,      sheet_name=SHEET_NAME, index=False)
        metadata_df.to_excel(writer, sheet_name="Metadata", index=False)

        wb      = writer.book
        ws_dd   = writer.sheets[SHEET_NAME]
        ws_meta = writer.sheets["Metadata"]

        # formatting helper
        def fmt_sheet(ws, data):
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, data.shape[0], data.shape[1] - 1)
            for col_idx, col in enumerate(data.columns):
                width = max(data[col].astype(str).map(len).max(), len(col)) + 2
                ws.set_column(col_idx, col_idx, width)

        # 2) Format EnhancedDD & Metadata
        fmt_sheet(ws_dd, df)
        fmt_sheet(ws_meta, metadata_df)

        # 3) Only write & format Report if it has at least one column
        if report_df.shape[1] > 0:
            ws_rep = report_df.to_excel(writer, sheet_name="Report", index=False)  # write it
            ws_rep = writer.sheets["Report"]
            fmt_sheet(ws_rep, report_df)
        else:
            print("→ Report sheet is empty; skipping it.")

    print(f"\n🎉 All done! Workbook saved as {OUTPUT_FILE}")

def main():
    # load
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    # run quiz & apply merges
    merges_df = run_quiz(df)
    df_merged = apply_merges(df, merges_df)

    # build downstream artifacts
    metadata_df = build_metadata(df_merged)
    report_df   = build_report(df_merged)

    # write out everything
    write_all(df_merged, metadata_df, report_df)


if __name__ == "__main__":
    main()
