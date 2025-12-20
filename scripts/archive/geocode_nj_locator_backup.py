#!/usr/bin/env python
"""
NJ Geocoder - Local Locator File Version
========================================
Uses a local ArcGIS locator file (.loc or .loz) for fast, offline geocoding.

This is much faster than the web service and has no rate limits.

Requirements:
- ArcGIS Pro or ArcGIS Desktop with arcpy
- Local locator file (.loc or .loz)

Author: CAD Data Cleaning Engine
Date: 2025-12-19
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import warnings

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import arcpy
try:
    import arcpy
    ARCPY_AVAILABLE = True
except ImportError:
    ARCPY_AVAILABLE = False
    logger.warning("arcpy not available. Install ArcGIS Pro or ArcGIS Desktop to use local locator files.")


class NJGeocoderLocal:
    """New Jersey Geocoder using local ArcGIS locator file."""
    
    def __init__(self, locator_path: str, max_workers: int = 4, use_web_service: bool = False):
        """
        Initialize geocoder with local locator file or ArcGIS Pro locator reference.
        
        Args:
            locator_path: Path to .loc/.loz file, or ArcGIS Pro locator name/reference
            max_workers: Maximum number of concurrent geocoding workers
            use_web_service: If True, locator_path is treated as a web service URL or ArcGIS Pro locator reference
        """
        if not ARCPY_AVAILABLE:
            raise ImportError("arcpy is required for local locator geocoding. "
                            "Please install ArcGIS Pro or ArcGIS Desktop.")
        
        self.max_workers = max_workers
        self.use_web_service = use_web_service
        
        if use_web_service or locator_path.startswith('http'):
            # Web service locator or ArcGIS Pro locator reference
            self.locator_path_str = locator_path
            logger.info(f"Using ArcGIS Pro locator reference or web service: {locator_path}")
        else:
            # Local file path
            self.locator_path = Path(locator_path)
            if not self.locator_path.exists():
                raise FileNotFoundError(f"Locator file not found: {locator_path}")
            
            # Convert to string for arcpy
            self.locator_path_str = str(self.locator_path.resolve())
            logger.info(f"Using local locator file: {self.locator_path_str}")
        
        # Verify locator is accessible
        try:
            if not use_web_service and not locator_path.startswith('http'):
                arcpy.env.workspace = str(self.locator_path.parent)
            
            # Test if locator is valid (may not work for web service references)
            try:
                desc = arcpy.Describe(self.locator_path_str)
                logger.info(f"Locator verified: {desc.name if hasattr(desc, 'name') else 'Unknown'}")
            except:
                # For web service or ArcGIS Pro references, Describe might not work
                logger.info("Locator reference accepted (web service or ArcGIS Pro locator)")
        except Exception as e:
            logger.warning(f"Could not verify locator: {e}")
            logger.info("Will attempt to use locator anyway...")
        
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'no_results': 0,
            'errors': []
        }
    
    def geocode_address(self, address: str) -> Optional[Dict]:
        """
        Geocode a single address using local locator.
        
        Args:
            address: Address string to geocode
            
        Returns:
            Dictionary with 'latitude', 'longitude', 'score', 'match_type', 'status'
            or None if geocoding failed
        """
        if not address or pd.isna(address) or str(address).strip() == '':
            return None
        
        try:
            # Use arcpy.geocoding.GeocodeAddresses for single address
            # Create a temporary table with the address
            temp_table = "in_memory\\temp_single_geocode"
            arcpy.management.CreateTable("in_memory", "temp_single_geocode")
            arcpy.management.AddField(temp_table, "Address", "TEXT", field_length=255)
            
            with arcpy.da.InsertCursor(temp_table, ["Address"]) as cursor:
                cursor.insertRow([str(address).strip()])
            
            # Geocode the table
            geocoded_table = "in_memory\\geocoded_single"
            arcpy.geocoding.GeocodeAddresses(
                temp_table,
                self.locator_path_str,
                "Address SingleLine",
                geocoded_table,
                "outSR=4326"
            )
            
            # Read result
            result = None
            with arcpy.da.SearchCursor(geocoded_table, 
                                      ["X", "Y", "Score", "Status"]) as cursor:
                for row in cursor:
                    x, y, score, status = row
                    if score and score >= 80 and x and y:
                        result = {
                            'latitude': y,
                            'longitude': x,
                            'score': score,
                            'match_type': status or 'Unknown',
                            'status': 'success'
                        }
                        self.stats['successful'] += 1
                    else:
                        result = {
                            'latitude': None,
                            'longitude': None,
                            'score': score or 0,
                            'match_type': status or 'No Match',
                            'status': 'low_score' if score and score < 80 else 'no_match'
                        }
                        self.stats['no_results'] += 1
                    break  # Only read first result
            
            # Cleanup
            arcpy.management.Delete(temp_table)
            try:
                arcpy.management.Delete(geocoded_table)
            except:
                pass
            
            if result:
                return result
            else:
                self.stats['no_results'] += 1
                return {
                    'latitude': None,
                    'longitude': None,
                    'score': 0,
                    'match_type': 'No Match',
                    'status': 'no_match'
                }
                
        except Exception as e:
            self.stats['failed'] += 1
            self.stats['errors'].append(f"Address '{address[:50]}...': {str(e)}")
            logger.warning(f"Failed to geocode '{address[:50]}...': {e}")
            return None
    
    def geocode_batch_table(self, addresses: List[str]) -> List[Optional[Dict]]:
        """
        Geocode a batch of addresses using arcpy table geocoding (faster).
        
        Args:
            addresses: List of address strings to geocode
            
        Returns:
            List of geocoding results (dicts or None)
        """
        if not addresses:
            return []
        
        try:
            # Create in-memory table with addresses
            temp_table = "in_memory\\temp_geocode_table"
            
            # Create table
            arcpy.management.CreateTable("in_memory", "temp_geocode_table")
            arcpy.management.AddField(temp_table, "OBJECTID", "LONG")
            arcpy.management.AddField(temp_table, "Address", "TEXT", field_length=255)
            
            # Insert addresses
            with arcpy.da.InsertCursor(temp_table, ["OBJECTID", "Address"]) as cursor:
                for idx, addr in enumerate(addresses, 1):
                    cursor.insertRow([idx, str(addr).strip()])
            
            # Geocode table
            geocoded_table = "in_memory\\geocoded_results"
            arcpy.geocoding.GeocodeAddresses(
                temp_table,
                self.locator_path_str,
                "Address SingleLine",
                geocoded_table,
                "outSR=4326"
            )
            
            # Read results
            results = []
            with arcpy.da.SearchCursor(geocoded_table, 
                                      ["Address", "X", "Y", "Score", "Status"]) as cursor:
                for row in cursor:
                    addr, x, y, score, status = row
                    if score and score >= 80 and x and y:
                        results.append({
                            'latitude': y,
                            'longitude': x,
                            'score': score,
                            'match_type': status,
                            'status': 'success'
                        })
                    else:
                        results.append({
                            'latitude': None,
                            'longitude': None,
                            'score': score or 0,
                            'match_type': status or 'No Match',
                            'status': 'low_score' if score and score < 80 else 'no_match'
                        })
            
            # Cleanup
            arcpy.management.Delete(temp_table)
            arcpy.management.Delete(geocoded_table)
            
            self.stats['successful'] += sum(1 for r in results if r.get('status') == 'success')
            self.stats['no_results'] += sum(1 for r in results if r.get('status') == 'no_match')
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch geocoding: {e}")
            # Fallback to individual geocoding
            return [self.geocode_address(addr) for addr in addresses]
    
    def backfill_coordinates(
        self,
        df: pd.DataFrame,
        address_column: str = 'FullAddress2',
        latitude_column: str = 'latitude',
        longitude_column: str = 'longitude',
        batch_size: int = 1000,
        progress_interval: int = 1000
    ) -> pd.DataFrame:
        """
        Backfill missing coordinates in DataFrame using local locator.
        
        Args:
            df: DataFrame with addresses
            address_column: Column name containing addresses
            latitude_column: Column name for latitude (will be created if missing)
            longitude_column: Column name for longitude (will be created if missing)
            batch_size: Number of addresses to geocode per batch
            progress_interval: Log progress every N addresses
            
        Returns:
            DataFrame with backfilled coordinates
        """
        df = df.copy()
        
        # Initialize columns if they don't exist
        if latitude_column not in df.columns:
            df[latitude_column] = np.nan
        if longitude_column not in df.columns:
            df[longitude_column] = np.nan
        
        # Find rows that need geocoding
        needs_geocoding = (
            (df[latitude_column].isna() | df[longitude_column].isna()) &
            df[address_column].notna() &
            (df[address_column].astype(str).str.strip() != '')
        )
        
        rows_to_geocode = df[needs_geocoding].copy()
        total_to_geocode = len(rows_to_geocode)
        
        if total_to_geocode == 0:
            logger.info("No addresses need geocoding. All coordinates are present or addresses are missing.")
            return df
        
        logger.info(f"Geocoding {total_to_geocode:,} addresses using local locator...")
        logger.info(f"Locator: {self.locator_path}")
        logger.info(f"Batch size: {batch_size}")
        
        # Get unique addresses to reduce geocoding calls
        unique_addresses = rows_to_geocode[address_column].drop_duplicates()
        logger.info(f"Found {len(unique_addresses):,} unique addresses to geocode")
        
        # Geocode unique addresses in batches
        geocode_results = {}
        processed = 0
        
        for i in range(0, len(unique_addresses), batch_size):
            batch = unique_addresses.iloc[i:i+batch_size].tolist()
            
            # Use batch table geocoding (faster)
            results = self.geocode_batch_table(batch)
            
            # Store results
            for addr, result in zip(batch, results):
                if result and result.get('status') == 'success':
                    geocode_results[addr] = result
            
            processed += len(batch)
            if processed % progress_interval == 0 or processed >= len(unique_addresses):
                logger.info(f"Processed {processed:,} / {len(unique_addresses):,} unique addresses "
                          f"({processed/len(unique_addresses)*100:.1f}%)")
        
        # Apply geocoding results to DataFrame (vectorized)
        if geocode_results:
            # Create results DataFrame for vectorized merge
            results_data = []
            for addr, result in geocode_results.items():
                results_data.append({
                    'address': addr,
                    'latitude': result['latitude'],
                    'longitude': result['longitude']
                })
            
            results_df = pd.DataFrame(results_data)
            
            # CRITICAL FIX: Deduplicate results_df to prevent Cartesian product in merge
            results_df = results_df.drop_duplicates(subset=['address'], keep='first')
            
            # Create temporary normalized address column for matching
            temp_addr_col = '_geocode_address_match_'
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
            
            # Update only where geocoded (vectorized)
            mask = df['latitude_geocoded'].notna()
            df.loc[mask, latitude_column] = df.loc[mask, 'latitude_geocoded']
            df.loc[mask, longitude_column] = df.loc[mask, 'longitude_geocoded']
            
            backfilled_count = mask.sum()
            
            # Cleanup temporary columns
            df = df.drop(columns=[temp_addr_col, 'address', 'latitude_geocoded', 'longitude_geocoded'], errors='ignore')
        else:
            backfilled_count = 0
        
        logger.info(f"Backfilled coordinates for {backfilled_count:,} records")
        logger.info(f"Geocoding stats: {self.stats['successful']:,} successful, "
                   f"{self.stats['no_results']:,} no results, {self.stats['failed']:,} failed")
        
        return df
    
    def get_stats(self) -> Dict:
        """Get geocoding statistics."""
        return self.stats.copy()


def main():
    """Command-line interface for local locator geocoding."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Geocode addresses using local ArcGIS locator file'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input Excel or CSV file with addresses'
    )
    parser.add_argument(
        '--locator',
        required=True,
        help='Path to local locator file (.loc or .loz), ArcGIS Pro locator name, or web service URL'
    )
    parser.add_argument(
        '--use-web-service',
        action='store_true',
        help='Treat locator as web service URL or ArcGIS Pro locator reference'
    )
    parser.add_argument(
        '--output',
        help='Output file path (default: input file with _geocoded suffix)'
    )
    parser.add_argument(
        '--format',
        choices=['excel', 'csv'],
        default='excel',
        help='Input file format (default: excel)'
    )
    parser.add_argument(
        '--address-column',
        default='FullAddress2',
        help='Column name containing addresses (default: FullAddress2)'
    )
    parser.add_argument(
        '--latitude-column',
        default='latitude',
        help='Column name for latitude (default: latitude)'
    )
    parser.add_argument(
        '--longitude-column',
        default='longitude',
        help='Column name for longitude (default: longitude)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for geocoding (default: 1000)'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=4,
        help='Maximum concurrent workers (default: 4)'
    )
    
    args = parser.parse_args()
    
    # Check if arcpy is available
    if not ARCPY_AVAILABLE:
        logger.error("arcpy is not available. Please install ArcGIS Pro or ArcGIS Desktop.")
        logger.error("Alternatively, use geocode_nj_geocoder.py for web service geocoding.")
        return 1
    
    # Determine output path
    input_path = Path(args.input)
    if args.output:
        output_path = Path(args.output)
    else:
        if args.format == 'csv':
            output_path = input_path.parent / f"{input_path.stem}_geocoded.csv"
        else:
            output_path = input_path.parent / f"{input_path.stem}_geocoded.xlsx"
    
    # Load data
    logger.info(f"Loading data from: {input_path}")
    if input_path.suffix.lower() == '.csv':
        df = pd.read_csv(input_path, dtype=str, encoding='utf-8-sig')
    else:
        df = pd.read_excel(input_path, dtype=str)
    
    logger.info(f"Loaded {len(df):,} records")
    
    # Initialize geocoder
    geocoder = NJGeocoderLocal(
        locator_path=args.locator,
        max_workers=args.max_workers,
        use_web_service=args.use_web_service
    )
    
    # Backfill coordinates
    start_time = time.time()
    df_geocoded = geocoder.backfill_coordinates(
        df,
        address_column=args.address_column,
        latitude_column=args.latitude_column,
        longitude_column=args.longitude_column,
        batch_size=args.batch_size
    )
    elapsed_time = time.time() - start_time
    
    # Save results
    logger.info(f"Saving geocoded data to: {output_path}")
    if output_path.suffix.lower() == '.csv':
        df_geocoded.to_csv(output_path, index=False, encoding='utf-8-sig')
    else:
        df_geocoded.to_excel(output_path, index=False)
    
    # Print summary
    stats = geocoder.get_stats()
    logger.info(f"\n{'='*60}")
    logger.info("GEOCODING SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total records: {len(df_geocoded):,}")
    logger.info(f"Records geocoded: {stats['successful']:,}")
    logger.info(f"No results: {stats['no_results']:,}")
    logger.info(f"Failed: {stats['failed']:,}")
    logger.info(f"Processing time: {elapsed_time/60:.1f} minutes")
    logger.info(f"Output file: {output_path}")
    
    return 0


if __name__ == "__main__":
    import time
    import sys
    sys.exit(main())

