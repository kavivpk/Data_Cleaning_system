"""
test_standardization.py - Unit and Validation Tests for Phase 4 Data Standardization Pipeline

Project: Data Cleaning and Preprocessing System
"""

import hashlib
import unittest
from pathlib import Path

import pandas as pd

# Import functions from standardize_data
from standardize_data import (
    CANONICAL_PRODUCT_MAPPING,
    EXPECTED_PRODUCT_CATEGORIES,
    MISSING_VALUE_MARKERS,
    load_cleaned_dataset,
    save_standardized_dataset,
    standardize_column_names,
    standardize_date_format,
    standardize_missing_values,
    standardize_numeric_columns,
    standardize_product_categories,
    standardize_sales_data,
    standardize_text_values,
    to_snake_case,
    validate_standardized_data,
)


class TestDataStandardizationPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test file paths and record baseline file hashes."""
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.raw_path = cls.project_root / "data" / "raw" / "sales_dirty.csv"
        cls.cleaned_path = cls.project_root / "data" / "cleaned" / "sales_cleaned.csv"
        cls.standardized_path = cls.project_root / "data" / "standardized" / "sales_standardized.csv"
        cls.report_path = cls.project_root / "reports" / "phase4_standardization_report.txt"

        # Record initial hashes to ensure raw and Phase 3 datasets are NEVER modified
        with open(cls.raw_path, "rb") as f:
            cls.raw_initial_hash = hashlib.sha256(f.read()).hexdigest()

        with open(cls.cleaned_path, "rb") as f:
            cls.cleaned_initial_hash = hashlib.sha256(f.read()).hexdigest()

    def test_01_load_cleaned_dataset(self):
        """Test loading Phase 3 cleaned dataset and handling non-existent files."""
        df = load_cleaned_dataset(self.cleaned_path)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 9)
        self.assertEqual(len(df.columns), 8)

        # FileNotFoundError for missing path
        fake_path = self.project_root / "data" / "cleaned" / "non_existent.csv"
        with self.assertRaises(FileNotFoundError):
            load_cleaned_dataset(fake_path)

    def test_02_standardize_column_names(self):
        """Test snake_case conversion for column names and duplicate resolution."""
        test_df = pd.DataFrame({
            "Order_ID": [1],
            "Customer Name": ["Alice"],
            "EMAIL-ADDRESS": ["alice@example.com"],
            "Product.Category": ["Laptop"],
            "Order_ID": [101]  # duplicate scenario if handled
        })
        renamed_df, mapping = standardize_column_names(test_df)

        self.assertIn("order_id", renamed_df.columns)
        self.assertIn("customer_name", renamed_df.columns)
        self.assertIn("email_address", renamed_df.columns)
        self.assertIn("product_category", renamed_df.columns)

        # Test to_snake_case helper directly
        self.assertEqual(to_snake_case("Order_ID"), "order_id")
        self.assertEqual(to_snake_case("Customer_Name"), "customer_name")
        self.assertEqual(to_snake_case("  Order Date - 2026  "), "order_date_2026")

    def test_03_standardize_text_values(self):
        """Test whitespace stripping, internal space collapsing, and casing."""
        test_df = pd.DataFrame({
            "customer_name": [" arun ", "MARY   JANE", None],
            "city": ["chennai", "MADURAI", "  Trichy  "],
            "email": ["  USER@DOMAIN.COM ", "Valid.Email@Domain.Org", None]
        })

        cleaned_df, stats = standardize_text_values(test_df)

        # customer_name: title case, whitespace trimmed, multiple spaces collapsed
        self.assertEqual(cleaned_df.loc[0, "customer_name"], "Arun")
        self.assertEqual(cleaned_df.loc[1, "customer_name"], "Mary Jane")
        self.assertTrue(pd.isna(cleaned_df.loc[2, "customer_name"]))

        # city: standardized to Title Case
        self.assertEqual(cleaned_df.loc[0, "city"], "Chennai")
        self.assertEqual(cleaned_df.loc[1, "city"], "Madurai")
        self.assertEqual(cleaned_df.loc[2, "city"], "Trichy")

        # email: lowercase and whitespace stripped
        self.assertEqual(cleaned_df.loc[0, "email"], "user@domain.com")
        self.assertEqual(cleaned_df.loc[1, "email"], "valid.email@domain.org")
        self.assertTrue(pd.isna(cleaned_df.loc[2, "email"]))

        self.assertGreater(stats["total_changes"], 0)

    def test_04_standardize_product_categories(self):
        """Test product category normalization against canonical categories."""
        test_df = pd.DataFrame({
            "product": ["laptop", " Mobile ", "MOUSE", "Keyboard", "Laptop"]
        })

        cleaned_df, stats = standardize_product_categories(test_df)

        expected = ["Laptop", "Mobile", "Mouse", "Keyboard", "Laptop"]
        self.assertListEqual(list(cleaned_df["product"]), expected)
        self.assertEqual(len(stats["unknown_categories"]), 0)
        self.assertSetEqual(set(stats["categories_found"]), EXPECTED_PRODUCT_CATEGORIES)

    def test_05_unknown_category_detection(self):
        """Verify that unknown/unexpected products are flagged and NOT silently altered."""
        test_df = pd.DataFrame({
            "product": ["Laptop", "Tablet", "Smartwatch", "Mouse"]
        })

        cleaned_df, stats = standardize_product_categories(test_df)

        # "Tablet" and "Smartwatch" should NOT be converted to Laptop or Mouse
        self.assertEqual(cleaned_df.loc[1, "product"], "Tablet")
        self.assertEqual(cleaned_df.loc[2, "product"], "Smartwatch")

        # Should be reported in unknown_categories
        unknown_vals = [u["value"] for u in stats["unknown_categories"]]
        self.assertIn("Tablet", unknown_vals)
        self.assertIn("Smartwatch", unknown_vals)
        self.assertEqual(len(stats["unknown_categories"]), 2)

    def test_06_standardize_missing_values(self):
        """Test detection and conversion of non-standard missing value markers."""
        test_df = pd.DataFrame({
            "text_col": ["Valid", "  ", "NULL", "n/a", "None", "Unknown"],
            "num_col": ["100", "-", "null", "200", "N/A", "300"]
        })

        cleaned_df, stats = standardize_missing_values(test_df)

        # 'Valid' and legitimate business imputation 'Unknown' must be preserved
        self.assertEqual(cleaned_df.loc[0, "text_col"], "Valid")
        self.assertEqual(cleaned_df.loc[5, "text_col"], "Unknown")

        # Inconsistent markers converted to pd.NA
        self.assertTrue(pd.isna(cleaned_df.loc[1, "text_col"]))
        self.assertTrue(pd.isna(cleaned_df.loc[2, "text_col"]))
        self.assertTrue(pd.isna(cleaned_df.loc[3, "text_col"]))
        self.assertTrue(pd.isna(cleaned_df.loc[4, "text_col"]))
        self.assertTrue(pd.isna(cleaned_df.loc[1, "num_col"]))
        self.assertTrue(pd.isna(cleaned_df.loc[2, "num_col"]))

        self.assertGreater(stats["total_markers_replaced"], 0)

    def test_07_standardize_date_format(self):
        """Test date parsing, day-first preservation, and error coercion."""
        test_df = pd.DataFrame({
            "order_date": [
                "2026-01-01",  # ISO
                "02/01/2026",  # Day-first (2nd Jan 2026)
                "2026/01/03",  # ISO with slashes
                "10/01/2026",  # Day-first (10th Jan 2026)
                "invalid-date",# Unparseable date
                None           # Missing date
            ]
        })

        cleaned_df, stats = standardize_date_format(test_df, date_column="order_date")

        self.assertTrue(pd.api.types.is_datetime64_any_dtype(cleaned_df["order_date"]))
        self.assertEqual(cleaned_df.loc[0, "order_date"], pd.Timestamp("2026-01-01"))
        self.assertEqual(cleaned_df.loc[1, "order_date"], pd.Timestamp("2026-01-02"))
        self.assertEqual(cleaned_df.loc[3, "order_date"], pd.Timestamp("2026-01-10"))

        # Invalid date coerced to NaT and reported
        self.assertTrue(pd.isna(cleaned_df.loc[4, "order_date"]))
        self.assertEqual(len(stats["invalid_dates"]), 1)
        self.assertEqual(stats["invalid_dates"][0]["original_value"], "invalid-date")

    def test_08_standardize_numeric_columns(self):
        """Test numeric datatype standardization and suspicious value reporting."""
        test_df = pd.DataFrame({
            "order_id": [" 101 ", "102"],
            "quantity": ["1", "-2"],
            "price": ["$45,000.00", "15000.50"]
        })

        cleaned_df, stats = standardize_numeric_columns(test_df)

        self.assertTrue(pd.api.types.is_integer_dtype(cleaned_df["order_id"]))
        self.assertTrue(pd.api.types.is_integer_dtype(cleaned_df["quantity"]))
        self.assertTrue(pd.api.types.is_float_dtype(cleaned_df["price"]))

        # Decimal precision preserved without rounding
        self.assertEqual(cleaned_df.loc[1, "price"], 15000.50)

        # Negative quantity preserved but flagged as suspicious
        self.assertEqual(cleaned_df.loc[1, "quantity"], -2)
        suspicious_list = stats["suspicious_values"]
        self.assertTrue(any(s["column"] == "quantity" and s["value"] == -2 for s in suspicious_list))

    def test_09_end_to_end_pipeline_and_file_preservation(self):
        """Test full Phase 4 pipeline execution, export verification, and baseline preservation."""
        standardized_df, stats = standardize_sales_data(
            input_path=self.cleaned_path,
            output_path=self.standardized_path,
            report_path=self.report_path
        )

        # Structure checks
        self.assertEqual(len(standardized_df), 9)
        self.assertEqual(len(standardized_df.columns), 8)
        self.assertListEqual(
            list(standardized_df.columns),
            ["order_id", "customer_name", "email", "product", "quantity", "price", "city", "order_date"]
        )

        # Check that output CSV exists and is reloadable
        self.assertTrue(self.standardized_path.is_file())
        reloaded_df = pd.read_csv(self.standardized_path)
        self.assertEqual(len(reloaded_df), 9)
        self.assertIn("order_date", reloaded_df.columns)

        # Date representation reload check
        self.assertEqual(reloaded_df.loc[1, "order_date"], "2026-01-02")
        self.assertEqual(reloaded_df.loc[8, "order_date"], "2026-01-10")

        # Check that report exists and contains required sections
        self.assertTrue(self.report_path.is_file())
        report_text = self.report_path.read_text(encoding="utf-8")
        self.assertIn("DATA STANDARDIZATION REPORT - PHASE 4", report_text)
        self.assertIn("Original Column Name      ->  Standardized Column Name", report_text)
        self.assertIn("order_id", report_text)
        self.assertIn("Row 6: 'MOUSE' -> 'Mouse'", report_text)
        self.assertIn("REMAINING DATA QUALITY ISSUES", report_text)

        # Verify that raw dataset was NOT modified (hash matches)
        with open(self.raw_path, "rb") as f:
            current_raw_hash = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(self.raw_initial_hash, current_raw_hash, "Raw dataset was modified!")

        # Verify that Phase 3 cleaned dataset was NOT modified (hash matches)
        with open(self.cleaned_path, "rb") as f:
            current_cleaned_hash = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(self.cleaned_initial_hash, current_cleaned_hash, "Phase 3 cleaned dataset was modified!")


if __name__ == "__main__":
    unittest.main()

