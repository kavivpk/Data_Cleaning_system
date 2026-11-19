"""
run_pipeline.py - Master End-to-End Orchestrator

Project: Data Cleaning and Preprocessing System
Description: Executes the full data processing pipeline across all phases in sequence:
               1. Phase 2: Raw Dataset Verification / Generation
               2. Phase 3: Data Cleaning (Deduplication, Imputation, Typing)
               3. Phase 4: Data Standardization (snake_case, Text Casing, Categories)
               4. Phase 5: Data Validation & QA (Rules, Scores, Issue Logging)
               5. Phase 6: Final Deliverables (CSV, Excel Workbook, Consolidated Report)
             Stops immediately on error, reports execution time, and validates integrity.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


# Pipeline stages definitions
PIPELINE_STAGES = [
    {
        "phase": "Phase 2",
        "name": "Dataset Generation & Verification",
        "script": "generate_dataset.py",
        "expected_output": Path("data/raw/sales_dirty.csv")
    },
    {
        "phase": "Phase 3",
        "name": "Data Cleaning",
        "script": "clean_data.py",
        "expected_output": Path("data/cleaned/sales_cleaned.csv")
    },
    {
        "phase": "Phase 4",
        "name": "Data Standardization",
        "script": "standardize_data.py",
        "expected_output": Path("data/standardized/sales_standardized.csv")
    },
    {
        "phase": "Phase 5",
        "name": "Data Validation & QA",
        "script": "validate_data.py",
        "expected_output": Path("data/validated/validation_issues.csv")
    },
    {
        "phase": "Phase 6",
        "name": "Final Deliverables & Documentation",
        "script": "export_final.py",
        "expected_output": Path("data/final/sales_final.csv")
    }
]


def run_stage(stage: Dict[str, Any], project_root: Path) -> Tuple[bool, float, str]:
    """
    Execute a single pipeline stage in a dedicated subprocess.

    Parameters:
        stage (Dict[str, Any]): Stage definition dict.
        project_root (Path): Project root directory.

    Returns:
        Tuple[bool, float, str]: (Success boolean, Elapsed seconds, Output message)
    """
    script_path = project_root / stage["script"]
    if not script_path.is_file():
        return False, 0.0, f"Script not found at: {script_path}"

    start_time = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False
        )
        elapsed = time.time() - start_time

        if result.returncode != 0:
            err_msg = result.stderr.strip() or result.stdout.strip()
            return False, elapsed, f"Execution failed with code {result.returncode}:\n{err_msg}"

        # Verify expected output exists
        expected_out = project_root / stage["expected_output"]
        if not expected_out.exists():
            return False, elapsed, f"Expected output artifact not created: {expected_out}"

        return True, elapsed, result.stdout
    except Exception as e:
        elapsed = time.time() - start_time
        return False, elapsed, f"Subprocess exception: {e}"


def main() -> None:
    """Execute the end-to-end Data Cleaning and Preprocessing Pipeline."""
    project_root = Path(__file__).resolve().parent

    print("\n" + "=" * 80)
    print("      DATA CLEANING AND PREPROCESSING SYSTEM - END-TO-END PIPELINE")
    print("=" * 80)
    print(f"Project Location: {project_root}")
    print(f"Python Runtime:   {sys.executable} (Version {sys.version.split()[0]})")
    print("=" * 80 + "\n")

    overall_start = time.time()
    completed_stages = 0

    for idx, stage in enumerate(PIPELINE_STAGES, start=1):
        phase_label = stage["phase"]
        stage_name = stage["name"]
        script_name = stage["script"]

        print(f"[{idx}/{len(PIPELINE_STAGES)}] Running {phase_label}: {stage_name} ({script_name})...")

        # For Phase 2, if raw data already exists, skip regeneration to preserve original dataset
        if stage["phase"] == "Phase 2" and (project_root / stage["expected_output"]).is_file():
            print(f"      [SKIP] Raw dataset already exists at: {stage['expected_output']} (Preserving original data).")
            completed_stages += 1
            continue

        success, duration, output = run_stage(stage, project_root)

        if not success:
            print(f"\n[FATAL ERROR] {phase_label} ({stage_name}) failed after {duration:.2f}s!")
            print(f"Error Details:\n{output}\n")
            print("=" * 80)
            print("PIPELINE EXECUTION ABORTED DUE TO PREREQUISITE FAILURE.")
            print("=" * 80)
            sys.exit(1)

        print(f"      [SUCCESS] Completed in {duration:.2f}s. Artifact verified: {stage['expected_output']}")
        completed_stages += 1

    total_duration = time.time() - overall_start

    print("\n" + "=" * 80)
    print("                 ALL PIPELINE PHASES COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print(f"Stages Executed:  {completed_stages}/{len(PIPELINE_STAGES)}")
    print(f"Total Time:       {total_duration:.2f}s")
    print("\nFinal Deliverables Generated:")
    print("  * Final CSV:       data/final/sales_final.csv")
    print("  * Final Excel:     data/final/sales_final.xlsx")
    print("  * Quality Report:  reports/final_data_quality_report.xlsx (5 sheets)")
    print("  * Full Report:     reports/final_project_report.txt")
    print("  * Issues Audit:    data/validated/validation_issues.csv")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
