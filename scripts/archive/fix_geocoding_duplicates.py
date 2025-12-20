"""Fix duplicate records issue in geocoding merge operation.

The issue is that if results_df has duplicate addresses (which shouldn't happen but could),
the merge operation creates a Cartesian product, multiplying rows.

Solution: Ensure results_df has unique addresses before merging.
"""
import pandas as pd
from pathlib import Path

def fix_geocoding_merge(df: pd.DataFrame, results_df: pd.DataFrame, 
                        temp_addr_col: str, address_column: str) -> pd.DataFrame:
    """Fixed version of the merge that prevents duplicates.
    
    The original issue: If results_df has duplicate addresses, the merge creates
    duplicate rows. This fix ensures results_df is deduplicated before merging.
    """
    # Ensure results_df has unique addresses (keep first occurrence)
    # This prevents Cartesian product in merge
    results_df = results_df.drop_duplicates(subset=['address'], keep='first')
    
    # Create temporary normalized address column for matching
    df[temp_addr_col] = df[address_column].astype(str).str.strip()
    results_df['address'] = results_df['address'].astype(str).str.strip()
    
    # Merge geocoding results (left join preserves all rows from df)
    df = df.merge(
        results_df,
        left_on=temp_addr_col,
        right_on='address',
        how='left',
        suffixes=('', '_geocoded')
    )
    
    return df

# Test the fix
if __name__ == "__main__":
    print("This script contains the fix for the duplicate records issue.")
    print("The fix ensures results_df is deduplicated before merging.")
    print("\nTo apply the fix, update geocode_nj_geocoder.py line 260-274")

