import sys
import pandas as pd
from rapidfuzz import fuzz
import re

# === CONFIG ===
INPUT_FILE           = "HDP00110_PRECICEV2_DataDictionary_2023-08-11.vlmd_2025-07-30.xlsx"
SHEET_NAME           = "EnhancedDD"
DESCRIPTION_COL      = "description"
CANONICAL_COL        = "Canonical CRF Name"
RATIONALE_COL        = "Rationale"
SIMILARITY_THRESHOLD = 90
# =============

def normalize_crf_name(name):
    if not isinstance(name, str):
        return ""
    name = name.lower()
    name = re.sub(r"[_\-]", " ", name)
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()

def main():
    # 1) load full sheet
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    # 2) grab every unique Canonical CRF Name
    canonicals = df[CANONICAL_COL].dropna().unique()

    # 3) normalize and map back to originals
    norm_cans = [normalize_crf_name(c) for c in canonicals]
    norm_to_original = dict(zip(norm_cans, canonicals))

    # 4) find fuzzy matches between normalized canonical names
    matches = []
    seen = set()
    for i, a in enumerate(norm_cans):
        for j, b in enumerate(norm_cans):
            if i >= j:
                continue
            pair = tuple(sorted([a, b]))
            if pair in seen:
                continue
            score = fuzz.token_sort_ratio(a, b)
            if score >= SIMILARITY_THRESHOLD:
                c1 = norm_to_original[a]
                c2 = norm_to_original[b]
                matches.append((c1, c2, score))
            seen.add(pair)

    # 5) interactive quiz with auto-apply cache
    confirmed_merges = []
    decisions = {}  # key=(canon1,canon2) -> mergedName or None for “no”

    print(f"\n--- Interactive Canonical-name Merge Quiz (Threshold: {SIMILARITY_THRESHOLD}) ---\n")
    for c1, c2, score in matches:
        key = (c1, c2)

        # auto-apply if we’ve seen it
        if key in decisions:
            merged = decisions[key]
            if merged:
                confirmed_merges.append((c1, c2, merged))
                print(f"↪ Auto-merge {c1} ←→ {c2} → '{merged}'\n")
            else:
                print(f"↪ Auto-skip {c1} ←→ {c2}\n")
            continue

        # first time: pull the first row for each canonical to show details
        row1 = df[df[CANONICAL_COL] == c1].iloc[0]
        row2 = df[df[CANONICAL_COL] == c2].iloc[0]

        print(f"Potential match (Score: {score})")
        print(f"  1) Canonical: {c1}")
        print(f"     Description: {row1[DESCRIPTION_COL]}")
        print(f"     Rationale:   {row1[RATIONALE_COL]}")
        print(f"  2) Canonical: {c2}")
        print(f"     Description: {row2[DESCRIPTION_COL]}")
        print(f"     Rationale:   {row2[RATIONALE_COL]}\n")

        ans = input("[y]es / [n]o / [c]ustom name / [s]kip all: ").strip().lower()
        if ans == "s":
            print("⏭  Skipping the rest.")
            break

        if ans == "y":
            merged_name = c1
        elif ans == "c":
            merged_name = input("Enter the merged canonical name: ").strip()
        else:
            merged_name = None

        decisions[key] = merged_name
        if merged_name:
            confirmed_merges.append((c1, c2, merged_name))
            print(f"✔  Will merge as '{merged_name}'.\n")
        else:
            print("✖  Will skip this pair.\n")

    # 6) write out confirmed merges
    if confirmed_merges:
        print("\nYou confirmed these merges:")
        for a, b, m in confirmed_merges:
            print(f"  - {a} ←→ {b} ⇒ '{m}'")
        pd.DataFrame(
            confirmed_merges,
            columns=["Canonical1", "Canonical2", "MergedName"]
        ).to_csv("confirmed_merges.csv", index=False)
        print("\nSaved to confirmed_merges.csv")
    else:
        print("No merges confirmed.")

if __name__ == "__main__":
    main()
