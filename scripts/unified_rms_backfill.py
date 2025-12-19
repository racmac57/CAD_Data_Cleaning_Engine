#!/usr/bin/env python
"""
Unified RMS Backfill Script
============================
Cross-maps CAD records to RMS records and backfills missing/invalid CAD fields
using validated RMS data according to the merge policy defined in cad_to_rms_field_map_latest.json

Author: CAD Data Cleaning Engine
Date: 2025-12-17
"""

import pandas as pd
import numpy as np
import json
import glob
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import logging
import warnings
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UnifiedRMSBackfill:
    """Unified RMS backfill processor following CAD-to-RMS merge policy."""
    
    def __init__(self, config_path: Optional[str] = None, merge_policy_path: Optional[str] = None):
        """
        Initialize RMS backfill processor.
        
        Args:
            config_path: Path to config_enhanced.json (optional)
            merge_policy_path: Path to cad_to_rms_field_map_latest.json (optional)
        """
        self.base_dir = Path(__file__).resolve().parent.parent
        
        # Load config
        if config_path is None:
            config_path = self.base_dir / 'config' / 'config_enhanced.json'
        self.config = self._load_config(config_path)
        
        # Load merge policy
        if merge_policy_path is None:
            merge_policy_path = self.base_dir / 'cad_to_rms_field_map_latest.json'
        self.merge_policy = self._load_merge_policy(merge_policy_path)
        
        # Get RMS directory
        self.rms_dir = Path(self.config.get('paths', {}).get('rms_dir', 'data/rms'))
        if not self.rms_dir.is_absolute():
            self.rms_dir = self.base_dir / self.rms_dir
        
        # Statistics
        self.stats = {
            'rms_records_loaded': 0,
            'cad_records_processed': 0,
            'matches_found': 0,
            'fields_backfilled': {},
            'backfill_log': []
        }
    
    def _load_config(self, config_path: Path) -> Dict:
        """Load configuration file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Expand path templates
            if 'paths' in config:
                paths = config['paths'].copy()
                max_iterations = 10
                for _ in range(max_iterations):
                    changed = False
                    for key, value in paths.items():
                        if isinstance(value, str) and '{' in value:
                            for ref_key, ref_value in paths.items():
                                if '{' + ref_key + '}' in value and '{' not in str(ref_value):
                                    paths[key] = value.replace('{' + ref_key + '}', str(ref_value))
                                    changed = True
                    if not changed:
                        break
                config['paths'] = paths
            
            return config
        except Exception as e:
            logger.warning(f"Could not load config from {config_path}: {e}. Using defaults.")
            return {'paths': {'rms_dir': 'data/rms'}}
    
    def _load_merge_policy(self, policy_path: Path) -> Dict:
        """Load CAD-to-RMS merge policy."""
        try:
            with open(policy_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Could not load merge policy from {policy_path}: {e}")
            raise
    
    def _normalize_key(self, value: Any) -> str:
        """Normalize join key value according to policy."""
        if pd.isna(value):
            return ''
        
        key_norm = self.merge_policy.get('join', {}).get('key_normalization', {})
        s = str(value).strip()
        
        if key_norm.get('trim', True):
            s = s.strip()
        
        if key_norm.get('collapse_internal_whitespace', True):
            s = ' '.join(s.split())
        
        if key_norm.get('remove_nonprinting', True):
            s = ''.join(char for char in s if char.isprintable())
        
        return s
    
    def _load_rms_file(self, rms_file: Path) -> Optional[pd.DataFrame]:
        """Load single RMS file (for parallel processing)."""
        try:
            if rms_file.suffix.lower() == '.csv':
                df = pd.read_csv(rms_file, dtype=str, encoding='utf-8-sig')
            else:
                df = pd.read_excel(rms_file, dtype=str)
            
            join_key_rms = self.merge_policy['join']['rms_key']
            
            # Normalize join key
            if join_key_rms in df.columns:
                df['_join_key_normalized'] = df[join_key_rms].apply(self._normalize_key)
            else:
                logger.warning(f"  Join key '{join_key_rms}' not found in {rms_file.name}")
                return None
            
            logger.info(f"  Loaded {len(df):,} records from {rms_file.name}")
            return df
        except Exception as e:
            logger.error(f"  Error loading {rms_file.name}: {e}")
            return None
    
    def _load_rms_data(self) -> pd.DataFrame:
        """Load and consolidate all RMS files (parallelized)."""
        rms_files = sorted(list(self.rms_dir.glob('*.xlsx')) + 
                          list(self.rms_dir.glob('*.xls')) +
                          list(self.rms_dir.glob('*.csv')))
        
        if not rms_files:
            logger.warning(f"No RMS files found in {self.rms_dir}")
            return pd.DataFrame()
        
        logger.info(f"Loading {len(rms_files)} RMS file(s) from {self.rms_dir}")
        
        # Parallelize file loading for multiple files
        if len(rms_files) > 1:
            n_workers = min(len(rms_files), mp.cpu_count())
            logger.info(f"Loading {len(rms_files)} files in parallel using {n_workers} workers...")
            
            # Use ThreadPoolExecutor for I/O-bound file operations (better for Windows)
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=n_workers) as executor:
                results = list(executor.map(self._load_rms_file, rms_files))
            
            rms_dataframes = [df for df in results if df is not None]
        else:
            # Single file - no need for parallelization
            df = self._load_rms_file(rms_files[0])
            rms_dataframes = [df] if df is not None else []
        
        if not rms_dataframes:
            return pd.DataFrame()
        
        # Consolidate
        rms_combined = pd.concat(rms_dataframes, ignore_index=True)
        self.stats['rms_records_loaded'] = len(rms_combined)
        
        # Deduplicate according to policy (with intelligent quality scoring)
        dedupe_policy = self.merge_policy.get('dedupe', {})
        if dedupe_policy.get('policy') == 'keep_best':
            rms_combined = self._deduplicate_rms_intelligent(rms_combined, dedupe_policy)
            logger.info(f"Deduplicated to {len(rms_combined):,} unique RMS records")
        
        return rms_combined
    
    
    def _deduplicate_rms_intelligent(self, rms_df: pd.DataFrame, dedupe_policy: Dict) -> pd.DataFrame:
        """Intelligent deduplication prioritizing record quality."""
        # Score each record by completeness of important fields
        quality_cols = []
        for mapping in self.merge_policy.get('mappings', []):
            rms_sources = mapping.get('rms_source_fields_priority', [])
            quality_cols.extend(rms_sources)
        
        # Remove duplicates and get unique quality columns
        quality_cols = list(set([col for col in quality_cols if col in rms_df.columns]))
        
        if quality_cols:
            # Calculate quality score (number of non-null important fields)
            rms_df['_quality_score'] = rms_df[quality_cols].notna().sum(axis=1)
        else:
            rms_df['_quality_score'] = 1
        
        # Apply sort priority from policy
        sort_priority = dedupe_policy.get('sort_priority', [])
        if sort_priority:
            sort_cols = [p['field'] for p in sort_priority if p['field'] in rms_df.columns]
            sort_dirs = [p['direction'] == 'desc' for p in sort_priority if p['field'] in rms_df.columns]
            
            if sort_cols:
                # Sort by quality score first (descending), then by policy columns
                rms_df = rms_df.sort_values(
                    by=['_quality_score'] + sort_cols,
                    ascending=[False] + [not d for d in sort_dirs]
                )
            else:
                rms_df = rms_df.sort_values('_quality_score', ascending=False)
        else:
            rms_df = rms_df.sort_values('_quality_score', ascending=False)
        
        # Keep first (best) record per join key
        rms_combined = rms_df.drop_duplicates(
            subset='_join_key_normalized',
            keep='first'
        ).drop('_quality_score', axis=1)
        
        return rms_combined
    
    def _should_update_field(
        self,
        cad_value: Any,
        rms_value: Any,
        mapping: Dict
    ) -> bool:
        """Determine if field should be updated based on mapping policy."""
        update_when = mapping.get('update_when', 'cad_null_or_blank')
        accept_when = mapping.get('accept_when', 'rms_not_null_or_blank')
        
        # Check update condition
        if update_when == 'cad_null_or_blank':
            cad_is_empty = pd.isna(cad_value) or str(cad_value).strip() == ''
            if not cad_is_empty:
                return False
        elif update_when == 'always':
            pass  # Always update
        else:
            return False  # Unknown policy
        
        # Check accept condition
        if accept_when == 'rms_not_null_or_blank':
            rms_is_valid = pd.notna(rms_value) and str(rms_value).strip() != ''
            return rms_is_valid
        elif accept_when == 'always':
            return True
        else:
            return False
    
    def _get_rms_field_value(
        self,
        rms_row: pd.Series,
        mapping: Dict
    ) -> Optional[Any]:
        """Get RMS field value using priority order."""
        priority_fields = mapping.get('rms_source_fields_priority', [])
        
        for field in priority_fields:
            if field in rms_row.index:
                value = rms_row[field]
                if pd.notna(value) and str(value).strip() != '':
                    return value
        
        return None
    
    def backfill_from_rms(self, cad_df: pd.DataFrame) -> pd.DataFrame:
        """
        Backfill CAD DataFrame with RMS data.
        
        Args:
            cad_df: CAD DataFrame to backfill
            
        Returns:
            DataFrame with backfilled fields
        """
        cad_df = cad_df.copy()
        self.stats['cad_records_processed'] = len(cad_df)
        
        # Load RMS data
        rms_df = self._load_rms_data()
        if rms_df.empty:
            logger.warning("No RMS data available for backfill")
            return cad_df
        
        # Normalize CAD join key
        join_key_cad = self.merge_policy['join']['cad_key']
        if join_key_cad not in cad_df.columns:
            logger.error(f"CAD join key '{join_key_cad}' not found in CAD data")
            return cad_df
        
        cad_df['_join_key_normalized'] = cad_df[join_key_cad].apply(self._normalize_key)
        
        # Merge CAD with RMS
        logger.info("Merging CAD with RMS data...")
        merged = cad_df.merge(
            rms_df,
            left_on='_join_key_normalized',
            right_on='_join_key_normalized',
            how='left',
            suffixes=('', '_rms'),
            indicator=True
        )
        
        matches = (merged['_merge'] == 'both').sum()
        self.stats['matches_found'] = matches
        logger.info(f"Matched {matches:,} CAD records with RMS data ({matches/len(cad_df)*100:.1f}%)")
        
        # Apply field mappings (vectorized)
        mappings = self.merge_policy.get('mappings', [])
        
        for mapping in mappings:
            cad_field = mapping['cad_internal_field']
            
            if cad_field not in cad_df.columns:
                logger.warning(f"CAD field '{cad_field}' not found, skipping")
                continue
            
            # Initialize backfill counter
            if cad_field not in self.stats['fields_backfilled']:
                self.stats['fields_backfilled'][cad_field] = 0
            
            # Vectorized backfill
            update_when = mapping.get('update_when', 'cad_null_or_blank')
            
            # Calculate update mask (vectorized)
            if update_when == 'cad_null_or_blank':
                update_mask = (merged[cad_field].isna() | 
                              (merged[cad_field].astype(str).str.strip() == ''))
            elif update_when == 'always':
                update_mask = pd.Series(True, index=merged.index)
            else:
                update_mask = pd.Series(False, index=merged.index)
            
            # Only update where merged with RMS
            update_mask = update_mask & (merged['_merge'] == 'both')
            
            # Get RMS source values with priority (vectorized)
            rms_sources = mapping.get('rms_source_fields_priority', [])
            if not isinstance(rms_sources, list):
                rms_sources = [rms_sources]
            
            # Coalesce RMS sources (vectorized)
            rms_value = None
            for rms_source in rms_sources:
                rms_col = rms_source
                if rms_col in merged.columns:
                    if rms_value is None:
                        rms_value = merged[rms_col].copy()
                    else:
                        # Fill nulls with next priority source
                        rms_value = rms_value.fillna(merged[rms_col])
            
            if rms_value is not None:
                # Only update where RMS value is valid
                valid_rms_mask = rms_value.notna() & (rms_value.astype(str).str.strip() != '')
                final_mask = update_mask & valid_rms_mask
                
                # Apply updates using numpy where for speed (vectorized)
                if final_mask.any():
                    cad_df.loc[final_mask, cad_field] = rms_value.loc[final_mask]
                    
                    backfilled_count = final_mask.sum()
                    self.stats['fields_backfilled'][cad_field] += backfilled_count
                    
                    # Log backfills (sample first 1000 for performance)
                    if len(self.stats['backfill_log']) < 1000:
                        log_indices = final_mask[final_mask].index[:1000]
                        for idx in log_indices:
                            self.stats['backfill_log'].append({
                                'row': idx,
                                'field': cad_field,
                                'cad_original': str(merged.at[idx, cad_field]) if pd.notna(merged.at[idx, cad_field]) else '',
                                'rms_value': str(rms_value.at[idx]),
                                'join_key': merged.at[idx, join_key_cad]
                            })
        
        # Clean up temporary columns
        cad_df = cad_df.drop(columns=['_join_key_normalized'], errors='ignore')
        
        # Log summary
        logger.info("Backfill summary:")
        for field, count in self.stats['fields_backfilled'].items():
            logger.info(f"  {field}: {count:,} records backfilled")
        
        return cad_df
    
    def get_stats(self) -> Dict:
        """Get backfill statistics."""
        return self.stats.copy()
    
    def save_backfill_log(self, output_path: Path):
        """Save detailed backfill log to CSV."""
        if self.stats['backfill_log']:
            log_df = pd.DataFrame(self.stats['backfill_log'])
            log_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"Saved backfill log to {output_path}")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Backfill CAD data from RMS records'
    )
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input CAD CSV/Excel file path'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file path (default: input file with _rms_backfilled suffix)'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to config_enhanced.json (optional)'
    )
    parser.add_argument(
        '--merge-policy',
        type=str,
        help='Path to cad_to_rms_field_map_latest.json (optional)'
    )
    parser.add_argument(
        '--log',
        type=str,
        help='Path to save backfill log CSV (optional)'
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
            output_path = input_path.parent / f"{input_path.stem}_rms_backfilled.csv"
        else:
            output_path = input_path.parent / f"{input_path.stem}_rms_backfilled.xlsx"
    
    # Load CAD data
    logger.info(f"Loading CAD data from: {input_path}")
    if input_path.suffix.lower() == '.csv':
        cad_df = pd.read_csv(input_path, dtype=str, encoding='utf-8-sig')
    else:
        cad_df = pd.read_excel(input_path, dtype=str)
    
    logger.info(f"Loaded {len(cad_df):,} CAD records")
    
    # Initialize backfill processor
    backfiller = UnifiedRMSBackfill(
        config_path=args.config,
        merge_policy_path=args.merge_policy
    )
    
    # Perform backfill
    start_time = datetime.now()
    cad_backfilled = backfiller.backfill_from_rms(cad_df)
    elapsed_time = (datetime.now() - start_time).total_seconds()
    
    # Save results
    logger.info(f"Saving results to: {output_path}")
    if args.format == 'csv':
        cad_backfilled.to_csv(output_path, index=False, encoding='utf-8-sig')
    else:
        cad_backfilled.to_excel(output_path, index=False, engine='openpyxl')
    
    # Save backfill log if requested
    if args.log:
        backfiller.save_backfill_log(Path(args.log))
    
    # Print summary
    stats = backfiller.get_stats()
    print("\n" + "="*80)
    print("RMS BACKFILL SUMMARY")
    print("="*80)
    print(f"CAD records processed:  {stats['cad_records_processed']:,}")
    print(f"RMS records loaded:     {stats['rms_records_loaded']:,}")
    print(f"Matches found:          {stats['matches_found']:,} "
          f"({stats['matches_found']/max(stats['cad_records_processed'],1)*100:.1f}%)")
    print(f"\nFields backfilled:")
    for field, count in stats['fields_backfilled'].items():
        print(f"  {field:20s} {count:>10,} records")
    print(f"\nProcessing time:        {elapsed_time:.2f} seconds")
    print(f"Output file:            {output_path}")
    print("="*80)


if __name__ == "__main__":
    main()

