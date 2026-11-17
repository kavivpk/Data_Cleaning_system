"""
test_cleaning.py - Unit and Validation Tests for Phase 3 Data Cleaning Pipeline

Project: Data Cleaning and Preprocessing System
"""

import hashlib
import unittest
from pathlib import Path

import pandas as pd

# Import functions from clean_data
from clean_data import (
    EMAIL_REGEX,
    clean_email_values,
    clean_sales_data,
    handle_missing_values,
    identify_duplicates,
    inspect_missing_values,
    load_dataset,
    remove_duplicates,
    standardize_data_types,
)


class TestDataCleaningPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test file paths and capture raw file state."""
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.raw_path = cls.project_root / "data" / "raw" / "sales_dirty.csv"
        cls.cleaned_path = cls.project_root / "data" / "cleaned" / "sales_cleaned.csv"
        cls.report_path = cls.project_root / "reports" / "phase3_cleaning_report.txt"

        # Record hash of raw file to verify it is never modified
        with open(cls.raw_path, "rb") as f:
            cls.raw_initial_hash = hashlib.sha256(f.read()).hexdigest()

    def test_01_load_dataset(self):
        """Test loading valid CSV and error handling for missing file."""
        df = load_dataset(self.raw_path)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 10)
        self.assertIn("Order_ID", df.columns)
        self.assertIn("Customer_Name", df.columns)
        self.assertIn("Email", df.columns)
        self.assertIn("Product", df.columns)
        self.assertIn("Quantity", df.columns)
        self.assertIn("Price", df.columns)
        self.assertIn("City", df.columns)
        self.assertIn("Order_Date", df.columns)

        # Non-existent file should raise FileNotFoundError
        fake_path = self.project_root / "data" / "raw" / "non_existent.csv"
        with self.assertRaises(FileNotFoundError):
            load_dataset(fake_path)

    def test_02_inspect_missing_values(self):
        """Test missing value inspection logic and statistics."""
        df = load_dataset(self.raw_path)
        summary = inspect_missing_values(df)

        self.assertIsInstance(summary, pd.DataFrame)
        self.assertListEqual(list(summary.columns), ["Column", "Missing_Count", "Missing_Percentage"])

        col_map = dict(zip(summary["Column"], summary["Missing_Count"]))
        self.assertEqual(col_map["Customer_Name"], 1)
        self.assertEqual(col_map["Email"], 1)
        self.assertEqual(col_map["Price"], 1)
        self.assertEqual(col_map["City"], 1)
        self.assertEqual(col_map["Order_ID"], 0)

    def test_03_handle_missing_values(self):
        """Test business rules for missing value imputation."""
        df = load_dataset(self.raw_path)
        cleaned_df, stats = handle_missing_values(df)

        # Customer_Name missing replaced with 'Unknown'
        self.assertEqual(cleaned_df["Customer_Name"].isna().sum(), 0)
        self.assertIn("Unknown", cleaned_df["Customer_Name"].values)

        # City missing replaced with 'Unknown'
        self.assertEqual(cleaned_df["City"].isna().sum(), 0)
        self.assertIn("Unknown", cleaned_df["City"].values)

        # Email missing preserved (not faked)
        self.assertEqual(cleaned_df["Email"].isna().sum(), 1)

        # Price missing imputed using product category median
        self.assertEqual(cleaned_df["Price"].isna().sum(), 0)
        # Order_ID 109 is a Keyboard. The known Keyboard has Price = 1200.0
        row_109 = cleaned_df[cleaned_df["Order_ID"] == 109].iloc[0]
        self.assertEqual(row_109["Price"], 1200.0)

        # Imputation stats reported
        self.assertEqual(len(stats["price_imputations"]), 1)
        self.assertEqual(stats["price_imputations"][0]["Order_ID"], 109)
        self.assertEqual(stats["price_imputations"][0]["Imputed_Price"], 1200.0)

    def test_04_identify_and_remove_duplicates(self):
        """Test duplicate detection and Order_ID business key deduplication."""
        df = load_dataset(self.raw_path)
        dup_info = identify_duplicates(df)

        self.assertEqual(len(dup_info["exact_duplicates"]), 2)
        self.assertEqual(len(dup_info["order_id_duplicates"]), 2)

        deduped_df, removed_count = remove_duplicates(df, subset=["Order_ID"], keep="first")
        self.assertEqual(removed_count, 1)
        self.assertEqual(len(deduped_df), 9)

        # Verify no duplicate Order_IDs remain
        self.assertEqual(deduped_df.duplicated(subset=["Order_ID"]).sum(), 0)

        # Verify distinct orders with same customer/product are preserved
        laptops = deduped_df[deduped_df["Product"] == "Laptop"]
        self.assertGreater(len(laptops), 1)

    def test_05_clean_email_values(self):
        """Test email whitespace trimming, lowercasing, and validation."""
        test_df = pd.DataFrame({
            "Order_ID": [1, 2, 3, 4],
            "Customer_Name": ["A", "B", "C", "D"],
            "Email": [" Test@Example.com ", "invalid-email", None, "VALID.USER@DOMAIN.ORG"]
        })

        cleaned_df, stats = clean_email_values(test_df)

        self.assertEqual(cleaned_df.loc[0, "Email"], "test@example.com")
        self.assertEqual(cleaned_df.loc[1, "Email"], "invalid-email")
        self.assertTrue(pd.isna(cleaned_df.loc[2, "Email"]))
        self.assertEqual(cleaned_df.loc[3, "Email"], "valid.user@domain.org")

        self.assertEqual(stats["invalid_count"], 1)
        self.assertEqual(stats["missing_count"], 1)
        self.assertEqual(stats["invalid_records"][0]["Email"], "invalid-email")

    def test_06_standardize_data_types(self):
        """Test datatype casting, day-first date parsing, and error safety."""
        df = load_dataset(self.raw_path)
        # Deduplicate first to test on clean structure
        df_deduped, _ = remove_duplicates(df, subset=["Order_ID"])
        df_imputed, _ = handle_missing_values(df_deduped)
        typed_df, stats = standardize_data_types(df_imputed)

        # Check dtypes
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(typed_df["Order_Date"]))
        self.assertTrue(pd.api.types.is_integer_dtype(typed_df["Order_ID"]))
        self.assertTrue(pd.api.types.is_integer_dtype(typed_df["Quantity"]))
        self.assertTrue(pd.api.types.is_float_dtype(typed_df["Price"]))

        # Verify dayfirst interpretation: '02/01/2026' should be 2026-01-02
        row_102 = typed_df[typed_df["Order_ID"] == 102].iloc[0]
        self.assertEqual(row_102["Order_Date"], pd.Timestamp("2026-01-02"))

        # Verify '10/01/2026' is 2026-01-10
        row_110 = typed_df[typed_df["Order_ID"] == 110].iloc[0]
        self.assertEqual(row_110["Order_Date"], pd.Timestamp("2026-01-10"))

        # Verify ISO '2026-01-03' is 2026-01-03
        row_103 = typed_df[typed_df["Order_ID"] == 103].iloc[0]
        self.assertEqual(row_103["Order_Date"], pd.Timestamp("2026-01-03"))

        # Zero invalid dates in standard dataset
        self.assertEqual(len(stats["invalid_dates"]), 0)

    def test_07_end_to_end_pipeline_and_file_generation(self):
        """Test complete pipeline execution, report generation, and data reloadability."""
        cleaned_df, stats = clean_sales_data(
            raw_path=self.raw_path,
            cleaned_path=self.cleaned_path,
            report_path=self.report_path
        )

        # Check cleaned DataFrame structure
        self.assertEqual(len(cleaned_df), 9)
        self.assertEqual(len(cleaned_df.columns), 8)

        # Check that cleaned CSV exists and is reloadable
        self.assertTrue(self.cleaned_path.is_file())
        reloaded_df = pd.read_csv(self.cleaned_path)
        self.assertEqual(len(reloaded_df), 9)

        # Check that Order_Date can be interpreted as datetime upon reload
        parsed_dates = pd.to_datetime(reloaded_df["Order_Date"])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(parsed_dates))

        # Check that report exists and contains required sections
        self.assertTrue(self.report_path.is_file())
        report_text = self.report_path.read_text(encoding="utf-8")
        self.assertIn("Original Number of Rows: 10", report_text)
        self.assertIn("Final Number of Rows:    9", report_text)
        self.assertIn("Duplicate Rows Removed:  1", report_text)
        self.assertIn("Order_ID 109 (Keyboard): Imputed Price = 1200.00", report_text)
        self.assertIn("Total Invalid Email Records: 1", report_text)
        self.assertIn("UNRESOLVED DATA QUALITY ISSUES", report_text)

        # Verify that raw dataset was NOT modified (hash matches)
        with open(self.raw_path, "rb") as f:
            current_raw_hash = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(self.raw_initial_hash, current_raw_hash, "Raw dataset was modified!")


if __name__ == "__main__":
    unittest.main()

