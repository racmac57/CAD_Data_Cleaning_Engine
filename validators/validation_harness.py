"""
Validation Harness - Pre-run validation checks

Performs comprehensive validation before running the CAD data correction pipeline:
- Environment checks (dependencies, memory, disk space)
- Schema validation
- File existence checks
- Configuration validation
"""

import sys
import os
import psutil
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Import utilities
sys.path.append(str(Path(__file__).parent.parent))

from utils.logger import setup_logger, log_validation_result
from utils.validate_schema import SchemaValidator
from utils.hash_utils import FileHashManager


class ValidationHarness:
    """Orchestrates all pre-run validation checks."""

    def __init__(self, config_path: str = "config/config.yml"):
        """
        Initialize validation harness.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()

        self.logger = setup_logger(
            name="ValidationHarness",
            log_file=self.config['paths']['log_file'],
            level=logging.INFO,
            console_output=True
        )

        self.validation_results = []
        self.passed = 0
        self.failed = 0

    def _load_config(self) -> Dict:
        """Load configuration file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"ERROR: Could not load config file: {e}")
            sys.exit(1)

    def run_all_validations(self) -> bool:
        """
        Run all validation checks.

        Returns:
            True if all validations passed, False otherwise
        """
        self.logger.info("=" * 80)
        self.logger.info("CAD DATA CORRECTION FRAMEWORK - VALIDATION HARNESS")
        self.logger.info("=" * 80)
        self.logger.info(f"Configuration: {self.config_path}")
        self.logger.info("")

        # Run validation checks
        self._check_environment()
        self._check_dependencies()
        self._check_files_exist()
        self._check_configuration()
        self._check_input_schema()
        self._check_disk_space()
        self._check_memory()

        # Report results
        self._report_results()

        return self.failed == 0

    def _add_result(self, check_name: str, passed: bool, message: str = ""):
        """Add validation result."""
        self.validation_results.append({
            'check': check_name,
            'passed': passed,
            'message': message
        })

        if passed:
            self.passed += 1
        else:
            self.failed += 1

        log_validation_result(self.logger, check_name, passed, message)

    def _check_environment(self):
        """Check environment requirements."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Environment Checks")
        self.logger.info("-" * 80)

        # Python version
        python_version = sys.version_info
        required_version = (3, 8)

        if python_version >= required_version:
            self._add_result(
                "Python Version",
                True,
                f"Python {python_version.major}.{python_version.minor}.{python_version.micro}"
            )
        else:
            self._add_result(
                "Python Version",
                False,
                f"Python {python_version.major}.{python_version.minor} (requires >= 3.8)"
            )

        # Operating system
        platform = sys.platform
        self._add_result(
            "Operating System",
            True,
            f"Platform: {platform}"
        )

        # Working directory
        cwd = Path.cwd()
        self._add_result(
            "Working Directory",
            True,
            f"{cwd}"
        )

    def _check_dependencies(self):
        """Check required Python packages."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Dependency Checks")
        self.logger.info("-" * 80)

        required_packages = [
            'pandas',
            'numpy',
            'yaml',
            'openpyxl',
            'psutil'
        ]

        for package in required_packages:
            try:
                __import__(package)
                # Get version if available
                try:
                    module = __import__(package)
                    version = getattr(module, '__version__', 'unknown')
                    self._add_result(
                        f"Package: {package}",
                        True,
                        f"Version {version}"
                    )
                except:
                    self._add_result(
                        f"Package: {package}",
                        True,
                        "Installed"
                    )
            except ImportError:
                self._add_result(
                    f"Package: {package}",
                    False,
                    "Not installed"
                )

    def _check_files_exist(self):
        """Check that required files exist."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("File Existence Checks")
        self.logger.info("-" * 80)

        # Check input file
        input_file = Path(self.config['paths']['input_file'])
        if input_file.exists():
            size_mb = input_file.stat().st_size / 1024 / 1024
            self._add_result(
                "Input File",
                True,
                f"{input_file.name} ({size_mb:.2f} MB)"
            )
        else:
            self._add_result(
                "Input File",
                False,
                f"Not found: {input_file}"
            )

        # Check correction files (optional)
        if 'corrections' in self.config['paths']:
            for correction_type, correction_file in self.config['paths']['corrections'].items():
                if correction_file:
                    correction_path = Path(correction_file)
                    exists = correction_path.exists()
                    self._add_result(
                        f"Correction File ({correction_type})",
                        exists or not self.config['processing'].get(f'apply_{correction_type}_corrections', False),
                        f"{correction_path.name} {'exists' if exists else 'not found (optional)'}"
                    )

        # Check reference files
        if 'reference' in self.config['paths']:
            for ref_type, ref_file in self.config['paths']['reference'].items():
                if ref_file:
                    ref_path = Path(ref_file)
                    exists = ref_path.exists()
                    self._add_result(
                        f"Reference File ({ref_type})",
                        exists or True,  # Reference files are optional
                        f"{ref_path.name} {'exists' if exists else 'not found (optional)'}"
                    )

    def _check_configuration(self):
        """Validate configuration settings."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Configuration Validation")
        self.logger.info("-" * 80)

        # Check required sections
        required_sections = [
            'project',
            'paths',
            'processing',
            'validation',
            'export',
            'logging'
        ]

        for section in required_sections:
            exists = section in self.config
            self._add_result(
                f"Config Section: {section}",
                exists,
                "Present" if exists else "Missing"
            )

        # Validate quality weights sum to 100
        if 'quality_weights' in self.config:
            total_weight = sum(self.config['quality_weights'].values())
            is_valid = abs(total_weight - 100) < 0.01

            self._add_result(
                "Quality Weights",
                is_valid,
                f"Total: {total_weight} (should be 100)"
            )

        # Check log level is valid
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        log_level = self.config['logging']['level']
        is_valid = log_level in valid_log_levels

        self._add_result(
            "Log Level",
            is_valid,
            f"{log_level} {'(valid)' if is_valid else '(invalid)'}"
        )

    def _check_input_schema(self):
        """Validate input file schema."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Input Schema Validation")
        self.logger.info("-" * 80)

        input_file = Path(self.config['paths']['input_file'])

        if not input_file.exists():
            self._add_result(
                "Schema Validation",
                False,
                "Input file not found"
            )
            return

        try:
            # Load sample of data for schema check
            if input_file.suffix == '.xlsx':
                df = pd.read_excel(input_file, nrows=100)
            else:
                df = pd.read_csv(input_file, nrows=100, encoding='utf-8-sig')

            # Validate schema
            validator = SchemaValidator(strict=False)
            result = validator.validate(df)

            report = validator.get_validation_report()

            self._add_result(
                "Schema Validation",
                result,
                f"Errors: {report['error_count']}, Warnings: {report['warning_count']}"
            )

        except Exception as e:
            self._add_result(
                "Schema Validation",
                False,
                f"Error: {str(e)}"
            )

    def _check_disk_space(self):
        """Check available disk space."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Disk Space Check")
        self.logger.info("-" * 80)

        try:
            # Get disk usage for output directory
            output_dir = Path(self.config['paths']['output_dir'])
            output_dir.mkdir(parents=True, exist_ok=True)

            disk_usage = psutil.disk_usage(str(output_dir))
            free_gb = disk_usage.free / (1024 ** 3)
            required_gb = 5.0  # Require at least 5 GB free

            self._add_result(
                "Disk Space",
                free_gb >= required_gb,
                f"{free_gb:.2f} GB free (requires {required_gb} GB)"
            )

        except Exception as e:
            self._add_result(
                "Disk Space",
                False,
                f"Error checking disk space: {e}"
            )

    def _check_memory(self):
        """Check available memory."""
        self.logger.info("\n" + "-" * 80)
        self.logger.info("Memory Check")
        self.logger.info("-" * 80)

        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024 ** 3)
            total_gb = memory.total / (1024 ** 3)
            required_gb = 2.0  # Require at least 2 GB available

            self._add_result(
                "Available Memory",
                available_gb >= required_gb,
                f"{available_gb:.2f} GB available of {total_gb:.2f} GB total (requires {required_gb} GB)"
            )

            # Check memory usage percentage
            memory_pct = memory.percent
            self._add_result(
                "Memory Usage",
                memory_pct < 90,
                f"{memory_pct:.1f}% used"
            )

        except Exception as e:
            self._add_result(
                "Memory Check",
                False,
                f"Error checking memory: {e}"
            )

    def _report_results(self):
        """Report validation results summary."""
        self.logger.info("\n" + "=" * 80)
        self.logger.info("VALIDATION SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Total Checks: {self.passed + self.failed}")
        self.logger.info(f"Passed: {self.passed}")
        self.logger.info(f"Failed: {self.failed}")
        self.logger.info("")

        if self.failed > 0:
            self.logger.error("VALIDATION FAILED - Please fix the errors above before running the pipeline")
            self.logger.info("")
            self.logger.info("Failed Checks:")
            for result in self.validation_results:
                if not result['passed']:
                    self.logger.error(f"  ✗ {result['check']}: {result['message']}")
        else:
            self.logger.info("✓ ALL VALIDATIONS PASSED - Ready to run pipeline")

        self.logger.info("=" * 80)

    def get_validation_report(self) -> Dict:
        """
        Get structured validation report.

        Returns:
            Dictionary with validation results
        """
        return {
            'total_checks': self.passed + self.failed,
            'passed': self.passed,
            'failed': self.failed,
            'success': self.failed == 0,
            'results': self.validation_results.copy()
        }


def validate_environment(config_path: str = "config/config.yml") -> bool:
    """
    Convenience function to run all validations.

    Args:
        config_path: Path to configuration file

    Returns:
        True if all validations passed
    """
    harness = ValidationHarness(config_path)
    return harness.run_all_validations()


if __name__ == "__main__":
    """Run validation harness from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="CAD Data Correction Framework - Validation Harness")
    parser.add_argument(
        '--config',
        type=str,
        default="config/config.yml",
        help="Path to configuration file"
    )

    args = parser.parse_args()

    # Run validations
    success = validate_environment(args.config)

    # Exit with appropriate code
    sys.exit(0 if success else 1)
