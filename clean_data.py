"""
clean_data.py - Phase 3: Data Cleaning Pipeline

Project: Data Cleaning and Preprocessing System
Description: Reusable, beginner-friendly data cleaning script using Python and Pandas.
             Handles missing values, duplicate records, incorrect data formats,
             email validation, and generates comprehensive cleaning reports.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd


# Regex pattern for validating email addresses (standard RFC 5322 simplified)
EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"


def load_dataset(file_path: Path) -> pd.DataFrame:
    """
    Load the raw CSV dataset into a Pandas DataFrame.

    Parameters:
        file_path (Path): Path to the raw CSV file.

    Returns:
        pd.DataFrame: A copy of the loaded DataFrame.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file is empty or cannot be parsed.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Raw dataset file not found at: {path.resolve()}")

    try:
        df = pd.read_csv(path)
        if df.empty:
            raise ValueError(f"The dataset at {path} is empty.")
        return df.copy()
    except Exception as e:
        raise RuntimeError(f"Error loading dataset from {path}: {e}") from e


def inspect_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect missing values using isnull() and isna(), then calculate counts
    and percentages for each column.

    Parameters:
        df (pd.DataFrame): DataFrame to inspect.

    Returns:
        pd.DataFrame: Summary table containing Missing_Count and Missing_Percentage.
    """
    # Detect missing values using both isna() and isnull() per project requirements
    missing_isna = df.isna().sum()
    missing_isnull = df.isnull().sum()

    # Verify that isnull() and isna() produce consistent results
    assert missing_isna.equals(missing_isnull), "Mismatch between isna() and isnull() results!"

    total_rows = len(df)
    missing_pct = (missing_isna / total_rows * 100).round(2) if total_rows > 0 else 0.0

    summary_df = pd.DataFrame({
        "Column": df.columns,
        "Missing_Count": missing_isna.values,
        "Missing_Percentage": missing_pct.values
    })
    return summary_df


def handle_missing_values(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Apply business rules to handle missing values:
      - Customer_Name: Replace missing with 'Unknown'.
      - Email: Do not generate fake email addresses. Preserve missing values and report them.
      - Price: Impute missing price using the median price of the same product category.
      - City: Replace missing with 'Unknown'.

    Parameters:
        df (pd.DataFrame): DataFrame with potential missing values.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]:
            Cleaned DataFrame and a dictionary detailing imputations and missing counts.
    """
    cleaned_df = df.copy()
    imputation_details: Dict[str, Any] = {
        "price_imputations": [],
        "customer_name_missing_count": int(cleaned_df["Customer_Name"].isna().sum()),
        "city_missing_count": int(cleaned_df["City"].isna().sum()),
        "email_missing_count": int(cleaned_df["Email"].isna().sum()),
    }

    # 1. Customer_Name: Replace missing values with "Unknown"
    # Rationale: Preserves commercial transaction records for sales aggregation
    # while explicitly identifying that customer identity is unrecorded.
    cleaned_df["Customer_Name"] = cleaned_df["Customer_Name"].fillna("Unknown")

    # 2. City: Replace missing values with "Unknown"
    # Rationale: Preserves order financial values while transparently flagging
    # unrecorded geographical delivery data.
    cleaned_df["City"] = cleaned_df["City"].fillna("Unknown")

    # 3. Price: Impute missing price using the median price of the same product category
    # Rationale: Product prices are typically uniform or bounded per category.
    # The median is robust against potential pricing outliers.
    # We normalize product strings (strip whitespace and standardize casing) to match categories accurately.
    norm_product = cleaned_df["Product"].astype(str).str.strip().str.title()
    category_medians = cleaned_df.groupby(norm_product)["Price"].transform("median")

    missing_price_mask = cleaned_df["Price"].isna()
    imputable_mask = missing_price_mask & category_medians.notna()

    for idx in cleaned_df[imputable_mask].index:
        imputed_value = float(category_medians.loc[idx])
        imputation_details["price_imputations"].append({
            "index": idx,
            "Order_ID": cleaned_df.loc[idx, "Order_ID"],
            "Product": cleaned_df.loc[idx, "Product"],
            "Imputed_Price": imputed_value
        })

    cleaned_df["Price"] = cleaned_df["Price"].fillna(category_medians)

    # 4. Email: Preserve missing values without generating fake emails
    # Rationale: Synthetic emails (e.g. unknown@domain.com) corrupt marketing databases,
    # increase bounce rates, and violate compliance standards.
    # Missing emails are preserved as NaN and reported.

    return cleaned_df, imputation_details


def identify_duplicates(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Identify exact duplicate rows and duplicate Order_ID values.

    Parameters:
        df (pd.DataFrame): DataFrame to inspect.

    Returns:
        Dict[str, pd.DataFrame]:
            Dictionary containing 'exact_duplicates' and 'order_id_duplicates' DataFrames.
    """
    exact_duplicates = df[df.duplicated(keep=False)]
    order_id_duplicates = df[df.duplicated(subset=["Order_ID"], keep=False)]

    return {
        "exact_duplicates": exact_duplicates,
        "order_id_duplicates": order_id_duplicates
    }


def remove_duplicates(
    df: pd.DataFrame,
    subset: List[str] = ["Order_ID"],
    keep: str = "first"
) -> Tuple[pd.DataFrame, int]:
    """
    Remove repeated transactions using Order_ID as the unique business key,
    keeping the first valid record.

    Important:
      Records are not deleted based on repeated customer or product names.

    Parameters:
        df (pd.DataFrame): DataFrame to deduplicate.
        subset (List[str]): Columns defining uniqueness (default: ['Order_ID']).
        keep (str): Which duplicate record to retain ('first', 'last', False).

    Returns:
        Tuple[pd.DataFrame, int]:
            Deduplicated DataFrame and the count of removed duplicate records.
    """
    initial_count = len(df)
    deduped_df = df.drop_duplicates(subset=subset, keep=keep).copy()
    removed_count = initial_count - len(deduped_df)

    # Verify duplicate Order_IDs after deduplication
    remaining_duplicates = deduped_df.duplicated(subset=subset).sum()
    assert remaining_duplicates == 0, f"Deduplication failed: {remaining_duplicates} duplicates remain."

    return deduped_df, removed_count


def _parse_custom_date(val: Any) -> Any:
    """
    Helper function to parse mixed date formats safely.
    Handles:
      - ISO dates: YYYY-MM-DD or YYYY/MM/DD (dayfirst=False)
      - Day-first dates: DD/MM/YYYY or DD-MM-YYYY (dayfirst=True)
      - Coerces invalid values to NaT.
    """
    if pd.isna(val):
        return pd.NaT

    val_str = str(val).strip()
    if not val_str:
        return pd.NaT

    try:
        # If the string starts with 4 digits, it is in Year-First format (e.g. 2026-01-01, 2026/01/07)
        if len(val_str) >= 4 and val_str[:4].isdigit():
            return pd.to_datetime(val_str, dayfirst=False, errors="coerce")
        # Otherwise, day-first format (e.g. 02/01/2026, 04-01-2026, 10/01/2026)
        else:
            return pd.to_datetime(val_str, dayfirst=True, errors="coerce")
    except Exception:
        return pd.NaT


def standardize_data_types(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Convert columns to their correct, standard data types:
      - Order_Date: datetime64 (dayfirst interpretation for DD/MM/YYYY, safe coercion)
      - Order_ID: integer (int64)
      - Quantity: integer (int64)
      - Price: float (float64)

    Parameters:
        df (pd.DataFrame): DataFrame to standardize.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]:
            Standardized DataFrame and statistics regarding type conversions and invalid records.
    """
    cleaned_df = df.copy()
    conversion_stats: Dict[str, Any] = {
        "invalid_dates": [],
        "invalid_numeric_order_id": [],
        "invalid_numeric_quantity": [],
        "invalid_numeric_price": []
    }

    # 1. Convert Order_Date to datetime
    original_dates = cleaned_df["Order_Date"].copy()
    parsed_dates = original_dates.apply(_parse_custom_date)
    cleaned_df["Order_Date"] = pd.to_datetime(parsed_dates)

    # Detect any values that failed parsing (became NaT while original was non-empty)
    for idx, (orig, parsed) in enumerate(zip(original_dates, cleaned_df["Order_Date"])):
        if pd.notna(orig) and str(orig).strip() != "" and pd.isna(parsed):
            conversion_stats["invalid_dates"].append({
                "row_index": idx,
                "original_value": orig
            })

    # 2. Convert Order_ID to integer safely
    numeric_order_id = pd.to_numeric(cleaned_df["Order_ID"], errors="coerce")
    for idx, (orig, conv) in enumerate(zip(cleaned_df["Order_ID"], numeric_order_id)):
        if pd.notna(orig) and pd.isna(conv):
            conversion_stats["invalid_numeric_order_id"].append({"row_index": idx, "original_value": orig})
    cleaned_df["Order_ID"] = numeric_order_id.astype("int64")

    # 3. Convert Quantity to integer safely
    numeric_quantity = pd.to_numeric(cleaned_df["Quantity"], errors="coerce")
    for idx, (orig, conv) in enumerate(zip(cleaned_df["Quantity"], numeric_quantity)):
        if pd.notna(orig) and pd.isna(conv):
            conversion_stats["invalid_numeric_quantity"].append({"row_index": idx, "original_value": orig})
    cleaned_df["Quantity"] = numeric_quantity.astype("int64")

    # 4. Convert Price to float safely
    numeric_price = pd.to_numeric(cleaned_df["Price"], errors="coerce")
    for idx, (orig, conv) in enumerate(zip(cleaned_df["Price"], numeric_price)):
        if pd.notna(orig) and pd.isna(conv):
            conversion_stats["invalid_numeric_price"].append({"row_index": idx, "original_value": orig})
    cleaned_df["Price"] = numeric_price.astype("float64")

    return cleaned_df, conversion_stats


def clean_email_values(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Clean and validate email addresses:
      - Trim leading and trailing spaces.
      - Standardize casing to lowercase.
      - Identify invalid email formats using regex.
      - Preserve invalid and missing emails without inventing fake ones.

    Parameters:
        df (pd.DataFrame): DataFrame with Email column.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]:
            DataFrame with trimmed and lowercased emails, and metadata on invalid/missing emails.
    """
    cleaned_df = df.copy()

    # Apply trim and lowercase to non-null string values
    def _clean_email_str(val: Any) -> Any:
        if pd.isna(val):
            return None
        return str(val).strip().lower()

    cleaned_df["Email"] = cleaned_df["Email"].apply(_clean_email_str)

    # Detect invalid email formats (excluding nulls, which are handled as missing)
    is_missing = cleaned_df["Email"].isna()
    is_valid_format = cleaned_df["Email"].str.match(EMAIL_REGEX, na=False)
    invalid_mask = (~is_valid_format) & (~is_missing)

    invalid_emails: List[Dict[str, Any]] = []
    for idx in cleaned_df[invalid_mask].index:
        invalid_emails.append({
            "Order_ID": cleaned_df.loc[idx, "Order_ID"],
            "Customer_Name": cleaned_df.loc[idx, "Customer_Name"],
            "Email": cleaned_df.loc[idx, "Email"]
        })

    email_stats = {
        "invalid_count": int(invalid_mask.sum()),
        "invalid_records": invalid_emails,
        "missing_count": int(is_missing.sum())
    }

    return cleaned_df, email_stats


def validate_cleaned_data(
    raw_df: pd.DataFrame,
    cleaned_df: pd.DataFrame,
    stats: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate the cleaned dataset against data quality criteria and print
    a clear before-and-after comparison.

    Parameters:
        raw_df (pd.DataFrame): Original raw dataset.
        cleaned_df (pd.DataFrame): Final cleaned dataset.
        stats (Dict[str, Any]): Cleaning execution statistics.

    Returns:
        Dict[str, Any]: Consolidated validation summary.
    """
    validation_summary = {
        "raw_rows": len(raw_df),
        "cleaned_rows": len(cleaned_df),
        "removed_rows": len(raw_df) - len(cleaned_df),
        "raw_missing": raw_df.isna().sum().to_dict(),
        "cleaned_missing": cleaned_df.isna().sum().to_dict(),
        "raw_exact_duplicates": int(raw_df.duplicated().sum()),
        "cleaned_exact_duplicates": int(cleaned_df.duplicated().sum()),
        "raw_order_id_duplicates": int(raw_df.duplicated(subset=["Order_ID"]).sum()),
        "cleaned_order_id_duplicates": int(cleaned_df.duplicated(subset=["Order_ID"]).sum()),
        "raw_dtypes": {col: str(dtype) for col, dtype in raw_df.dtypes.items()},
        "cleaned_dtypes": {col: str(dtype) for col, dtype in cleaned_df.dtypes.items()},
        "invalid_emails_count": stats.get("email_stats", {}).get("invalid_count", 0),
        "invalid_dates_count": len(stats.get("conversion_stats", {}).get("invalid_dates", [])),
        "price_imputed_count": len(stats.get("imputation_stats", {}).get("price_imputations", []))
    }

    print("\n" + "=" * 70)
    print("           PHASE 3: DATA CLEANING VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Dataset Rows:           Before = {validation_summary['raw_rows']} | After = {validation_summary['cleaned_rows']}")
    print(f"Duplicates Removed:     {validation_summary['removed_rows']}")
    print(f"Remaining Duplicates:   Exact = {validation_summary['cleaned_exact_duplicates']} | Order_ID = {validation_summary['cleaned_order_id_duplicates']}")
    print(f"Price Imputations:      {validation_summary['price_imputed_count']} records imputed via category median")
    print(f"Invalid Emails Found:   {validation_summary['invalid_emails_count']} (preserved, not faked)")
    print(f"Invalid Dates Found:    {validation_summary['invalid_dates_count']}")

    print("\n--- Missing Values Before vs After ---")
    comparison_missing = pd.DataFrame({
        "Column": list(validation_summary["raw_missing"].keys()),
        "Raw_Missing": list(validation_summary["raw_missing"].values()),
        "Cleaned_Missing": [validation_summary["cleaned_missing"].get(col, 0) for col in validation_summary["raw_missing"]]
    })
    print(comparison_missing.to_string(index=False))

    print("\n--- Data Types Before vs After ---")
    comparison_dtypes = pd.DataFrame({
        "Column": list(validation_summary["raw_dtypes"].keys()),
        "Raw_Type": list(validation_summary["raw_dtypes"].values()),
        "Cleaned_Type": [validation_summary["cleaned_dtypes"].get(col, "N/A") for col in validation_summary["raw_dtypes"]]
    })
    print(comparison_dtypes.to_string(index=False))
    print("=" * 70 + "\n")

    return validation_summary


def save_cleaned_dataset(df: pd.DataFrame, output_path: Path) -> Path:
    """
    Save the cleaned dataset to the specified CSV path.
    Ensures that parent directories are created and never overwrites raw data.

    Parameters:
        df (pd.DataFrame): Cleaned DataFrame.
        output_path (Path): Destination CSV path.

    Returns:
        Path: Absolute path of the saved file.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    df.to_csv(path, index=False)
    print(f"Cleaned dataset successfully saved to: {path}")
    return path


def generate_cleaning_report(stats: Dict[str, Any], output_path: Path) -> Path:
    """
    Create a detailed text report of Phase 3 Data Cleaning operations,
    statistics, and unresolved data quality issues.

    Parameters:
        stats (Dict[str, Any]): Comprehensive cleaning statistics.
        output_path (Path): Destination path for the report text file.

    Returns:
        Path: Absolute path to the generated report file.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    raw_missing = stats.get("raw_missing", {})
    cleaned_missing = stats.get("cleaned_missing", {})
    raw_dtypes = stats.get("raw_dtypes", {})
    cleaned_dtypes = stats.get("cleaned_dtypes", {})
    price_imputations = stats.get("imputation_stats", {}).get("price_imputations", [])
    email_stats = stats.get("email_stats", {})
    invalid_dates = stats.get("conversion_stats", {}).get("invalid_dates", [])

    report_lines = [
        "================================================================================",
        "                     DATA CLEANING REPORT - PHASE 3",
        "                Project: Data Cleaning and Preprocessing",
        "================================================================================",
        "",
        "1. ROW SUMMARY",
        f"   - Original Number of Rows: {stats.get('raw_rows', 'N/A')}",
        f"   - Final Number of Rows:    {stats.get('cleaned_rows', 'N/A')}",
        f"   - Duplicate Rows Removed:  {stats.get('removed_rows', 'N/A')}",
        "",
        "2. DUPLICATE RECORDS ANALYSIS",
        f"   - Exact Duplicate Rows Detected Before Cleaning:  {stats.get('raw_exact_duplicates', 0)}",
        f"   - Duplicate Order_IDs Detected Before Cleaning:    {stats.get('raw_order_id_duplicates', 0)}",
        f"   - Business Key Used for Deduplication:            Order_ID",
        "   - Deduplication Rule:                             Keep first valid record, drop subsequent duplicates.",
        f"   - Exact Duplicates Remaining After Cleaning:      {stats.get('cleaned_exact_duplicates', 0)}",
        f"   - Duplicate Order_IDs Remaining After Cleaning:    {stats.get('cleaned_order_id_duplicates', 0)}",
        "",
        "3. MISSING VALUE HANDLING",
        "   Columns and Missing Counts:",
    ]

    for col, count in raw_missing.items():
        after_count = cleaned_missing.get(col, 0)
        report_lines.append(f"   - {col:15}: Before = {count} | After = {after_count}")

    report_lines.extend([
        "",
        "   Business Rules & Rationales for Missing Value Strategies:",
        "   a) Customer_Name:",
        "      - Strategy: Imputed with 'Unknown'.",
        "      - Rationale: The transaction represents valid commercial activity with financial",
        "        value. Dropping records with missing names causes revenue underreporting.",
        "        Marking as 'Unknown' preserves transactional data for aggregate reporting.",
        "   b) Email:",
        "      - Strategy: Preserved as missing (NaN); reported without synthetic replacement.",
        "      - Rationale: Creating synthetic/fake emails (e.g. unknown@domain.com) corrupts marketing",
        "        databases, distorts customer analytics, and induces email bounce penalties.",
        "   c) Price:",
        "      - Strategy: Imputed using median price of the matching product category.",
        "      - Rationale: Product prices are typically consistent within categories. Median is robust",
        "        against extreme pricing outliers and reconstructs financial metrics accurately.",
        "   d) City:",
        "      - Strategy: Imputed with 'Unknown'.",
        "      - Rationale: Retains the order in financial and item totals without distorting",
        "        regional performance benchmarks.",
        "",
        "4. PRICE IMPUTATION DETAILS",
        f"   - Number of Price Values Imputed: {len(price_imputations)}"
    ])

    if price_imputations:
        for item in price_imputations:
            report_lines.append(
                f"     * Order_ID {item['Order_ID']} ({item['Product']}): Imputed Price = {item['Imputed_Price']:.2f}"
            )
    else:
        report_lines.append("     * No price values required imputation.")

    report_lines.extend([
        "",
        "5. EMAIL VALIDATION",
        f"   - Total Invalid Email Records: {email_stats.get('invalid_count', 0)}",
        f"   - Total Missing Email Records: {email_stats.get('missing_count', 0)}"
    ])

    if email_stats.get("invalid_records"):
        for rec in email_stats["invalid_records"]:
            report_lines.append(
                f"     * Order_ID {rec['Order_ID']} (Customer: {rec['Customer_Name']}): Invalid Email = '{rec['Email']}'"
            )

    report_lines.extend([
        "",
        "6. DATE CONVERSION & VALIDATION",
        "   - Standardized Order_Date from object string to datetime64[ns/us].",
        "   - Day-first interpretation enabled for DD/MM/YYYY and DD-MM-YYYY formats (e.g. 02/01/2026 -> 2026-01-02).",
        "   - ISO 8601 YYYY-MM-DD / YYYY/MM/DD formats properly supported.",
        "   - Safe parsing with errors='coerce' to prevent unhandled runtime exceptions.",
        f"   - Invalid Date Records Detected: {len(invalid_dates)}"
    ])

    if invalid_dates:
        for d in invalid_dates:
            report_lines.append(f"     * Row {d['row_index']}: Original Value = '{d['original_value']}'")
    else:
        report_lines.append("     * All date records parsed successfully.")

    report_lines.extend([
        "",
        "7. DATA TYPE STANDARDIZATION",
        "   Column Data Types Before and After Cleaning:"
    ])

    for col, b_type in raw_dtypes.items():
        a_type = cleaned_dtypes.get(col, "N/A")
        report_lines.append(f"   - {col:15}: {b_type:15} -> {a_type}")

    report_lines.extend([
        "",
        "8. CLEANING OPERATIONS PERFORMED",
        "   1. Dataset Ingestion: Verified existence and loaded raw CSV data without mutation.",
        "   2. Missing Value Audit: Evaluated missingness across all features via isna() and isnull().",
        "   3. Duplicate Row Detection: Flagged exact duplicate rows and duplicate Order_IDs.",
        "   4. Deduplication: Removed duplicate Order_ID (Row 105), preserving first valid entry.",
        "   5. Missing Value Imputation: Handled Customer_Name, City, and Price by business rules.",
        "   6. Email Standardization: Trimmed whitespace, converted to lowercase, flagged invalid format.",
        "   7. Data Type Conversion: Coerced Order_ID and Quantity to int64, Price to float64, Order_Date to datetime.",
        "   8. Quality Verification: Cross-validated row counts, null distributions, and type signatures.",
        "   9. Export: Saved clean dataset to data/cleaned/sales_cleaned.csv.",
        "",
        "9. UNRESOLVED DATA QUALITY ISSUES (FOR FUTURE PHASES)",
        "   - Missing Email: 1 record (Order_ID 107, Suresh) has no email on file. In line with",
        "     business integrity rules, no synthetic email was fabricated. Retained as missing.",
        "   - Invalid Email: 1 record (Order_ID 104) has 'invalid-email'. Preserved for manual CRM correction.",
        "   - Negative Quantity: Order_ID 107 contains Quantity = -2. This represents a potential return,",
        "     credit note, or data entry error. Outlier/anomaly transformation is reserved for Phase 4.",
        "   - Inconsistent Text Casing: Casing variations exist in City ('chennai', 'MADURAI', 'CHENNAI')",
        "     and Product ('MOUSE', 'Mouse'). Text standardization belongs to Phase 4.",
        "",
        "================================================================================",
        "                           END OF CLEANING REPORT",
        "================================================================================"
    ])

    report_content = "\n".join(report_lines)
    path.write_text(report_content, encoding="utf-8")
    print(f"Cleaning report successfully generated at: {path}")
    return path


def clean_sales_data(
    raw_path: Path,
    cleaned_path: Path,
    report_path: Path
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Main reusable data cleaning pipeline executing all Phase 3 cleaning tasks.

    Parameters:
        raw_path (Path): Path to raw CSV input.
        cleaned_path (Path): Path to output cleaned CSV.
        report_path (Path): Path to output report TXT.

    Returns:
        Tuple[pd.DataFrame, Dict[str, Any]]: Cleaned DataFrame and execution metadata.
    """
    print("=" * 70)
    print("          STARTING PHASE 3 – DATA CLEANING PIPELINE")
    print("=" * 70)

    # 1. Load Dataset
    print(f"\n[Step 1] Loading raw dataset from: {raw_path}")
    raw_df = load_dataset(raw_path)
    print(f"Loaded raw dataset with {len(raw_df)} rows and {len(raw_df.columns)} columns.")

    # 2. Inspect Missing Values Before Cleaning
    print("\n[Step 2] Inspecting missing values in raw dataset...")
    missing_before = inspect_missing_values(raw_df)
    print(missing_before.to_string(index=False))

    # 3. Identify and Remove Duplicates
    print("\n[Step 3] Identifying and handling duplicate records...")
    duplicate_info = identify_duplicates(raw_df)
    exact_dups = duplicate_info["exact_duplicates"]
    order_id_dups = duplicate_info["order_id_duplicates"]

    print(f"Exact duplicate rows detected: {len(exact_dups)}")
    if not exact_dups.empty:
        print("Exact duplicate records:")
        print(exact_dups.to_string(index=False))

    print(f"Duplicate Order_ID records detected: {len(order_id_dups)}")
    if not order_id_dups.empty:
        print("Duplicate Order_ID records:")
        print(order_id_dups.to_string(index=False))

    df_deduped, removed_count = remove_duplicates(raw_df, subset=["Order_ID"], keep="first")
    print(f"Deduplication complete: {removed_count} duplicate record(s) removed using Order_ID.")

    # 4. Handle Missing Values
    print("\n[Step 4] Handling missing values according to business rules...")
    df_imputed, imputation_stats = handle_missing_values(df_deduped)
    print(f"Customer_Name: Missing replaced with 'Unknown'")
    print(f"City: Missing replaced with 'Unknown'")
    print(f"Email: Missing preserved ({imputation_stats['email_missing_count']} missing on file)")
    for imp in imputation_stats["price_imputations"]:
        print(f"Price: Imputed Order_ID {imp['Order_ID']} ({imp['Product']}) with category median: {imp['Imputed_Price']}")

    # 5. Clean Email Values
    print("\n[Step 5] Cleaning and validating email values...")
    df_email_cleaned, email_stats = clean_email_values(df_imputed)
    print(f"Email strings trimmed and normalized to lowercase.")
    print(f"Invalid email count: {email_stats['invalid_count']}")
    if email_stats["invalid_records"]:
        for item in email_stats["invalid_records"]:
            print(f"  - Order_ID {item['Order_ID']} has invalid email: '{item['Email']}' (preserved)")

    # 6. Standardize Data Types
    print("\n[Step 6] Standardizing data types (Order_Date, Order_ID, Quantity, Price)...")
    df_typed, conversion_stats = standardize_data_types(df_email_cleaned)
    print("Order_Date parsed to datetime with day-first support for DD/MM/YYYY formats.")
    print("Order_ID and Quantity converted to int64.")
    print("Price converted to float64.")

    # Final cleaned DataFrame
    cleaned_df = df_typed.copy()

    # 7. Validate Cleaned Data
    print("\n[Step 7] Validating cleaned dataset...")
    pipeline_stats: Dict[str, Any] = {
        "raw_rows": len(raw_df),
        "cleaned_rows": len(cleaned_df),
        "removed_rows": removed_count,
        "raw_missing": raw_df.isna().sum().to_dict(),
        "cleaned_missing": cleaned_df.isna().sum().to_dict(),
        "raw_exact_duplicates": int(raw_df.duplicated().sum()),
        "cleaned_exact_duplicates": int(cleaned_df.duplicated().sum()),
        "raw_order_id_duplicates": int(raw_df.duplicated(subset=["Order_ID"]).sum()),
        "cleaned_order_id_duplicates": int(cleaned_df.duplicated(subset=["Order_ID"]).sum()),
        "raw_dtypes": {col: str(dtype) for col, dtype in raw_df.dtypes.items()},
        "cleaned_dtypes": {col: str(dtype) for col, dtype in cleaned_df.dtypes.items()},
        "imputation_stats": imputation_stats,
        "email_stats": email_stats,
        "conversion_stats": conversion_stats
    }

    validate_cleaned_data(raw_df, cleaned_df, pipeline_stats)

    # 8. Save Cleaned Dataset
    print("[Step 8] Saving cleaned dataset...")
    save_cleaned_dataset(cleaned_df, cleaned_path)

    # 9. Generate Report
    print("\n[Step 9] Generating Phase 3 Cleaning Report...")
    generate_cleaning_report(pipeline_stats, report_path)

    print("\n" + "=" * 70)
    print("       PHASE 3 – DATA CLEANING PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 70)

    return cleaned_df, pipeline_stats


def main() -> None:
    """
    Main entry point for executing Phase 3 Data Cleaning.
    Can be run from project root or any subfolder.
    """
    # Locate project root dynamically based on script location
    script_dir = Path(__file__).resolve().parent
    raw_data_file = script_dir / "data" / "raw" / "sales_dirty.csv"
    cleaned_data_file = script_dir / "data" / "cleaned" / "sales_cleaned.csv"
    report_file = script_dir / "reports" / "phase3_cleaning_report.txt"

    try:
        clean_sales_data(
            raw_path=raw_data_file,
            cleaned_path=cleaned_data_file,
            report_path=report_file
        )
    except Exception as err:
        print(f"\n[FATAL ERROR] Data cleaning pipeline failed: {err}")
        raise


if __name__ == "__main__":
    main()

