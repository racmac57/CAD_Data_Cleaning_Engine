#!/usr/bin/env python
"""
NJ Geocoder Service - Latitude/Longitude Backfill
==================================================
Uses the New Jersey Geocoder REST service to backfill missing coordinates.

Service Endpoint: https://geo.nj.gov/arcgis/rest/services/Tasks/NJ_Geocode/GeocodeServer

Author: CAD Data Cleaning Engine
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
import requests
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# NJ Geocoder Service Configuration
GEOCODER_URL = "https://geo.nj.gov/arcgis/rest/services/Tasks/NJ_Geocode/GeocodeServer"
FIND_ADDRESS_ENDPOINT = f"{GEOCODER_URL}/findAddressCandidates"
BATCH_SIZE = 100  # Process addresses in batches
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
REQUEST_TIMEOUT = 30  # seconds
MAX_WORKERS = 5  # Concurrent requests


class NJGeocoder:
    """New Jersey Geocoder service client for batch geocoding."""
    
    def __init__(self, max_workers: int = MAX_WORKERS):
        """
        Initialize geocoder.
        
        Args:
            max_workers: Maximum number of concurrent geocoding requests
        """
        self.max_workers = max_workers
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'no_results': 0,
            'errors': []
        }
    
    def geocode_address(self, address: str, retry_count: int = 0) -> Optional[Dict]:
        """
        Geocode a single address using NJ Geocoder service.
        
        Args:
            address: Address string to geocode
            retry_count: Current retry attempt number
            
        Returns:
            Dictionary with 'latitude', 'longitude', 'score', 'match_type', 'status'
            or None if geocoding failed
        """
        if not address or pd.isna(address) or str(address).strip() == '':
            return None
        
        params = {
            'SingleLine': str(address).strip(),
            'f': 'json',
            'outSR': '4326'  # WGS84
        }
        
        try:
            response = requests.get(
                FIND_ADDRESS_ENDPOINT,
                params=params,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            
            self.stats['total_requests'] += 1
            
            # Check for candidates
            if 'candidates' in data and len(data['candidates']) > 0:
                # Get best match (first candidate, sorted by score)
                best_match = data['candidates'][0]
                
                location = best_match.get('location', {})
                score = best_match.get('score', 0)
                
                # Only accept high-quality matches (score >= 80)
                if score >= 80 and 'x' in location and 'y' in location:
                    self.stats['successful'] += 1
                    return {
                        'latitude': location.get('y'),
                        'longitude': location.get('x'),
                        'score': score,
                        'match_type': best_match.get('attributes', {}).get('Addr_type', 'Unknown'),
                        'status': 'success'
                    }
                else:
                    self.stats['no_results'] += 1
                    return {
                        'latitude': None,
                        'longitude': None,
                        'score': score,
                        'match_type': 'Low Score',
                        'status': 'low_score'
                    }
            else:
                self.stats['no_results'] += 1
                return {
                    'latitude': None,
                    'longitude': None,
                    'score': 0,
                    'match_type': 'No Match',
                    'status': 'no_match'
                }
                
        except requests.exceptions.RequestException as e:
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (retry_count + 1))
                return self.geocode_address(address, retry_count + 1)
            else:
                self.stats['failed'] += 1
                self.stats['errors'].append(f"Address '{address[:50]}...': {str(e)}")
                logger.warning(f"Failed to geocode '{address[:50]}...' after {MAX_RETRIES} retries: {e}")
                return None
        except Exception as e:
            self.stats['failed'] += 1
            self.stats['errors'].append(f"Address '{address[:50]}...': {str(e)}")
            logger.error(f"Unexpected error geocoding '{address[:50]}...': {e}")
            return None
    
    def geocode_batch(self, addresses: List[str]) -> List[Optional[Dict]]:
        """
        Geocode a batch of addresses using parallel processing.
        
        Args:
            addresses: List of address strings to geocode
            
        Returns:
            List of geocoding results (dicts or None)
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all geocoding tasks
            future_to_address = {
                executor.submit(self.geocode_address, addr): addr 
                for addr in addresses
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_address):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    addr = future_to_address[future]
                    logger.error(f"Error geocoding address '{addr[:50]}...': {e}")
                    results.append(None)
        
        return results
    
    def backfill_coordinates(
        self,
        df: pd.DataFrame,
        address_column: str = 'FullAddress2',
        latitude_column: str = 'latitude',
        longitude_column: str = 'longitude',
        batch_size: int = BATCH_SIZE,
        progress_interval: int = 1000
    ) -> pd.DataFrame:
        """
        Backfill missing latitude/longitude values in DataFrame.
        
        Args:
            df: DataFrame with address data
            address_column: Name of column containing addresses
            latitude_column: Name of latitude column to populate
            longitude_column: Name of longitude column to populate
            batch_size: Number of addresses to process per batch
            progress_interval: Log progress every N records
            
        Returns:
            DataFrame with backfilled coordinates
        """
        df = df.copy()
        
        # Initialize columns if they don't exist
        if latitude_column not in df.columns:
            df[latitude_column] = np.nan
        if longitude_column not in df.columns:
            df[longitude_column] = np.nan
        
        # Find rows that need geocoding (missing lat/lon but have address)
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
        
        logger.info(f"Geocoding {total_to_geocode:,} addresses using NJ Geocoder service...")
        logger.info(f"Using {self.max_workers} concurrent workers, batch size: {batch_size}")
        
        # Get unique addresses to reduce API calls
        unique_addresses = rows_to_geocode[address_column].drop_duplicates()
        logger.info(f"Found {len(unique_addresses):,} unique addresses to geocode")
        
        # Geocode unique addresses
        geocode_results = {}
        processed = 0
        
        for i in range(0, len(unique_addresses), batch_size):
            batch = unique_addresses.iloc[i:i+batch_size].tolist()
            results = self.geocode_batch(batch)
            
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
            # If results_df has duplicate addresses, the merge would create duplicate rows
            # Keep first occurrence of each address
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
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Backfill latitude/longitude using NJ Geocoder service'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input CSV/Excel file path'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: input file with _geocoded suffix)'
    )
    parser.add_argument(
        '--address-column',
        type=str,
        default='FullAddress2',
        help='Name of address column (default: FullAddress2)'
    )
    parser.add_argument(
        '--latitude-column',
        type=str,
        default='latitude',
        help='Name of latitude column (default: latitude)'
    )
    parser.add_argument(
        '--longitude-column',
        type=str,
        default='longitude',
        help='Name of longitude column (default: longitude)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=BATCH_SIZE,
        help=f'Batch size for processing (default: {BATCH_SIZE})'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=MAX_WORKERS,
        help=f'Maximum concurrent requests (default: {MAX_WORKERS})'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'excel'],
        default='csv',
        help='Output format (default: csv)'
    )
    
    args = parser.parse_args()
    
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
    geocoder = NJGeocoder(max_workers=args.max_workers)
    
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
    logger.info(f"Saving results to: {output_path}")
    if args.format == 'csv':
        df_geocoded.to_csv(output_path, index=False, encoding='utf-8-sig')
    else:
        df_geocoded.to_excel(output_path, index=False, engine='openpyxl')
    
    # Print summary
    stats = geocoder.get_stats()
    total_missing = df[args.latitude_column].isna().sum() if args.latitude_column in df.columns else len(df)
    total_geocoded = df_geocoded[args.latitude_column].notna().sum()
    
    print("\n" + "="*80)
    print("GEOCODING SUMMARY")
    print("="*80)
    print(f"Total records:           {len(df):,}")
    print(f"Records needing geocode: {total_missing:,}")
    print(f"Records geocoded:       {total_geocoded:,}")
    print(f"Success rate:           {stats['successful']:,} / {stats['total_requests']:,} "
          f"({stats['successful']/max(stats['total_requests'],1)*100:.1f}%)")
    print(f"Processing time:        {elapsed_time:.2f} seconds")
    print(f"Output file:            {output_path}")
    print("="*80)


if __name__ == "__main__":
    main()

