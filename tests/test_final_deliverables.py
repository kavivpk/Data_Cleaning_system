"""
test_final_deliverables.py - Unit and Validation Tests for Phase 6 Deliverables & Pipeline

Project: Data Cleaning and Preprocessing System
"""

import hashlib
import unittest
from pathlib import Path

import openpyxl
import pandas as pd


class TestFinalDeliverables(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up file paths and load final deliverables for testing."""
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.raw_csv = cls.project_root / "data" / "raw" / "sales_dirty.csv"
        cls.cleaned_csv = cls.project_root / "data" / "cleaned" / "sales_cleaned.csv"
        cls.standardized_csv = cls.project_root / "data" / "standardized" / "sales_standardized.csv"
        cls.final_csv = cls.project_root / "data" / "final" / "sales_final.csv"
        cls.final_xlsx = cls.project_root / "data" / "final" / "sales_final.xlsx"
        cls.report_xlsx = cls.project_root / "reports" / "final_data_quality_report.xlsx"
        cls.report_txt = cls.project_root / "reports" / "final_project_report.txt"
        cls.readme_path = cls.project_root / "README.md"
        cls.requirements_path = cls.project_root / "requirements.txt"
        cls.gitignore_path = cls.project_root / ".gitignore"

    def test_01_final_csv_structure(self):
        """Test existence, row count, and schema of sales_final.csv."""
        self.assertTrue(self.final_csv.is_file(), "sales_final.csv does not exist.")
        df = pd.read_csv(self.final_csv)
        self.assertEqual(len(df), 9, f"Expected 9 rows in sales_final.csv, got {len(df)}")
        self.assertEqual(len(df.columns), 8, f"Expected 8 columns, got {len(df.columns)}")
        expected_cols = ["order_id", "customer_name", "email", "product", "quantity", "price", "city", "order_date"]
        self.assertListEqual(list(df.columns), expected_cols)

    def test_02_final_xlsx_structure(self):
        """Test existence, row count, and schema of sales_final.xlsx."""
        self.assertTrue(self.final_xlsx.is_file(), "sales_final.xlsx does not exist.")
        df = pd.read_excel(self.final_xlsx)
        self.assertEqual(len(df), 9, f"Expected 9 rows in sales_final.xlsx, got {len(df)}")
        self.assertEqual(len(df.columns), 8, f"Expected 8 columns, got {len(df.columns)}")

    def test_03_csv_and_excel_equivalence(self):
        """Test that sales_final.csv and sales_final.xlsx contain equivalent records."""
        df_csv = pd.read_csv(self.final_csv)
        df_xlsx = pd.read_excel(self.final_xlsx)

        # Compare row counts
        self.assertEqual(len(df_csv), len(df_xlsx))

        # Compare order_id sequence
        self.assertListEqual(list(df_csv["order_id"]), list(df_xlsx["order_id"]))

        # Compare customer names
        self.assertListEqual(list(df_csv["customer_name"]), list(df_xlsx["customer_name"]))

        # Compare products
        self.assertListEqual(list(df_csv["product"]), list(df_xlsx["product"]))

        # Compare quantities
        self.assertListEqual(list(df_csv["quantity"]), list(df_xlsx["quantity"]))

        # Compare prices numerically
        for p_csv, p_xlsx in zip(df_csv["price"], df_xlsx["price"]):
            self.assertAlmostEqual(float(p_csv), float(p_xlsx), places=2)

        # Compare cities
        self.assertListEqual(list(df_csv["city"]), list(df_xlsx["city"]))

        # Compare dates
        self.assertListEqual(list(df_csv["order_date"]), list(df_xlsx["order_date"]))

    def test_04_excel_workbook_sheets(self):
        """Test that final_data_quality_report.xlsx exists and contains all 5 required sheets."""
        self.assertTrue(self.report_xlsx.is_file(), "final_data_quality_report.xlsx does not exist.")
        wb = openpyxl.load_workbook(self.report_xlsx)
        expected_sheets = [
            "Executive Summary",
            "Data Quality",
            "Validation Issues",
            "Column Summary",
            "Cleaning Summary"
        ]
        self.assertListEqual(wb.sheetnames, expected_sheets)

        # Check that each sheet has content
        for sheet_name in expected_sheets:
            ws = wb[sheet_name]
            self.assertGreater(ws.max_row, 1, f"Sheet '{sheet_name}' has no data rows.")
            self.assertGreater(ws.max_column, 1, f"Sheet '{sheet_name}' has no columns.")
            self.assertIsNotNone(ws.freeze_panes, f"Sheet '{sheet_name}' is missing frozen header panes.")

    def test_05_consolidated_report_content(self):
        """Test that final_project_report.txt contains all required report sections."""
        self.assertTrue(self.report_txt.is_file(), "final_project_report.txt does not exist.")
        report_text = self.report_txt.read_text(encoding="utf-8")
        required_sections = [
            "1. PROJECT OVERVIEW",
            "2. BUSINESS PROBLEM",
            "3. PROJECT OBJECTIVES",
            "4. DATASET DESCRIPTION",
            "5. TECHNOLOGY STACK",
            "6. PHASE 2: DATA INSPECTION SUMMARY",
            "7. PHASE 3: DATA CLEANING SUMMARY",
            "8. PHASE 4: DATA STANDARDIZATION SUMMARY",
            "9. PHASE 5: DATA VALIDATION & QA SUMMARY",
            "10. FINAL DATASET INFORMATION",
            "11. DATA QUALITY SCORECARD",
            "12. REMAINING OPERATIONAL LIMITATIONS",
            "13. FINAL CONCLUSION"
        ]
        for section in required_sections:
            self.assertIn(section, report_text, f"Missing section: {section}")

        self.assertIn("98.52%", report_text)

    def test_06_requirements_and_gitignore(self):
        """Test existence of requirements.txt and .gitignore with proper contents."""
        self.assertTrue(self.requirements_path.is_file(), "requirements.txt does not exist.")
        req_content = self.requirements_path.read_text(encoding="utf-8")
        self.assertIn("pandas", req_content)
        self.assertIn("openpyxl", req_content)

        self.assertTrue(self.gitignore_path.is_file(), ".gitignore does not exist.")
        git_content = self.gitignore_path.read_text(encoding="utf-8")
        self.assertIn("__pycache__", git_content)
        self.assertIn(".venv", git_content)

    def test_07_raw_dataset_preservation(self):
        """Verify that the raw dataset has not been modified or corrupted."""
        self.assertTrue(self.raw_csv.is_file())
        df_raw = pd.read_csv(self.raw_csv)
        self.assertEqual(len(df_raw), 10, "Raw dataset must retain exactly 10 initial records.")
        self.assertIn("Customer_Name", df_raw.columns)


if __name__ == "__main__":
    unittest.main()
