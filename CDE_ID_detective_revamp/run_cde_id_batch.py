#!/usr/bin/env python3
"""
Batch runner for CDE_ID_revamp_v5.ipynb using papermill.

Reads one or more data-dictionary CSV files (as produced by
mds_export_data_dictionaries.py), executes the CDE-ID notebook for each one
via papermill, and writes one output Excel per file.

A run-report CSV is always written to <output_dir>/run_report.csv with one
row per file: status, timing, output path, and reason for any skips/errors.

Processing modes
----------------
    Default          Process every CSV in --input-dir.
    --new-only       Skip files that already have a reconciled output in
                     --output-dir (i.e. <stem>_cde_reconciled.xlsx exists).
    --single-file    Process one specific CSV instead of a directory.
                     Mutually exclusive with --input-dir.

Usage
-----
    # All files in a directory:
    python run_cde_id_batch.py --input-dir ~/Documents/HEAL/mds-dd-pull \\
                               --output-dir ~/Documents/HEAL/cde-results

    # Only files not yet processed:
    python run_cde_id_batch.py --input-dir ~/Documents/HEAL/mds-dd-pull \\
                               --output-dir ~/Documents/HEAL/cde-results \\
                               --new-only

    # One specific file:
    python run_cde_id_batch.py --single-file ~/Documents/HEAL/mds-dd-pull/abc123.csv \\
                               --output-dir ~/Documents/HEAL/cde-results

    # With an index.csv (limits scope to listed files):
    python run_cde_id_batch.py --input-dir ~/Documents/HEAL/mds-dd-pull \\
                               --index-csv  ~/Documents/HEAL/mds-dd-pull/index.csv \\
                               --output-dir ~/Documents/HEAL/cde-results \\
                               --max-files 10
"""

import configparser
import csv
from datetime import datetime
from pathlib import Path
import sys
import time

import click
import pandas as pd
import papermill as pm
from papermill.exceptions import PapermillExecutionError


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

class _TeeStream:
    """Write to two streams simultaneously (e.g. stdout + log file)."""
    def __init__(self, primary, secondary):
        self._primary = primary
        self._secondary = secondary

    def write(self, data):
        self._primary.write(data)
        self._secondary.write(data)
        return len(data) if isinstance(data, (bytes, str)) else 0

    def flush(self):
        self._primary.flush()
        self._secondary.flush()

    def isatty(self):
        return False

    def __getattr__(self, name):
        return getattr(self._primary, name)


_LOG_FILE = None  # set in main()


def tprint(msg=""):
    """Print with a timestamp prefix."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# ---------------------------------------------------------------------------
# Paths relative to this script
# ---------------------------------------------------------------------------

SCRIPT_DIR    = Path(__file__).parent.resolve()
NOTEBOOK_PATH = SCRIPT_DIR / "CDE_ID_revamp_v5.ipynb"
DEFAULT_CONFIG = SCRIPT_DIR / "config_prestep.ini"

REQUIRED_COLUMNS = {"section", "name", "description", "enumLabels"}
MIN_FIELDS = 3

# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------

def check_csv(csv_path: Path) -> tuple[bool, str, int]:
    """
    Quick preflight: check required columns and minimum field count.
    Returns (ok, reason, field_count).
    """
    try:
        df = pd.read_csv(csv_path, nrows=5)
    except Exception as e:
        return False, f"unreadable CSV: {e}", 0

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return False, f"missing columns: {sorted(missing)}", 0

    try:
        n = len(pd.read_csv(csv_path))
    except Exception:
        n = 0

    if n < MIN_FIELDS:
        return False, f"only {n} field(s) — below minimum {MIN_FIELDS}", n

    return True, "", n


def resolve_kb_paths(config_path: Path) -> dict[str, Path]:
    """
    Read config and resolve the three KnowledgeBase file paths,
    converting Windows backslashes so they work on macOS/Linux.
    """
    cfg = configparser.ConfigParser()
    cfg.read(config_path, encoding="utf-8")
    config_dir = config_path.parent

    def _abs(key: str, fallback: str) -> Path:
        raw = cfg.get("Files", key, fallback=fallback)
        return (config_dir / Path(raw.replace("\\", "/"))).resolve()

    return {
        "crf_json_path": _abs(
            "crf_json_path",
            "KnowledgeBase/CRF_descriptions.json",
        ),
        "kb_excel_path": _abs(
            "heal_cde_knowledge_base_file",
            "KnowledgeBase/Compiled_CORE_CDEs list_English_one sheet_as of 2025-01-28.xlsx",
        ),
        "kb_json_path": _abs(
            "KB_JSON_PATH",
            "KnowledgeBase/All_HEALPAINCDEsDD_row_level_flattened.json",
        ),
    }


# ---------------------------------------------------------------------------
# Single-file runner
# ---------------------------------------------------------------------------

def run_one_file(
    csv_path: Path,
    output_xlsx: Path,
    config_path: Path,
    env_path: Path,
    kb_paths: dict[str, Path],
    timeout_seconds: int = 7200,
    keep_notebook: bool = False,
) -> dict:
    """
    Execute the CDE-ID notebook for one CSV file via papermill.

    Returns a result dict with keys:
        status, elapsed_seconds, output_file, error
    """
    start = time.time()
    output_nb = output_xlsx.with_suffix(".ipynb")

    try:
        tprint("  Notebook params:")
        tprint(f"    config_path : {config_path}")
        tprint(f"    env_path    : {env_path}")
        tprint(f"    crf_json_path: {kb_paths.get('crf_json_path')}")
        tprint(f"    kb_excel_path: {kb_paths.get('kb_excel_path')}")
        tprint(f"    kb_json_path : {kb_paths.get('kb_json_path')}")
        tprint("  Starting notebook execution…")

        pm.execute_notebook(
            str(NOTEBOOK_PATH),
            str(output_nb),
            parameters={
                "input_file":    str(csv_path),
                "output_file":   str(output_xlsx),
                "config_path":   str(config_path),
                "env_path":      str(env_path),
                "crf_json_path": str(kb_paths["crf_json_path"]),
                "kb_excel_path": str(kb_paths["kb_excel_path"]),
                "kb_json_path":  str(kb_paths["kb_json_path"]),
            },
            kernel_name="heal-python3",
            cwd=str(SCRIPT_DIR),
            execution_timeout=timeout_seconds,
            log_output=True,   # stream notebook cell output to the console/log
            progress_bar=False,
        )
        tprint("  Notebook execution finished.")

        elapsed = round(time.time() - start, 1)

        # The notebook's export cell appends "_reconciled" to the stem.
        actual = output_xlsx.with_name(output_xlsx.stem + "_reconciled" + output_xlsx.suffix)
        found = actual if actual.exists() else (output_xlsx if output_xlsx.exists() else None)

        if found:
            return {"status": "success", "elapsed_seconds": elapsed,
                    "output_file": str(found), "error": ""}
        else:
            return {"status": "no_output", "elapsed_seconds": elapsed,
                    "output_file": "",
                    "error": "Notebook completed but output file was not created."}

    except PapermillExecutionError as e:
        return {"status": "error",
                "elapsed_seconds": round(time.time() - start, 1),
                "output_file": "",
                "error": str(e)[:2000]}

    except Exception as e:
        return {"status": "error",
                "elapsed_seconds": round(time.time() - start, 1),
                "output_file": "",
                "error": str(e)[:2000]}

    finally:
        if output_nb.exists() and not keep_notebook:
            try:
                output_nb.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

REPORT_COLUMNS = [
    "csv_file", "dd_guid", "dd_title", "field_count",
    "status", "start_time", "elapsed_seconds",
    "processing_seconds",
    "output_file", "skip_reason", "error_message",
]


def write_report(rows: list[dict], report_path: Path) -> None:
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nRun report → {report_path}  ({len(rows)} rows)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--input-dir", default=None,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Directory containing per-dd CSV files. Required unless --single-file is used.",
)
@click.option(
    "--single-file", default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Process a single CSV file. Mutually exclusive with --input-dir.",
)
@click.option(
    "--new-only", is_flag=True, default=False,
    help="Skip files that already have a reconciled output (<stem>_cde_reconciled.xlsx) "
         "in --output-dir. Ignored when --single-file is used.",
)
@click.option(
    "--output-dir", required=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Directory where output Excel files and the run report are written.",
)
@click.option(
    "--index-csv", default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Optional index.csv (from mds_export_data_dictionaries.py). "
         "When provided, only files listed there are processed.",
)
@click.option(
    "--config", "config_path",
    default=str(DEFAULT_CONFIG), show_default=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to config_prestep.ini.",
)
@click.option(
    "--env-file", "env_path", default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to .env file containing OPENAI_API_KEY. "
         "Defaults to <config-dir>/.env.",
)
@click.option(
    "--max-files", default=0, show_default=True,
    help="Stop after this many files (0 = unlimited).",
)
@click.option(
    "--timeout", default=7200, show_default=True,
    help="Per-cell timeout in seconds passed to papermill.",
)
@click.option(
    "--skip-errors/--no-skip-errors", default=True, show_default=True,
    help="Continue with remaining files after an error.",
)
@click.option(
    "--keep-notebooks", is_flag=True, default=False,
    help="Keep the executed .ipynb files alongside the Excel outputs "
         "(useful for debugging failures).",
)
def main(
    input_dir: Path | None,
    single_file: Path | None,
    new_only: bool,
    output_dir: Path,
    index_csv: Path | None,
    config_path: Path,
    env_path: Path | None,
    max_files: int,
    timeout: int,
    skip_errors: bool,
    keep_notebooks: bool,
) -> None:
    # --- validate mode ---
    if single_file and input_dir:
        print("Error: --single-file and --input-dir are mutually exclusive.", file=sys.stderr)
        sys.exit(1)
    if not single_file and not input_dir:
        print("Error: provide either --input-dir or --single-file.", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "run_report.csv"

    # --- set up tee logging (stdout + log file) ---
    global _LOG_FILE
    log_dir = output_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"run_{run_ts}.log"
    _LOG_FILE = open(log_path, "w", encoding="utf-8", buffering=1)  # line-buffered
    sys.stdout = _TeeStream(sys.__stdout__, _LOG_FILE)
    sys.stderr = _TeeStream(sys.__stderr__, _LOG_FILE)
    tprint(f"Log file  : {log_path}")

    # --- resolve and verify .env ---
    resolved_env = env_path or (config_path.parent / ".env")
    if not resolved_env.exists():
        print(
            f"Error: .env file not found at {resolved_env}\n"
            f"Create it with:  OPENAI_API_KEY=sk-...\n"
            f"              OPENAI_BASE_URL=https://...\n"
            f"Or pass --env-file /path/to/.env",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- verify notebook exists ---
    if not NOTEBOOK_PATH.exists():
        print(f"Error: notebook not found at {NOTEBOOK_PATH}", file=sys.stderr)
        sys.exit(1)

    # --- resolve KB paths once (from config, fixing Windows backslashes) ---
    kb_paths = resolve_kb_paths(config_path)
    missing_kb = [str(p) for p in kb_paths.values() if not p.exists()]
    if missing_kb:
        print("Error: KnowledgeBase files not found:", file=sys.stderr)
        for p in missing_kb:
            print(f"  {p}", file=sys.stderr)
        sys.exit(1)

    tprint(f"Notebook  : {NOTEBOOK_PATH}")
    tprint(f"Config    : {config_path}")
    tprint(f"Env file  : {resolved_env}")

    # --- build file list ---
    index_map: dict[str, dict] = {}
    csv_files: list[Path] = []

    if single_file:
        csv_files = [single_file]
    elif index_csv:
        idx_df = pd.read_csv(index_csv)
        for _, row in idx_df.iterrows():
            fname = str(row.get("csv_file", "")).strip()
            if fname:
                p = input_dir / fname
                if p.exists():
                    csv_files.append(p)
                    guid = str(row.get("dd_guid", p.stem)).strip()
                    index_map[p.stem] = {
                        "dd_guid": guid,
                        "dd_title": str(row.get("dd_title", "")).strip(),
                        "field_count": row.get("field_count", ""),
                    }
    else:
        csv_files = sorted(
            p for p in input_dir.glob("*.csv")
            if p.name not in {"index.csv", "run_report.csv"}
        )

    # --- --new-only: drop files that already have a reconciled output ---
    if new_only and not single_file:
        before = len(csv_files)
        csv_files = [
            p for p in csv_files
            if not (output_dir / f"{p.stem}_cde_reconciled.xlsx").exists()
        ]
        skipped_existing = before - len(csv_files)
        if skipped_existing:
            print(f"  --new-only: skipping {skipped_existing} already-processed file(s).")

    if max_files > 0:
        csv_files = csv_files[:max_files]

    mode_label = "single file" if single_file else ("new only" if new_only else "all")
    tprint(f"Mode      : {mode_label}")
    tprint(f"Files to process: {len(csv_files)}")

    # start batch timer
    batch_start = time.time()

    # --- process files ---
    report_rows: list[dict] = []
    success = skipped = errors = 0

    for i, csv_path in enumerate(csv_files, 1):
        guid = index_map.get(csv_path.stem, {}).get("dd_guid", csv_path.stem)
        title = index_map.get(csv_path.stem, {}).get("dd_title", "")
        start_time = datetime.now().isoformat(timespec="seconds")

        tprint(f"[{i}/{len(csv_files)}] {csv_path.name}")
        tprint(f"  guid : {guid}")
        if title:
            tprint(f"  title: {title[:60]}")

        ok, reason, field_count = check_csv(csv_path)
        if not ok:
            tprint(f"  SKIP: {reason}")
            report_rows.append({
                "csv_file": str(csv_path), "dd_guid": guid, "dd_title": title,
                "field_count": field_count, "status": "skipped",
                "start_time": start_time, "elapsed_seconds": 0,
                "processing_seconds": 0,
                "output_file": "", "skip_reason": reason, "error_message": "",
            })
            skipped += 1
            continue

        output_xlsx = output_dir / f"{csv_path.stem}_cde.xlsx"
        file_start = time.time()
        tprint(f"  Handing off to notebook…")
        result = run_one_file(
            csv_path, output_xlsx, config_path, resolved_env,
            kb_paths, timeout, keep_notebooks,
        )
        processing_seconds = round(time.time() - file_start, 1)

        status = result["status"]
        tprint(f"  status : {status}  ({result['elapsed_seconds']}s)")
        if result["error"]:
            tprint(f"  error  : {result['error'][:120]}")
        if result["output_file"]:
            tprint(f"  output : {result['output_file']}")

        report_rows.append({
            "csv_file": str(csv_path), "dd_guid": guid, "dd_title": title,
            "field_count": field_count, "status": status,
            "start_time": start_time, "elapsed_seconds": result["elapsed_seconds"],
            "processing_seconds": processing_seconds,
            "output_file": result["output_file"], "skip_reason": "",
            "error_message": result["error"],
        })

        if status == "success":
            success += 1
        else:
            errors += 1
            if not skip_errors:
                print("Stopping due to error (--no-skip-errors).")
                break

        write_report(report_rows, report_path)

    total = len(report_rows)
    batch_elapsed = round(time.time() - batch_start, 1)
    tprint(
        f"\n{'─'*60}\n"
        f"Finished.\n"
        f"  Total  : {total}\n"
        f"  Success: {success}\n"
        f"  Skipped: {skipped}\n"
        f"  Errors : {errors}\n"
        f"  Report : {report_path}\n"
        f"  Log    : {log_path}\n"
        f"  Total processing time: {batch_elapsed}s\n"
    )

    if _LOG_FILE:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        _LOG_FILE.close()


if __name__ == "__main__":
    main()
