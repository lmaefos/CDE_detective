import json
import pandas as pd
from pathlib import Path

# Input JSON (relative to where you run the script)
in_path = Path("HDP00895_vlmd.json")

with open(in_path, "r", encoding="utf-8") as f:
    data = json.load(f)

fields = data.get("fields", data if isinstance(data, list) else [])

def flatten_field(item: dict) -> dict:
    row = {
        "name": item.get("name"),
        "description": item.get("description"),
    }

    # Keep other top-level keys (like enumLabels) as single-cell JSON strings
    for k, v in item.items():
        if k in {"name", "description", "constraints"}:
            continue
        row[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v

    # Flatten constraints (different vars can have different keys)
    constraints = item.get("constraints") or {}
    for ck, cv in constraints.items():
        if isinstance(cv, list):
            row[ck] = " | ".join(map(str, cv))  # enum lists
        elif isinstance(cv, dict):
            row[ck] = json.dumps(cv, ensure_ascii=False)
        else:
            row[ck] = cv

    return row

df = pd.DataFrame([flatten_field(x) for x in fields])

# Optional: ensure these columns exist
for c in ["minimum", "maximum", "enum", "enumLabels"]:
    if c not in df.columns:
        df[c] = pd.NA

df = df.rename(columns={"minimum": "min", "maximum": "max"})
df.insert(
    3,
    "range",
    df.apply(
        lambda r: f"{r['min']}–{r['max']}"
        if pd.notna(r["min"]) and pd.notna(r["max"])
        else pd.NA,
        axis=1,
    ),
)
df.insert(
    5,
    "enum_n",
    df["enum"].apply(
        lambda x: len(str(x).split(" | ")) if isinstance(x, str) and x.strip() else 0
    ),
)

# Output name matches input JSON name
out_path = in_path.with_suffix(".xlsx")

df.to_excel(out_path, index=False)
print(f"✅ Wrote: {out_path}")