"""
Schema validation utilities for CAD data processing pipeline.

Validates that input data contains all required columns and has
expected data types before processing begins.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from enum import Enum
import logging


class DataType(Enum):
    """Supported data types for schema validation."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    OBJECT = "object"


class SchemaValidator:
    """Validates DataFrame schemas against expected structure."""

    # Expected CAD schema (configurable)
    CAD_SCHEMA = {
        # Core identifying fields
        "ReportNumberNew": {"type": DataType.STRING, "nullable": False, "description": "CAD case number"},

        # Incident details
        "Incident": {"type": DataType.STRING, "nullable": True, "description": "Incident type"},
        "Disposition": {"type": DataType.STRING, "nullable": True, "description": "Call disposition"},
        "How Reported": {"type": DataType.STRING, "nullable": True, "description": "How call was reported"},

        # Location fields
        "FullAddress2": {"type": DataType.STRING, "nullable": True, "description": "Full address"},
        "PDZone": {"type": DataType.STRING, "nullable": True, "description": "Police zone"},
        "Grid": {"type": DataType.STRING, "nullable": True, "description": "Map grid"},

        # Time fields
        "Time of Call": {"type": DataType.DATETIME, "nullable": True, "description": "Call time"},
        "Time Dispatched": {"type": DataType.DATETIME, "nullable": True, "description": "Dispatch time"},
        "Time Out": {"type": DataType.DATETIME, "nullable": True, "description": "Unit out time"},
        "Time In": {"type": DataType.DATETIME, "nullable": True, "description": "Unit in time"},
        "Hour": {"type": DataType.STRING, "nullable": True, "description": "Hour of call"},

        # Officer fields
        "Officer": {"type": DataType.STRING, "nullable": True, "description": "Officer assigned"},

        # Duration fields
        "Time Spent": {"type": DataType.OBJECT, "nullable": True, "description": "Time spent on call"},
        "Time Response": {"type": DataType.OBJECT, "nullable": True, "description": "Response time"},

        # Text fields
        "CADNotes": {"type": DataType.STRING, "nullable": True, "description": "CAD notes"},
        "Narrative": {"type": DataType.STRING, "nullable": True, "description": "Narrative text"},

        # Response classification
        "Response Type": {"type": DataType.STRING, "nullable": True, "description": "Response type"},
    }

    def __init__(self, schema: Optional[Dict] = None, strict: bool = False):
        """
        Initialize schema validator.

        Args:
            schema: Custom schema dictionary (uses CAD_SCHEMA if None)
            strict: If True, fail on any schema violations. If False, warn only.
        """
        self.schema = schema or self.CAD_SCHEMA
        self.strict = strict
        self.logger = logging.getLogger(__name__)
        self.validation_errors = []
        self.validation_warnings = []

    def validate(self, df: pd.DataFrame) -> bool:
        """
        Validate DataFrame against schema.

        Args:
            df: DataFrame to validate

        Returns:
            True if validation passed, False otherwise
        """
        self.validation_errors = []
        self.validation_warnings = []

        self.logger.info("=" * 80)
        self.logger.info("SCHEMA VALIDATION")
        self.logger.info("=" * 80)
        self.logger.info(f"DataFrame shape: {df.shape[0]:,} rows × {df.shape[1]} columns")
        self.logger.info(f"Schema fields: {len(self.schema)} required")
        self.logger.info(f"Strict mode: {self.strict}")

        # Check for required columns
        missing_cols = self._check_required_columns(df)

        # Check data types
        type_issues = self._check_data_types(df)

        # Check nullable constraints
        nullable_issues = self._check_nullable_constraints(df)

        # Check for extra columns
        extra_cols = self._check_extra_columns(df)

        # Report results
        self._report_results()

        # Determine pass/fail
        has_errors = len(self.validation_errors) > 0

        if has_errors:
            if self.strict:
                self.logger.error("VALIDATION FAILED (strict mode)")
                return False
            else:
                self.logger.warning("VALIDATION COMPLETED WITH ERRORS (non-strict mode)")
                return True
        else:
            self.logger.info("VALIDATION PASSED")
            return True

    def _check_required_columns(self, df: pd.DataFrame) -> List[str]:
        """Check if all required columns are present."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Checking Required Columns")
        self.logger.info("-" * 80)

        missing_columns = []
        df_columns = set(df.columns)

        for col_name, col_spec in self.schema.items():
            if col_name not in df_columns:
                missing_columns.append(col_name)
                error_msg = f"Missing required column: '{col_name}' ({col_spec['description']})"
                self.validation_errors.append(error_msg)
                self.logger.error(f"  ✗ {error_msg}")
            else:
                self.logger.info(f"  ✓ {col_name}")

        if not missing_columns:
            self.logger.info(f"\nAll {len(self.schema)} required columns present")

        return missing_columns

    def _check_data_types(self, df: pd.DataFrame) -> List[str]:
        """Check if columns have expected data types."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Checking Data Types")
        self.logger.info("-" * 80)

        type_issues = []

        for col_name, col_spec in self.schema.items():
            if col_name not in df.columns:
                continue  # Already reported as missing

            expected_type = col_spec["type"]
            actual_dtype = df[col_name].dtype

            # Map pandas dtypes to our DataType enum
            is_valid = self._is_type_compatible(actual_dtype, expected_type)

            if is_valid:
                self.logger.info(f"  ✓ {col_name}: {actual_dtype} (expected {expected_type.value})")
            else:
                warning_msg = f"{col_name}: type mismatch - got {actual_dtype}, expected {expected_type.value}"
                type_issues.append(warning_msg)
                self.validation_warnings.append(warning_msg)
                self.logger.warning(f"  ! {warning_msg}")

        return type_issues

    def _is_type_compatible(self, actual_dtype, expected_type: DataType) -> bool:
        """Check if actual pandas dtype is compatible with expected DataType."""
        dtype_str = str(actual_dtype).lower()

        if expected_type == DataType.STRING:
            return 'object' in dtype_str or 'string' in dtype_str
        elif expected_type == DataType.INTEGER:
            return 'int' in dtype_str
        elif expected_type == DataType.FLOAT:
            return 'float' in dtype_str or 'int' in dtype_str
        elif expected_type == DataType.DATETIME:
            return 'datetime' in dtype_str
        elif expected_type == DataType.BOOLEAN:
            return 'bool' in dtype_str
        elif expected_type == DataType.OBJECT:
            return True  # Object type is flexible

        return False

    def _check_nullable_constraints(self, df: pd.DataFrame) -> List[str]:
        """Check nullable constraints."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Checking Nullable Constraints")
        self.logger.info("-" * 80)

        nullable_issues = []

        for col_name, col_spec in self.schema.items():
            if col_name not in df.columns:
                continue  # Already reported as missing

            if not col_spec.get("nullable", True):
                null_count = df[col_name].isnull().sum()

                if null_count > 0:
                    error_msg = f"{col_name}: contains {null_count:,} null values but should not be nullable"
                    nullable_issues.append(error_msg)
                    self.validation_errors.append(error_msg)
                    self.logger.error(f"  ✗ {error_msg}")
                else:
                    self.logger.info(f"  ✓ {col_name}: no null values")
            else:
                null_count = df[col_name].isnull().sum()
                null_pct = (null_count / len(df)) * 100
                if null_count > 0:
                    self.logger.info(f"  ~ {col_name}: {null_count:,} null values ({null_pct:.1f}%)")

        return nullable_issues

    def _check_extra_columns(self, df: pd.DataFrame) -> List[str]:
        """Check for columns not in schema."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Checking for Extra Columns")
        self.logger.info("-" * 80)

        schema_columns = set(self.schema.keys())
        df_columns = set(df.columns)
        extra_columns = df_columns - schema_columns

        if extra_columns:
            self.logger.info(f"Found {len(extra_columns)} extra columns not in schema:")
            for col in sorted(extra_columns):
                self.logger.info(f"  + {col}")
                self.validation_warnings.append(f"Extra column: {col}")
        else:
            self.logger.info("No extra columns found")

        return list(extra_columns)

    def _report_results(self):
        """Report validation results summary."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("VALIDATION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Errors: {len(self.validation_errors)}")
        self.logger.info(f"Warnings: {len(self.validation_warnings)}")

        if self.validation_errors:
            self.logger.error("\nERRORS:")
            for error in self.validation_errors:
                self.logger.error(f"  • {error}")

        if self.validation_warnings:
            self.logger.warning("\nWARNINGS:")
            for warning in self.validation_warnings:
                self.logger.warning(f"  • {warning}")

        self.logger.info("=" * 80)

    def get_validation_report(self) -> Dict:
        """
        Get structured validation report.

        Returns:
            Dictionary with validation results
        """
        return {
            "passed": len(self.validation_errors) == 0 or not self.strict,
            "errors": self.validation_errors.copy(),
            "warnings": self.validation_warnings.copy(),
            "error_count": len(self.validation_errors),
            "warning_count": len(self.validation_warnings),
            "strict_mode": self.strict
        }


def validate_cad_schema(df: pd.DataFrame, strict: bool = False) -> bool:
    """
    Convenience function to validate CAD schema.

    Args:
        df: DataFrame to validate
        strict: If True, fail on any violations

    Returns:
        True if validation passed, False otherwise
    """
    validator = SchemaValidator(strict=strict)
    return validator.validate(df)


def create_custom_schema(field_definitions: Dict) -> Dict:
    """
    Create custom schema from field definitions.

    Args:
        field_definitions: Dict mapping column names to specs

    Returns:
        Schema dictionary
    """
    schema = {}
    for col_name, spec in field_definitions.items():
        schema[col_name] = {
            "type": spec.get("type", DataType.STRING),
            "nullable": spec.get("nullable", True),
            "description": spec.get("description", "")
        }
    return schema


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s'
    )

    # Example: Create test DataFrame
    test_df = pd.DataFrame({
        "ReportNumberNew": ["24-123456", "24-123457"],
        "Incident": ["Test Incident", "Another Incident"],
        "Time of Call": pd.to_datetime(["2024-01-01 10:00", "2024-01-01 11:00"])
    })

    # Validate (will show missing columns)
    validator = SchemaValidator(strict=False)
    result = validator.validate(test_df)

    # Get report
    report = validator.get_validation_report()
    print(f"\nValidation result: {result}")
    print(f"Errors: {report['error_count']}")
    print(f"Warnings: {report['warning_count']}")
