#!/usr/bin/env python
"""
Performance Testing Script for Geocoding Optimization
======================================================
Compares sequential vs parallel geocoding performance.

Author: CAD Data Cleaning Engine
Date: 2025-12-19
"""

import pandas as pd
import time
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def test_configuration(
    input_file: str,
    locator_path: str,
    batch_size: int,
    max_workers: int,
    use_parallel: bool,
    executor_type: str = 'process',
    sample_size: int = None
):
    """Test a specific geocoding configuration."""
    
    from geocode_nj_locator import NJGeocoderLocal
    
    # Load data
    input_path = Path(input_file)
    if input_path.suffix.lower() == '.csv':
        df = pd.read_csv(input_file, dtype=str, encoding='utf-8-sig')
    else:
        df = pd.read_excel(input_file, dtype=str)
    
    # Sample if requested
    if sample_size and sample_size < len(df):
        df = df.sample(n=sample_size, random_state=42)
        logger.info(f"Using sample of {sample_size:,} records")
    
    # Initialize geocoder
    geocoder = NJGeocoderLocal(
        locator_path=locator_path,
        max_workers=max_workers
    )
    
    # Run geocoding
    config_name = f"{'Parallel' if use_parallel else 'Sequential'} | Batch={batch_size} | Workers={max_workers if use_parallel else 1} | Type={executor_type}"
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing: {config_name}")
    logger.info(f"{'='*80}")
    
    start_time = time.time()
    
    df_geocoded = geocoder.backfill_coordinates(
        df,
        batch_size=batch_size,
        use_parallel=use_parallel,
        executor_type=executor_type
    )
    
    elapsed_time = time.time() - start_time
    
    # Get statistics
    stats = geocoder.get_stats()
    
    # Calculate metrics
    total_addresses = stats['successful'] + stats['no_results'] + stats['failed']
    success_rate = (stats['successful'] / total_addresses * 100) if total_addresses > 0 else 0
    addresses_per_sec = stats['successful'] / elapsed_time if elapsed_time > 0 else 0
    
    # Results
    results = {
        'config': config_name,
        'batch_size': batch_size,
        'workers': max_workers if use_parallel else 1,
        'parallel': use_parallel,
        'executor_type': executor_type,
        'total_records': len(df),
        'addresses_geocoded': stats['successful'],
        'no_results': stats['no_results'],
        'failed': stats['failed'],
        'success_rate_pct': success_rate,
        'elapsed_time_sec': elapsed_time,
        'elapsed_time_min': elapsed_time / 60,
        'addresses_per_sec': addresses_per_sec,
        'addresses_per_min': addresses_per_sec * 60
    }
    
    # Print results
    print(f"\nResults for: {config_name}")
    print(f"  Total records:       {results['total_records']:,}")
    print(f"  Addresses geocoded:  {results['addresses_geocoded']:,}")
    print(f"  Success rate:        {results['success_rate_pct']:.1f}%")
    print(f"  Elapsed time:        {results['elapsed_time_sec']:.2f}s ({results['elapsed_time_min']:.2f} min)")
    print(f"  Geocoding rate:      {results['addresses_per_sec']:.0f} addr/sec ({results['addresses_per_min']:.0f} addr/min)")
    
    return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Benchmark geocoding performance with different configurations'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input file path'
    )
    parser.add_argument(
        '--locator',
        required=True,
        help='Locator file path or reference'
    )
    parser.add_argument(
        '--sample',
        type=int,
        help='Sample size for testing (default: use full file)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick test with just 2 configurations'
    )
    
    args = parser.parse_args()
    
    if args.quick:
        # Just test baseline vs optimized
        logger.info("Running quick benchmark (2 configurations)...")
        
        results = []
        
        # Baseline
        res1 = test_configuration(
            args.input, args.locator,
            batch_size=1000, max_workers=1, use_parallel=False,
            sample_size=args.sample
        )
        res1['description'] = 'Baseline (Sequential)'
        results.append(res1)
        
        time.sleep(2)
        
        # Optimized
        res2 = test_configuration(
            args.input, args.locator,
            batch_size=5000, max_workers=4, use_parallel=True,
            executor_type='process', sample_size=args.sample
        )
        res2['description'] = 'Optimized (Parallel, 4 workers)'
        results.append(res2)
        
        # Compare
        print(f"\n{'='*80}")
        print("QUICK BENCHMARK RESULTS")
        print(f"{'='*80}")
        print(f"Baseline:  {res1['elapsed_time_min']:.2f} min, {res1['addresses_per_min']:,.0f} addr/min")
        print(f"Optimized: {res2['elapsed_time_min']:.2f} min, {res2['addresses_per_min']:,.0f} addr/min")
        
        speedup = res2['addresses_per_min'] / res1['addresses_per_min'] if res1['addresses_per_min'] > 0 else 0
        time_saved = res1['elapsed_time_min'] - res2['elapsed_time_min']
        
        print(f"\nSpeedup: {speedup:.2f}x faster")
        print(f"Time saved: {time_saved:.2f} minutes ({time_saved*60:.0f} seconds)")
        print("="*80)
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

