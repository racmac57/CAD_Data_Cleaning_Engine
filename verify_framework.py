"""
Framework Verification Script

Verifies that all components of the CAD Data Correction Framework
are properly installed and configured.

Usage:
    python verify_framework.py
"""

import sys
from pathlib import Path
from typing import List, Tuple

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text: str):
    """Print section header."""
    print("\n" + "=" * 80)
    print(f"{BLUE}{text}{RESET}")
    print("=" * 80)


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✓{RESET} {text}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}✗{RESET} {text}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{YELLOW}⚠{RESET} {text}")


def check_python_version() -> bool:
    """Check Python version is 3.8+."""
    version = sys.version_info
    if version >= (3, 8):
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor} (requires >= 3.8)")
        return False


def check_dependencies() -> Tuple[int, int]:
    """Check required Python packages."""
    required = {
        'pandas': '1.5.0',
        'numpy': '1.23.0',
        'yaml': '6.0',
        'openpyxl': '3.0.10',
        'psutil': '5.9.0'
    }

    passed = 0
    failed = 0

    for package, min_version in required.items():
        try:
            if package == 'yaml':
                import yaml
                module = yaml
            else:
                module = __import__(package)

            version = getattr(module, '__version__', 'unknown')
            print_success(f"{package} (version {version})")
            passed += 1
        except ImportError:
            print_error(f"{package} not installed")
            failed += 1

    return passed, failed


def check_directory_structure() -> Tuple[int, int]:
    """Check that required directories exist."""
    required_dirs = [
        'processors',
        'validators',
        'utils',
        'config',
        'logs',
        'data',
        'data/input',
        'data/output',
        'data/audit',
        'data/manual_review',
        'examples'
    ]

    passed = 0
    failed = 0

    for dir_path in required_dirs:
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            print_success(f"{dir_path}/")
            passed += 1
        else:
            print_error(f"{dir_path}/ not found")
            failed += 1

    return passed, failed


def check_core_files() -> Tuple[int, int]:
    """Check that core framework files exist."""
    required_files = [
        'main.py',
        'config/config.yml',
        'processors/__init__.py',
        'processors/cad_data_processor.py',
        'validators/__init__.py',
        'validators/validation_harness.py',
        'validators/validate_full_pipeline.py',
        'utils/__init__.py',
        'utils/logger.py',
        'utils/hash_utils.py',
        'utils/validate_schema.py',
        'examples/basic_usage.py',
        'FRAMEWORK_README.md',
        'QUICK_START.md',
        'DEPLOYMENT_GUIDE.md',
        'framework_requirements.txt'
    ]

    passed = 0
    failed = 0

    for file_path in required_files:
        path = Path(file_path)
        if path.exists() and path.is_file():
            size_kb = path.stat().st_size / 1024
            print_success(f"{file_path} ({size_kb:.1f} KB)")
            passed += 1
        else:
            print_error(f"{file_path} not found")
            failed += 1

    return passed, failed


def check_imports() -> Tuple[int, int]:
    """Check that all modules can be imported."""
    modules_to_test = [
        ('processors.cad_data_processor', 'CADDataProcessor'),
        ('validators.validation_harness', 'ValidationHarness'),
        ('validators.validate_full_pipeline', 'PipelineValidator'),
        ('utils.logger', 'setup_logger'),
        ('utils.hash_utils', 'FileHashManager'),
        ('utils.validate_schema', 'SchemaValidator')
    ]

    passed = 0
    failed = 0

    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print_success(f"{module_name}.{class_name}")
            passed += 1
        except Exception as e:
            print_error(f"{module_name}.{class_name}: {str(e)}")
            failed += 1

    return passed, failed


def check_config_file() -> bool:
    """Check that config file is valid YAML."""
    try:
        import yaml

        config_path = Path('config/config.yml')
        if not config_path.exists():
            print_error("config/config.yml not found")
            return False

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Check required sections
        required_sections = [
            'project',
            'paths',
            'processing',
            'validation',
            'quality_weights',
            'export',
            'logging'
        ]

        missing_sections = []
        for section in required_sections:
            if section not in config:
                missing_sections.append(section)

        if missing_sections:
            print_error(f"Missing config sections: {', '.join(missing_sections)}")
            return False

        # Check quality weights sum to 100
        if 'quality_weights' in config:
            total = sum(config['quality_weights'].values())
            if abs(total - 100) > 0.01:
                print_warning(f"Quality weights sum to {total} (should be 100)")

        print_success("config/config.yml is valid")
        return True

    except Exception as e:
        print_error(f"Error loading config: {str(e)}")
        return False


def test_basic_functionality() -> bool:
    """Test basic framework functionality."""
    try:
        from utils.logger import setup_logger
        from utils.hash_utils import FileHashManager
        from utils.validate_schema import SchemaValidator

        # Test logger
        logger = setup_logger(name="test_verify", log_file="logs/verify_test.log")
        logger.info("Test log message")
        print_success("Logger initialization works")

        # Test hash manager
        hash_manager = FileHashManager("data/audit/test_manifest.json")
        print_success("HashManager initialization works")

        # Test schema validator
        validator = SchemaValidator(strict=False)
        print_success("SchemaValidator initialization works")

        return True

    except Exception as e:
        print_error(f"Basic functionality test failed: {str(e)}")
        return False


def main():
    """Run all verification checks."""
    print_header("CAD DATA CORRECTION FRAMEWORK - VERIFICATION")
    print(f"Working Directory: {Path.cwd()}")
    print(f"Python Executable: {sys.executable}")

    total_passed = 0
    total_failed = 0

    # Check 1: Python Version
    print_header("1. Python Version Check")
    if check_python_version():
        total_passed += 1
    else:
        total_failed += 1

    # Check 2: Dependencies
    print_header("2. Dependencies Check")
    passed, failed = check_dependencies()
    total_passed += passed
    total_failed += failed

    # Check 3: Directory Structure
    print_header("3. Directory Structure Check")
    passed, failed = check_directory_structure()
    total_passed += passed
    total_failed += failed

    # Check 4: Core Files
    print_header("4. Core Files Check")
    passed, failed = check_core_files()
    total_passed += passed
    total_failed += failed

    # Check 5: Module Imports
    print_header("5. Module Import Check")
    passed, failed = check_imports()
    total_passed += passed
    total_failed += failed

    # Check 6: Config File
    print_header("6. Configuration File Check")
    if check_config_file():
        total_passed += 1
    else:
        total_failed += 1

    # Check 7: Basic Functionality
    print_header("7. Basic Functionality Test")
    if test_basic_functionality():
        total_passed += 1
    else:
        total_failed += 1

    # Summary
    print_header("VERIFICATION SUMMARY")
    print(f"\nTotal Checks: {total_passed + total_failed}")
    print(f"Passed: {GREEN}{total_passed}{RESET}")
    print(f"Failed: {RED}{total_failed}{RESET}")

    if total_failed == 0:
        print(f"\n{GREEN}✓ ALL VERIFICATION CHECKS PASSED{RESET}")
        print(f"\nFramework is properly installed and ready to use!")
        print(f"\nNext steps:")
        print(f"  1. Configure paths in config/config.yml")
        print(f"  2. Run: python main.py --validate-only")
        print(f"  3. Run: python main.py --test-mode")
        print(f"  4. Run: python main.py")
        return 0
    else:
        print(f"\n{RED}✗ VERIFICATION FAILED{RESET}")
        print(f"\nPlease fix the errors above before using the framework.")
        print(f"\nCommon fixes:")
        print(f"  - Install missing dependencies: pip install -r framework_requirements.txt")
        print(f"  - Check that all files were properly created")
        print(f"  - Verify you're in the correct directory")
        return 1


if __name__ == "__main__":
    sys.exit(main())
