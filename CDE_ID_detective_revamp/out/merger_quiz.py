import sys
import pandas as pd
from rapidfuzz import process, fuzz

# === CONFIG ===
INPUT_FILE = "HDP00066_ACTNOWOBOE_DataDictionary_REDCap.vlmd_2025-07-29.xlsx"
SHEET_NAME = "EnhancedDD"                    # Change to your sheet name!
FORM_COL = "section"            # Change to your column name!
DESCRIPTION_COL = "description"
CANONICAL_COL = "Canonical CRF Name"       # Change to your column name!
RATIONALE_COL = "Rationale"                # Change to your column name!
SIMILARITY_THRESHOLD = 70                  # Tune as needed (0-100)
# =============

import re

def normalize_crf_name(name):
    if not isinstance(name, str):
        return ""
    # Lowercase, remove underscores/dashes, collapse spaces, remove punctuation
    name = name.lower()
    name = re.sub(r"[_\-]", " ", name)
    name = re.sub(r"[^\w\s]", "", name)        # Remove punctuation except whitespace
    name = re.sub(r"\s+", " ", name)           # Collapse multiple spaces
    return name.strip()

def main():
    # Load data
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)
    forms = df[FORM_COL].unique()
    # Normalize all forms for matching, but keep the mapping to originals
    norm_forms = [normalize_crf_name(f) for f in forms]
    norm_to_original = dict(zip(norm_forms, forms))

    print(f"\nLoaded {len(forms)} unique forms.\n")

    # Find fuzzy matches based on normalized names
    matches = []
    checked_pairs = set()
    for i, norm_form in enumerate(norm_forms):
        for j, norm_other in enumerate(norm_forms):
            if i == j:
                continue
            pair = tuple(sorted([norm_form, norm_other]))
            if pair in checked_pairs:
                continue
            score = fuzz.token_sort_ratio(norm_form, norm_other)
            if score >= SIMILARITY_THRESHOLD:
                form = norm_to_original[norm_form]
                other = norm_to_original[norm_other]
                matches.append((form, other, score))
            checked_pairs.add(pair)
    
    # Quiz!
    confirmed_merges = []
    print(f"\n--- Interactive CRF Merge Quiz (Normalized, Threshold: {SIMILARITY_THRESHOLD}) ---\n")
    for form1, form2, score in matches:
        row1 = df[df[FORM_COL] == form1].iloc[0]
        row2 = df[df[FORM_COL] == form2].iloc[0]
        print(f"\nPotential match (Score: {score})")
        print(f"  1) {form1} | Canonical: {row1[CANONICAL_COL]}")
        print(f"     Description: {row1[DESCRIPTION_COL]}")
        print(f"     Rationale: {row1[RATIONALE_COL]}")
        print(f"  2) {form2} | Canonical: {row2[CANONICAL_COL]}")
        print(f"     Description: {row2[DESCRIPTION_COL]}")
        print(f"     Rationale: {row2[RATIONALE_COL]}")
        ans = input("\nCombine these? [y]es / [n]o / [c]ustom name / [s]kip all: ").strip().lower()
        if ans == "y":
            # Use form1's canonical as the merged name
            confirmed_merges.append((row1[CANONICAL_COL], row2[CANONICAL_COL], row1[CANONICAL_COL]))
        elif ans == "c":
            custom_name = input("Enter the desired merged canonical name: ").strip()
            confirmed_merges.append((row1[CANONICAL_COL], row2[CANONICAL_COL], custom_name))
        elif ans == "s":
            break
        # 'n' or any other input = skip

    # Output results
    if confirmed_merges:
        print("\nYou confirmed the following merges:")
        for a, b, newname in confirmed_merges:
            print(f"  - {a} <---> {b} => '{newname}'")
        # Save to file for downstream use
        pd.DataFrame(confirmed_merges, columns=["Canonical1", "Canonical2", "MergedName"]).to_csv("confirmed_merges.csv", index=False)
        print("Saved to confirmed_merges.csv!")
    else:
        print("No merges confirmed.")

if __name__ == "__main__":
    main()