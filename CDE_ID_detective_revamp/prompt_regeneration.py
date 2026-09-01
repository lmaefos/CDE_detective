"""Prompt regeneration for the CDE-ID pipeline.

Closes the loop between human review and the next batch run:

    all-outputs (predicted)  ─┐
                              ├─> classify ─> regenerate ─> config_prestep_vN.ini
    metadata (human-reviewed) ┘                             (pending review)

Design notes driven by the actual pipeline:

* There are four LLM stages, each with its own prompt under [Instructions] in
  config_prestep.ini. A correction must be attributed to the stage that caused
  it before any prompt is rewritten -- a wrong CDE caused by a wrong CRF two
  stages upstream must not trigger a rewrite of the recon prompt.

* Not every correction is prompt-fixable. Protected-family blocks and missing
  retrieval candidates are config or corpus problems. Rewriting prompt text for
  those produces noise, so they are classified out and reported separately.

* configparser dedents continuation lines, so the model receives a flat prompt.
  Writing back therefore has to re-indent, and must be a targeted text edit --
  configparser.write() would strip every comment in the file.
"""

from __future__ import annotations

import argparse
import configparser
import json
import re
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Protocol

import pandas as pd

# --------------------------------------------------------------------------
# Pipeline structure
# --------------------------------------------------------------------------

INSTRUCTIONS_SECTION = "Instructions"

# Prompt key -> the predicted column that stage is responsible for.
STAGE_OUTPUT = {
    "crf_id_prestep": "Refined CRF Name",
    "matching_instruction": "HEAL Core CRF Match",
    "recon_adjudication_instruction": "best_best_match_cde",
}
# form_harmonizer is excluded: it emits a clustering via function call, not a
# per-row decision, so row-level corrections cannot be attributed to it.

# --------------------------------------------------------------------------
# Review file schemas
# --------------------------------------------------------------------------
#
# Two layouts exist in the wild:
#
#   "metadata"  -- a sheet inside the reconciled workbook. Its column headers
#                  are misleading: "HEAL Core CRF Match" is NOT the matching
#                  stage's output, it mirrors best_best_match_crf (the CRF of
#                  the reconciled pick). Verified on HDP01340: 209/209 rows
#                  match best_best_match_crf, 70/209 disagree with the
#                  identically-named column in all-outputs. It carries only the
#                  reviewer's final state, so "did the reviewer change this?"
#                  has to be inferred by comparison.
#
#   "reviewed"  -- outputs/default/*_reviewed.xlsx. Carries _auto and _final
#                  pairs plus an explicit `corrected` flag, so no inference is
#                  needed. Prefer this when both are available.


@dataclass(frozen=True)
class ReviewSchema:
    name: str
    join_key: str
    pred_cde: str | None       # None -> take predicted side from the run file
    pred_crf: str | None
    final_cde: str
    final_crf: str
    corrected_flag: str | None = None
    label_col: str = ""          # independent column used to verify positional joins
    sheet: str | int = 0

    def present_in(self, columns) -> bool:
        cols = set(columns)
        required = {self.join_key, self.final_cde, self.final_crf}
        return required <= cols


SCHEMAS = [
    ReviewSchema(
        name="reviewed",
        join_key="variable_name",
        pred_cde="cde_name_auto",
        pred_crf="crf_name_auto",
        final_cde="cde_name_final",
        final_crf="crf_name_final",
        corrected_flag="corrected",
        label_col="label",
        sheet="Sheet1",
    ),
    ReviewSchema(
        name="metadata",
        join_key="Original Variable Name",
        pred_cde=None,
        pred_crf=None,
        final_cde="Best Match CDE Name",
        final_crf="HEAL Core CRF Match",   # actually best_best_match_crf
        corrected_flag=None,
        label_col="Original Variable Name",
        sheet="metadata",
    ),
]


def load_reviewed(path: Path) -> tuple[pd.DataFrame, ReviewSchema]:
    """Load a reviewed file under whichever schema it happens to use.

    Sheet names differ across pipeline generations, so detection is by column
    content rather than by sheet name.
    """
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        header = xl.parse(sheet, nrows=0)
        for schema in SCHEMAS:
            if schema.present_in(header.columns):
                return xl.parse(sheet), schema
    raise ValueError(
        f"{path.name}: no sheet matches a known review schema. "
        f"Sheets: {xl.sheet_names}. Expected columns for one of: "
        + "; ".join(f"{s.name} ({s.join_key}, {s.final_cde})" for s in SCHEMAS)
    )


# Run-file columns.
OUTPUT_JOIN_KEY = "name"
PRED_CRF = "best_best_match_crf"
PRED_CDE = "best_best_match_cde"
OUTPUT_LABEL = "title"                      # verifies positional alignment
MATCHING_STAGE_CRF = "HEAL Core CRF Match"  # the matching stage's actual output

CANDIDATE_COLUMNS = [
    "Best Match CDE Name",
    "Potential Match 2 - CDE Name",
    "Potential Match 3 - CDE Name",
]

# Substrings that must survive regeneration verbatim. The allowed-CRF list and
# the JSON output keys are contracts, not style.
INVARIANTS = {
    "matching_instruction": ["vs_67dbd4f7596c819192ddb860daafca24"],
    "recon_adjudication_instruction": [
        "best_best_match_cde",
        "best_best_match_crf",
        "best_best_match_variable",
        "recon_decision",
        "recon_confidence",
        "recon_rationale",
    ],
    "crf_id_prestep": ["CRF", "Rationale"],
}


class Cause(str, Enum):
    """Why the reviewer had to intervene."""

    PRESTEP = "prestep"                  # CRF identification was wrong
    MATCHING = "matching"                # HEAL Core CRF match was wrong
    RECON = "recon"                      # right candidates surfaced, wrong pick
    RETRIEVAL_GAP = "retrieval_gap"      # correct CDE never surfaced -- not prompt-fixable
    PROTECTED_FAMILY = "protected_family"  # guardrail blocked -- config, not prompt-fixable

    @property
    def prompt_fixable(self) -> bool:
        return self in {Cause.PRESTEP, Cause.MATCHING, Cause.RECON}

    @property
    def prompt_key(self) -> str | None:
        return {
            Cause.PRESTEP: "crf_id_prestep",
            Cause.MATCHING: "matching_instruction",
            Cause.RECON: "recon_adjudication_instruction",
        }.get(self)


@dataclass(frozen=True)
class Correction:
    variable: str
    section: str
    cause: Cause
    predicted_crf: str | None
    reviewed_crf: str | None
    predicted_cde: str | None
    reviewed_cde: str | None
    candidates: tuple[str, ...] = ()
    note: str | None = None

    def render(self) -> str:
        if self.cause is Cause.MATCHING:
            return f"- {self.variable} ({self.section}): CRF {self.predicted_crf!r} -> {self.reviewed_crf!r}"
        cands = ", ".join(c for c in self.candidates if c) or "none surfaced"
        return (
            f"- {self.variable} ({self.section}, CRF {self.reviewed_crf}): "
            f"picked {self.predicted_cde!r} -> should be {self.reviewed_cde!r} "
            f"[candidates: {cands}]"
        )


@dataclass
class PromptVersion:
    key: str
    version: int
    text: str
    parent_version: int | None = None
    rationale: str = ""
    n_corrections: int = 0
    status: str = "pending_review"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )


class LLM(Protocol):
    def __call__(self, system: str, user: str) -> str: ...


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------


def _clean(v) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s or None


def _norm(v: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (v or "").lower())


def classify(pred, rev, schema: ReviewSchema) -> Correction | None:
    """Attribute one reviewed row to the stage that caused the error.

    When the review file carries its own _auto columns, those are the model's
    proposal exactly as the reviewer saw it, so use them. Otherwise the
    predicted side comes from the run file.
    """
    rev_crf = _clean(rev.get(schema.final_crf))
    rev_cde = _clean(rev.get(schema.final_cde))
    pred_crf = _clean(rev.get(schema.pred_crf)) if schema.pred_crf else _clean(pred.get(PRED_CRF))
    pred_cde = _clean(rev.get(schema.pred_cde)) if schema.pred_cde else _clean(pred.get(PRED_CDE))
    candidates = tuple(c for c in (_clean(pred.get(col)) for col in CANDIDATE_COLUMNS) if c)

    changed = _norm(pred_crf) != _norm(rev_crf) or _norm(pred_cde) != _norm(rev_cde)

    # An explicit reviewer flag beats inference, but a flag with no visible
    # change means they touched something this module cannot see -- skip it
    # rather than emit a correction whose before and after are identical.
    if schema.corrected_flag and schema.corrected_flag in rev.index:
        if not _truthy(rev.get(schema.corrected_flag)) or not changed:
            return None
    elif not changed:
        return None

    flag = _clean(pred.get("recon_review_flag"))
    protected = _clean(pred.get("Protected Family Rule Applied"))
    stage_crf = _clean(pred.get(MATCHING_STAGE_CRF))
    refined = _clean(pred.get("Refined CRF Name"))
    in_candidates = bool(rev_cde) and any(_norm(rev_cde) == _norm(c) for c in candidates)

    if (flag and "protected family" in flag.lower()) or (protected or "").lower() == "yes":
        cause = Cause.PROTECTED_FAMILY
    elif in_candidates:
        # The right answer was on the table and recon passed it over.
        cause = Cause.RECON
    elif (
        rev_crf
        and stage_crf
        and _norm(rev_crf) != _norm(pred_crf)      # reviewer actually moved the CRF
        and _norm(rev_crf) != _norm(stage_crf)
    ):
        # Wrong CRF upstream -> wrong candidate pool. Blame the prestep only if
        # it also got the CRF wrong; otherwise matching lost a correct prestep.
        cause = Cause.PRESTEP if _norm(refined) != _norm(rev_crf) else Cause.MATCHING
    else:
        cause = Cause.RETRIEVAL_GAP

    return Correction(
        variable=str(rev.get(schema.join_key)),
        section=_clean(pred.get("section")) or "",
        cause=cause,
        predicted_crf=pred_crf,
        reviewed_crf=rev_crf,
        predicted_cde=pred_cde,
        reviewed_cde=rev_cde,
        candidates=candidates,
        note=flag,
    )


def _truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "yes", "y", "1", "1.0", "x"}


def diff_run(
    outputs: pd.DataFrame,
    reviewed: pd.DataFrame,
    schema: ReviewSchema,
) -> list[Correction]:
    """Compare a completed run against the reviewer's corrected file.

    Joins on the schema's key when it lines up. Some review files use surrogate
    row IDs (var_0, var_1, ...) that never match the run file's variable names;
    for those, fall back to a positional join, but only after verifying row
    order with an independent column. Silently mismatching rows here would
    poison every downstream correction, so an unverifiable fallback raises.
    """
    keys = reviewed[schema.join_key].astype(str)
    by_name = {str(r[OUTPUT_JOIN_KEY]): r for _, r in outputs.iterrows()}
    overlap = sum(1 for k in keys if k in by_name)

    if overlap == 0:
        if len(reviewed) != len(outputs):
            raise ValueError(
                f"join key {schema.join_key!r} matches nothing and row counts "
                f"differ ({len(reviewed)} reviewed vs {len(outputs)} run) -- "
                "cannot align these files"
            )
        agree = (
            reviewed[schema.label_col].astype(str).values
            == outputs[OUTPUT_LABEL].astype(str).values
        ).sum()
        if agree < len(reviewed):
            raise ValueError(
                f"join key {schema.join_key!r} matches nothing and positional "
                f"alignment is unverified ({agree}/{len(reviewed)} labels agree)"
            )
        print(f"  joining positionally ({agree}/{len(reviewed)} labels agree)")
        pairs = zip(
            (r for _, r in outputs.iterrows()),
            (r for _, r in reviewed.iterrows()),
        )
    else:
        if overlap < len(reviewed):
            print(f"  warning: {len(reviewed) - overlap} reviewed rows had no match")
        pairs = (
            (by_name[str(rev[schema.join_key])], rev)
            for _, rev in reviewed.iterrows()
            if str(rev[schema.join_key]) in by_name
        )

    return [c for pred, rev in pairs if (c := classify(pred, rev, schema))]


def group_by_stage(corrections: list[Correction]) -> dict[str, list[Correction]]:
    out: dict[str, list[Correction]] = {}
    for c in corrections:
        if c.cause.prompt_fixable:
            out.setdefault(c.cause.prompt_key, []).append(c)
    return out


# --------------------------------------------------------------------------
# Regeneration
# --------------------------------------------------------------------------

SYSTEM = """You are improving one prompt used by an automated pipeline that maps \
study data-dictionary variables to HEAL Common Data Elements.

You will receive the current prompt for a single pipeline stage and a list of \
decisions a human data steward corrected at that stage. Rewrite the prompt so \
the same class of error is less likely.

Hard rules:
- Preserve the output contract exactly: the same JSON keys, the same allowed \
values, the same "return only JSON" instruction.
- Preserve any enumerated list of allowed CRF names verbatim. Never add, remove, \
or reword an entry in that list.
- Preserve any vector store ID verbatim.
- Generalize. Encode the rule the reviewer was applying, not the specific \
variable names you were shown.
- Prefer sharpening existing guidance over appending new rules. Do not let the \
prompt grow without bound.
- Output plain text with no markdown formatting or backticks.

Return JSON only:
{"prompt": "<full rewritten prompt>", "rationale": "<2-3 sentences on what changed and why>"}
"""

USER_TEMPLATE = """PIPELINE STAGE: {key}

CURRENT PROMPT
---
{current}
---

CORRECTIONS AT THIS STAGE ({n})
{corrections}
"""


def _parse_json(raw: str) -> dict:
    text = re.sub(r"^\s*```(?:json)?|```\s*$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned non-JSON: {raw[:300]}") from exc


def check_invariants(key: str, old: str, new: str) -> list[str]:
    """Return a list of contract violations; empty means the rewrite is safe."""
    problems = []
    for token in INVARIANTS.get(key, []):
        if token in old and token not in new:
            problems.append(f"dropped required token: {token}")

    # The allowed-CRF list in matching_instruction is a hard contract.
    if key == "matching_instruction":
        old_crfs = set(re.findall(r"^\s*-\s+([A-Z][^\n]*)$", old, re.MULTILINE))
        new_crfs = set(re.findall(r"^\s*-\s+([A-Z][^\n]*)$", new, re.MULTILINE))
        if missing := old_crfs - new_crfs:
            problems.append(f"removed {len(missing)} allowed-CRF entries")
    return problems


def regenerate(
    key: str,
    current: str,
    corrections: list[Correction],
    llm: LLM,
    min_corrections: int = 5,
    max_shown: int = 30,
) -> tuple[str, str] | None:
    """Return (new_prompt, rationale), or None if nothing should change."""
    if len(corrections) < min_corrections:
        return None

    shown = corrections[:max_shown]
    body = "\n".join(c.render() for c in shown)
    if len(corrections) > max_shown:
        body += f"\n- ...and {len(corrections) - max_shown} more of the same shape"

    payload = _parse_json(
        llm(
            system=SYSTEM,
            user=USER_TEMPLATE.format(
                key=key, current=current, n=len(corrections), corrections=body
            ),
        )
    )
    new_text = payload["prompt"].strip()

    if new_text == current.strip():
        return None
    if problems := check_invariants(key, current, new_text):
        raise ValueError(f"Rejected rewrite of {key}: {'; '.join(problems)}")

    return new_text, payload.get("rationale", "")


# --------------------------------------------------------------------------
# Reading and writing config_prestep.ini
# --------------------------------------------------------------------------


def read_instructions(ini_path: Path) -> dict[str, str]:
    cp = configparser.ConfigParser()
    cp.read(ini_path, encoding="utf-8")
    return dict(cp[INSTRUCTIONS_SECTION])


def _reindent(text: str, indent: str = "    ") -> str:
    """Re-indent continuation lines so the ini stays parseable."""
    lines = text.strip().splitlines()
    if not lines:
        return ""
    return "\n".join([lines[0].strip()] + [indent + ln.strip() for ln in lines[1:]])


def write_instruction(ini_path: Path, key: str, new_text: str) -> None:
    """Replace one key's value in place, preserving comments and every other line."""
    raw = ini_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"^({re.escape(key)}\s*=\s*)(.*?)(?=^\S|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    if not pattern.search(raw):
        raise KeyError(f"{key} not found in {ini_path}")
    replacement = f"{key} = {_reindent(new_text)}\n"
    ini_path.write_text(pattern.sub(lambda m: replacement, raw, count=1), encoding="utf-8")


def next_version(store: Path) -> int:
    existing = [int(m.group(1)) for p in store.glob("config_prestep_v*.ini")
                if (m := re.search(r"_v(\d+)\.ini$", p.name))]
    return max(existing, default=0) + 1


def save_candidate(
    store: Path,
    live_ini: Path,
    edits: dict[str, tuple[str, str]],
    corrections: list[Correction],
) -> Path:
    """Write a new versioned ini with the accepted rewrites applied."""
    store.mkdir(parents=True, exist_ok=True)
    version = next_version(store)
    out = store / f"config_prestep_v{version}.ini"
    shutil.copy(live_ini, out)

    versions = []
    for key, (text, rationale) in edits.items():
        write_instruction(out, key, text)
        versions.append(
            PromptVersion(
                key=key,
                version=version,
                text=text,
                rationale=rationale,
                n_corrections=sum(1 for c in corrections if c.cause.prompt_key == key),
            )
        )

    (store / f"config_prestep_v{version}.meta.json").write_text(
        json.dumps(
            {
                "version": version,
                "source": str(live_ini),
                "prompts": [asdict(v) | {"text": "<in ini>"} for v in versions],
                "corrections": [asdict(c) | {"cause": c.cause.value} for c in corrections],
            },
            indent=2,
        )
    )
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Regenerate CDE-ID prompts from human review.")
    ap.add_argument("--run", type=Path, required=True, help="Completed run xlsx (all-outputs)")
    ap.add_argument("--reviewed", type=Path, required=True, help="Reviewed xlsx (metadata sheet)")
    ap.add_argument("--ini", type=Path, default=Path("config_prestep.ini"))
    ap.add_argument("--store", type=Path, default=Path("prompts"))
    ap.add_argument("--min-corrections", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    for p in (args.run, args.reviewed, args.ini):
        if not p.is_file():
            ap.error(f"not a file: {p}")

    outputs = pd.read_excel(args.run, sheet_name="all-outputs")
    reviewed, schema = load_reviewed(args.reviewed)
    print(f"review schema: {schema.name} ({len(reviewed)} rows)")

    corrections = diff_run(outputs, reviewed, schema)
    counts: dict[str, int] = {}
    for c in corrections:
        counts[c.cause.value] = counts.get(c.cause.value, 0) + 1
    print(f"{len(corrections)} corrections: {counts or '{}'}")

    for cause in (Cause.RETRIEVAL_GAP, Cause.PROTECTED_FAMILY):
        if n := counts.get(cause.value):
            where = "the KB / retrieval corpus" if cause is Cause.RETRIEVAL_GAP else "[ProtectedPrimaryFamilies]"
            print(f"  {n} not prompt-fixable ({cause.value}) -- look at {where}")

    instructions = read_instructions(args.ini)
    edits: dict[str, tuple[str, str]] = {}
    for key, group in group_by_stage(corrections).items():
        result = regenerate(key, instructions[key], group, _default_llm(), args.min_corrections)
        if result is None:
            print(f"  {key}: {len(group)} corrections, no rewrite")
            continue
        edits[key] = result
        print(f"  {key}: rewritten from {len(group)} corrections")

    if not edits:
        print("Nothing to regenerate.")
        return 0
    if args.dry_run:
        for key, (text, rationale) in edits.items():
            print(f"\n=== {key} ===\n{rationale}\n---\n{text}")
        return 0

    path = save_candidate(args.store, args.ini, edits, corrections)
    print(f"Wrote {path} (pending review -- diff it before promoting)")
    return 0


def _default_llm() -> LLM:
    def call(system: str, user: str) -> str:  # pragma: no cover
        raise NotImplementedError(
            "Wire this to the client run_cde_id_batch.py already uses "
            "(model from [Models]), or pass llm= to regenerate()."
        )

    return call


if __name__ == "__main__":
    raise SystemExit(main())
