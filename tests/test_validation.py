"""
test_validation.py - Unit and Validation Tests for Phase 5 Data Validation & QA Pipeline

Project: Data Cleaning and Preprocessing System
"""

import hashlib
import unittest
from pathlib import Path

import pandas as pd

# Import validation functions from validate_data
from validate_data import (
    DEFAULT_APPROVED_CATEGORIES,
    calculate_quality_scores,
    export_validation_issues,
    load_standardized_dataset,
    run_data_validation,
    validate_business_rules,
    validate_categories,
    validate_completeness,
    validate_consistency,
    validate_dates,
    validate_email,
    validate_numeric_columns,
    validate_uniqueness,
)


class TestDataValidationPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test file paths and record baseline file hashes for all previous phases."""
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.raw_path = cls.project_root / "data" / "raw" / "sales_dirty.csv"
        cls.cleaned_path = cls.project_root / "data" / "cleaned" / "sales_cleaned.csv"
        cls.standardized_path = cls.project_root / "data" / "standardized" / "sales_standardized.csv"
        cls.validated_dir = cls.project_root / "data" / "validated"
        cls.issues_csv_path = cls.validated_dir / "validation_issues.csv"
        cls.report_path = cls.project_root / "reports" / "phase5_validation_report.txt"

        # Record initial hashes of previous phase files to ensure zero modification
        with open(cls.raw_path, "rb") as f:
            cls.raw_hash = hashlib.sha256(f.read()).hexdigest()

        with open(cls.cleaned_path, "rb") as f:
            cls.cleaned_hash = hashlib.sha256(f.read()).hexdigest()

        with open(cls.standardized_path, "rb") as f:
            cls.standardized_hash = hashlib.sha256(f.read()).hexdigest()

    def test_01_load_standardized_dataset(self):
        """Test loading standardized CSV dataset and verifying error handling."""
        df = load_standardized_dataset(self.standardized_path)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 9)
        self.assertEqual(len(df.columns), 8)
        self.assertListEqual(
            list(df.columns),
            ["order_id", "customer_name", "email", "product", "quantity", "price", "city", "order_date"]
        )

        fake_path = self.project_root / "data" / "standardized" / "non_existent_dataset.csv"
        with self.assertRaises(FileNotFoundError):
            load_standardized_dataset(fake_path)

    def test_02_validate_completeness_missing_detection(self):
        """Test detection of missing values, nulls, and whitespace-only strings."""
        df = load_standardized_dataset(self.standardized_path)
        summary, issues = validate_completeness(df)

        self.assertEqual(summary["total_missing_cells"], 1)
        self.assertIn("email", summary["columns_with_missing"])
        self.assertEqual(summary["column_stats"]["email"]["status"], "INCOMPLETE")
        self.assertEqual(summary["column_stats"]["order_id"]["status"], "COMPLETE")
        self.assertAlmostEqual(summary["completeness_score_pct"], 98.61, places=1)

        # Test synthetic whitespace-only string detection
        test_df = pd.DataFrame({
            "order_id": [1, 2],
            "city": ["Chennai", "   "]
        })
        _, test_issues = validate_completeness(test_df)
        whitespace_issues = [i for i in test_issues if i["issue_type"] == "Whitespace-Only String"]
        self.assertEqual(len(whitespace_issues), 1)
        self.assertEqual(whitespace_issues[0]["column_name"], "city")

    def test_03_validate_uniqueness_duplicate_detection(self):
        """Test detection of duplicate rows, duplicate order_id, and repeated emails."""
        df = load_standardized_dataset(self.standardized_path)
        summary, issues = validate_uniqueness(df)

        self.assertEqual(summary["duplicate_rows_count"], 0)
        self.assertEqual(summary["duplicate_order_ids_count"], 0)
        self.assertEqual(summary["uniqueness_score_pct"], 100.0)

        # Test synthetic duplicate order_id
        dup_df = pd.DataFrame({
            "order_id": [101, 101, 102],
            "customer_name": ["Alice", "Bob", "Charlie"],
            "email": ["a@test.com", "b@test.com", "c@test.com"]
        })
        _, dup_issues = validate_uniqueness(dup_df)
        order_dup_issues = [i for i in dup_issues if i["issue_type"] == "Duplicate Order ID"]
        self.assertGreater(len(order_dup_issues), 0)
        self.assertEqual(order_dup_issues[0]["severity"], "ERROR")

    def test_04_validate_email_syntax_detection(self):
        """Test identification of invalid email formats while preserving nulls."""
        df = load_standardized_dataset(self.standardized_path)
        summary, issues = validate_email(df)

        self.assertEqual(summary["invalid_count"], 1)
        self.assertEqual(summary["missing_count"], 1)
        self.assertEqual(summary["valid_count"], 7)
        self.assertEqual(summary["invalid_records"][0]["email"], "invalid-email")

        # Verify issue record
        email_issues = [i for i in issues if i["issue_type"] == "Invalid Email Format"]
        self.assertEqual(len(email_issues), 1)
        self.assertEqual(email_issues[0]["order_id"], 104)
        self.assertEqual(email_issues[0]["severity"], "ERROR")

    def test_05_validate_numeric_quantity_and_price(self):
        """Test identification of negative quantities, negative prices, and zero values."""
        df = load_standardized_dataset(self.standardized_path)
        summary, issues = validate_numeric_columns(df)

        # Check negative quantity detection in real data (order_id 107 has quantity = -2)
        self.assertEqual(summary["quantity"]["negative_count"], 1)
        q_issues = [i for i in issues if i["issue_type"] == "Negative Quantity"]
        self.assertEqual(len(q_issues), 1)
        self.assertEqual(q_issues[0]["order_id"], 107)
        self.assertEqual(q_issues[0]["invalid_value"], -2)
        self.assertEqual(q_issues[0]["severity"], "WARNING")

        # Test synthetic negative and zero price
        test_df = pd.DataFrame({
            "order_id": [1, 2, 3],
            "quantity": [1, 2, 3],
            "price": [100.0, -50.0, 0.0]
        })
        test_summary, test_issues = validate_numeric_columns(test_df)
        self.assertEqual(test_summary["price"]["negative_count"], 1)
        self.assertEqual(test_summary["price"]["zero_count"], 1)

        neg_price_issue = [i for i in test_issues if i["issue_type"] == "Negative Price"]
        self.assertEqual(len(neg_price_issue), 1)
        self.assertEqual(neg_price_issue[0]["severity"], "ERROR")

    def test_06_validate_dates_and_range(self):
        """Test datetime validity, date range checking, and unparseable date handling."""
        df = load_standardized_dataset(self.standardized_path)
        summary, issues = validate_dates(df, start_date="2026-01-01", end_date="2026-12-31")

        self.assertEqual(summary["valid_count"], 9)
        self.assertEqual(summary["unparseable_count"], 0)
        self.assertEqual(summary["out_of_range_count"], 0)

        # Test synthetic invalid and out-of-range dates
        test_df = pd.DataFrame({
            "order_id": [1, 2, 3],
            "order_date": ["2026-01-05", "invalid-date-string", "2027-08-10"]
        })
        test_summary, test_issues = validate_dates(test_df, start_date="2026-01-01", end_date="2026-12-31")
        self.assertEqual(test_summary["unparseable_count"], 1)
        self.assertEqual(test_summary["out_of_range_count"], 1)

        unparseable = [i for i in test_issues if i["issue_type"] == "Unparseable Date"]
        self.assertEqual(len(unparseable), 1)
        self.assertEqual(unparseable[0]["severity"], "ERROR")

    def test_07_validate_categories_unknown_product(self):
        """Test product category catalog validation and unexpected product detection."""
        df = load_standardized_dataset(self.standardized_path)
        summary, issues = validate_categories(df)

        self.assertEqual(summary["product"]["unexpected_count"], 0)
        self.assertSetEqual(set(summary["product"]["unique_found"]), DEFAULT_APPROVED_CATEGORIES)

        # Test synthetic unknown product
        test_df = pd.DataFrame({
            "order_id": [1, 2],
            "product": ["Laptop", "Smartwatch"],
            "city": ["Chennai", "Unknown"]
        })
        test_summary, test_issues = validate_categories(test_df)
        self.assertEqual(test_summary["product"]["unexpected_count"], 1)
        unapproved = [i for i in test_issues if i["issue_type"] == "Unapproved Product Category"]
        self.assertEqual(len(unapproved), 1)
        self.assertEqual(unapproved[0]["invalid_value"], "Smartwatch")
        self.assertEqual(unapproved[0]["severity"], "ERROR")

    def test_08_calculate_quality_scores(self):
        """Test calculation of transparent Data Quality Scores and average arithmetic."""
        df = load_standardized_dataset(self.standardized_path)
        comp_summary, _ = validate_completeness(df)
        uniq_summary, _ = validate_uniqueness(df)
        email_summary, _ = validate_email(df)
        date_summary, _ = validate_dates(df)
        num_summary, _ = validate_numeric_columns(df)
        cat_summary, _ = validate_categories(df)
        const_summary, _ = validate_consistency(df)

        agg = {
            "completeness": comp_summary,
            "uniqueness": uniq_summary,
            "email": email_summary,
            "dates": date_summary,
            "numeric": num_summary,
            "categories": cat_summary,
            "consistency": const_summary
        }

        scores = calculate_quality_scores(agg, df)

        self.assertIn("completeness_score_pct", scores)
        self.assertIn("uniqueness_score_pct", scores)
        self.assertIn("validity_score_pct", scores)
        self.assertIn("consistency_score_pct", scores)
        self.assertIn("overall_quality_score_pct", scores)

        # Completeness: 71 / 72 cells = 98.61%
        self.assertAlmostEqual(scores["completeness_score_pct"], 98.61, places=1)
        # Uniqueness: 100%
        self.assertEqual(scores["uniqueness_score_pct"], 100.0)
        # Validity: (44 - 2) / 44 = 95.45%
        self.assertAlmostEqual(scores["validity_score_pct"], 95.45, places=1)
        # Consistency: 100%
        self.assertEqual(scores["consistency_score_pct"], 100.0)

        # Overall: arithmetic mean of the 4 dimensions
        expected_overall = round(
            (scores["completeness_score_pct"] + scores["uniqueness_score_pct"] +
             scores["validity_score_pct"] + scores["consistency_score_pct"]) / 4.0, 2
        )
        self.assertEqual(scores["overall_quality_score_pct"], expected_overall)

    def test_09_export_validation_issues_csv(self):
        """Test export of issue-level records to validation_issues.csv."""
        sample_issues = [
            {
                "row_index": 3,
                "order_id": 104,
                "column_name": "email",
                "invalid_value": "invalid-email",
                "issue_type": "Invalid Email Format",
                "severity": "ERROR",
                "description": "Invalid email syntax"
            },
            {
                "row_index": 5,
                "order_id": 107,
                "column_name": "quantity",
                "invalid_value": -2,
                "issue_type": "Negative Quantity",
                "severity": "WARNING",
                "description": "Negative quantity"
            }
        ]

        test_csv_path = self.validated_dir / "test_issues.csv"
        export_validation_issues(sample_issues, test_csv_path)

        self.assertTrue(test_csv_path.is_file())
        df_read = pd.read_csv(test_csv_path)
        self.assertEqual(len(df_read), 2)
        self.assertListEqual(
            list(df_read.columns),
            ["row_index", "order_id", "column_name", "invalid_value", "issue_type", "severity", "description"]
        )

        # Cleanup test file
        test_csv_path.unlink()

    def test_10_end_to_end_pipeline_and_file_preservation(self):
        """Test end-to-end Phase 5 pipeline execution and verify previous phase files preservation."""
        results, df_issues = run_data_validation(
            input_path=self.standardized_path,
            output_dir=self.validated_dir,
            report_path=self.report_path
        )

        # Check outputs exist
        self.assertTrue(self.issues_csv_path.is_file())
        self.assertTrue(self.report_path.is_file())

        # Check issues CSV structure
        self.assertGreater(len(df_issues), 0)
        self.assertIn("severity", df_issues.columns)
        self.assertIn("invalid_value", df_issues.columns)

        # Check report content
        report_text = self.report_path.read_text(encoding="utf-8")
        self.assertIn("DATA VALIDATION & QUALITY ASSURANCE REPORT - PHASE 5", report_text)
        self.assertIn("OVERALL DATA QUALITY SCORE", report_text)
        self.assertIn("ISSUES REQUIRING BUSINESS INVESTIGATION", report_text)
        self.assertIn("PASS / WARNING / ERROR AUDIT COUNTS", report_text)

        # Verify that raw dataset was NOT modified (hash match)
        with open(self.raw_path, "rb") as f:
            current_raw_hash = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(self.raw_hash, current_raw_hash, "Raw dataset was modified!")

        # Verify that Phase 3 cleaned dataset was NOT modified (hash match)
        with open(self.cleaned_path, "rb") as f:
            current_cleaned_hash = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(self.cleaned_hash, current_cleaned_hash, "Phase 3 cleaned dataset was modified!")

        # Verify that Phase 4 standardized dataset was NOT modified (hash match)
        with open(self.standardized_path, "rb") as f:
            current_standardized_hash = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(self.standardized_hash, current_standardized_hash, "Phase 4 standardized dataset was modified!")


if __name__ == "__main__":
    unittest.main()
