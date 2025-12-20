#!/usr/bin/env python
"""
Test script to verify the processing summary formatting fix.
Tests with various stat configurations to ensure no ValueError occurs.
"""

import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).resolve().parent
project_root = scripts_dir.parent
sys.path.insert(0, str(scripts_dir))

from enhanced_esri_output_generator import EnhancedESRIOutputGenerator
import pandas as pd

def test_formatting_scenarios():
    """Test various stat configurations to ensure robust formatting."""
    
    print("="*80)
    print("TESTING PROCESSING SUMMARY FORMATTING FIX")
    print("="*80)
    
    # Create generator
    generator = EnhancedESRIOutputGenerator()
    
    # Test scenario 1: All numeric stats (normal case)
    print("\n[TEST 1] All numeric stats (normal case)")
    rms_stats_1 = {
        'matches_found': 175657,
        'fields_backfilled': {
            'Incident': 97,
            'PDZone': 41138,
            'Officer': 11
        }
    }
    
    try:
        # Create test dataframe
        df_test = pd.DataFrame({
            'ReportNumberNew': ['1', '2', '3'],
            'Incident': ['A', None, 'C'],
            'latitude': [40.5, None, 40.7]
        })
        
        # This should work without errors
        summary_path = generator._generate_processing_summary(
            df_test,
            [],
            project_root / 'data',
            validation_stats={'rules_passed': 10, 'rules_failed': 2, 'fixes_applied': 5},
            rms_backfill_stats=rms_stats_1,
            geocoding_stats={'successful': 1, 'success_rate': 33.3}
        )
        print("  [OK] Test passed - no formatting errors")
        
        # Read and display relevant section
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if '175,657' in content:
                print("  [OK] Numeric formatting with commas works correctly")
            else:
                print("  [WARN] Expected '175,657' not found in output")
        
        # Cleanup
        summary_path.unlink()
                
    except ValueError as e:
        print(f"  [FAIL] ValueError occurred: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test scenario 2: Missing/None stats (edge case)
    print("\n[TEST 2] Missing/None stats (edge case)")
    rms_stats_2 = {
        'fields_backfilled': {
            'Incident': 50
        }
        # Note: 'matches_found' key is missing entirely
    }
    
    try:
        summary_path = generator._generate_processing_summary(
            df_test,
            [],
            project_root / 'data',
            rms_backfill_stats=rms_stats_2
        )
        print("  [OK] Test passed - handles missing 'matches_found' key")
        
        # Check for 'N/A' in output
        with open(summary_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'Records Matched to RMS**: N/A' in content or 'Records Matched to RMS**: N/A' in content:
                print("  [OK] Missing value displays as 'N/A'")
            else:
                print("  [WARN] Expected 'N/A' for missing value")
        
        # Cleanup
        summary_path.unlink()
                
    except ValueError as e:
        print(f"  [FAIL] ValueError occurred: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test scenario 3: String values in stats (another edge case)
    print("\n[TEST 3] String values in stats (edge case)")
    rms_stats_3 = {
        'matches_found': 'Not Available',  # String instead of int
        'fields_backfilled': {}
    }
    
    try:
        summary_path = generator._generate_processing_summary(
            df_test,
            [],
            project_root / 'data',
            rms_backfill_stats=rms_stats_3
        )
        print("  [OK] Test passed - handles string values without formatting")
        
        # Cleanup
        summary_path.unlink()
        
    except ValueError as e:
        print(f"  [FAIL] ValueError occurred: {e}")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test scenario 4: Empty/None stats
    print("\n[TEST 4] Empty/None stats")
    try:
        summary_path = generator._generate_processing_summary(
            df_test,
            [],
            project_root / 'data',
            validation_stats=None,
            rms_backfill_stats=None,
            geocoding_stats=None
        )
        print("  [OK] Test passed - handles None stats gracefully")
        
        # Cleanup
        summary_path.unlink()
        
    except Exception as e:
        print(f"  [FAIL] Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "="*80)
    print("ALL TESTS PASSED - Fix verified!")
    print("="*80)
    print("\nThe formatting bug is fixed. You can now:")
    print("1. Re-run the pipeline to complete Steps 4-5")
    print("2. Generate the final processing summary without errors")
    
    return True


if __name__ == "__main__":
    success = test_formatting_scenarios()
    sys.exit(0 if success else 1)

