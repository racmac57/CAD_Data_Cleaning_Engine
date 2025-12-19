"""
File integrity hashing utilities for CAD data processing pipeline.

Provides SHA256 hashing for files to detect silent corruption and
track file changes throughout the processing pipeline.
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import logging


class FileHashManager:
    """Manages file hashing and integrity verification."""

    def __init__(self, manifest_path: str = "data/audit/hash_manifest.json"):
        """
        Initialize hash manager.

        Args:
            manifest_path: Path to JSON file storing hash manifest
        """
        self.manifest_path = Path(manifest_path)
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest = self._load_manifest()
        self.logger = logging.getLogger(__name__)

    def _load_manifest(self) -> Dict:
        """Load existing hash manifest or create new one."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {"version": "1.0", "files": {}}
        return {"version": "1.0", "files": {}}

    def _save_manifest(self):
        """Save hash manifest to disk."""
        self.manifest["last_updated"] = datetime.now().isoformat()
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2)

    def compute_file_hash(self, file_path: str, algorithm: str = 'sha256') -> str:
        """
        Compute hash of a file.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm (sha256, md5, sha1)

        Returns:
            Hexadecimal hash string
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        hash_obj = hashlib.new(algorithm)
        chunk_size = 8192

        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hash_obj.update(chunk)

        return hash_obj.hexdigest()

    def record_file_hash(
        self,
        file_path: str,
        stage: str = "unknown",
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Compute and record file hash in manifest.

        Args:
            file_path: Path to file
            stage: Processing stage (e.g., "input", "cleaned", "output")
            metadata: Optional metadata about the file

        Returns:
            Hash value
        """
        file_path = Path(file_path)
        file_hash = self.compute_file_hash(file_path)

        file_info = {
            "hash": file_hash,
            "algorithm": "sha256",
            "size_bytes": file_path.stat().st_size,
            "stage": stage,
            "timestamp": datetime.now().isoformat(),
            "path": str(file_path.resolve())
        }

        if metadata:
            file_info["metadata"] = metadata

        # Use relative path as key
        key = f"{file_path.name}_{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.manifest["files"][key] = file_info
        self._save_manifest()

        self.logger.info(f"Recorded hash for {file_path.name} (stage: {stage})")
        self.logger.info(f"  Hash: {file_hash[:16]}...")
        self.logger.info(f"  Size: {file_info['size_bytes']:,} bytes")

        return file_hash

    def verify_file_hash(self, file_path: str, expected_hash: str) -> bool:
        """
        Verify a file's hash matches expected value.

        Args:
            file_path: Path to file
            expected_hash: Expected hash value

        Returns:
            True if hash matches, False otherwise
        """
        actual_hash = self.compute_file_hash(file_path)
        matches = actual_hash == expected_hash

        if matches:
            self.logger.info(f"Hash verification PASSED for {Path(file_path).name}")
        else:
            self.logger.error(f"Hash verification FAILED for {Path(file_path).name}")
            self.logger.error(f"  Expected: {expected_hash[:16]}...")
            self.logger.error(f"  Actual:   {actual_hash[:16]}...")

        return matches

    def compare_files(self, file1: str, file2: str) -> bool:
        """
        Compare two files by hash.

        Args:
            file1: Path to first file
            file2: Path to second file

        Returns:
            True if files are identical, False otherwise
        """
        hash1 = self.compute_file_hash(file1)
        hash2 = self.compute_file_hash(file2)

        matches = hash1 == hash2

        self.logger.info(f"File comparison: {Path(file1).name} vs {Path(file2).name}")
        self.logger.info(f"  Result: {'IDENTICAL' if matches else 'DIFFERENT'}")

        return matches

    def get_file_history(self, file_name: str) -> List[Dict]:
        """
        Get processing history for a file.

        Args:
            file_name: Name of file to look up

        Returns:
            List of file records from manifest
        """
        history = []
        for key, info in self.manifest["files"].items():
            if file_name in key:
                history.append(info)

        # Sort by timestamp
        history.sort(key=lambda x: x["timestamp"])
        return history

    def detect_changes(self, file_path: str, stage: str) -> Optional[Dict]:
        """
        Detect if file has changed since last recorded hash.

        Args:
            file_path: Path to file
            stage: Processing stage to compare against

        Returns:
            Dict with change information or None if no previous record
        """
        file_path = Path(file_path)
        current_hash = self.compute_file_hash(file_path)

        # Find most recent record for this file and stage
        for key, info in sorted(
            self.manifest["files"].items(),
            key=lambda x: x[1]["timestamp"],
            reverse=True
        ):
            if file_path.name in key and info["stage"] == stage:
                changed = current_hash != info["hash"]
                return {
                    "changed": changed,
                    "previous_hash": info["hash"],
                    "current_hash": current_hash,
                    "previous_timestamp": info["timestamp"],
                    "current_timestamp": datetime.now().isoformat()
                }

        return None

    def generate_integrity_report(self) -> str:
        """
        Generate integrity report for all tracked files.

        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 80,
            "FILE INTEGRITY REPORT",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Manifest: {self.manifest_path}",
            f"Total Files Tracked: {len(self.manifest['files'])}",
            "",
            "Files by Stage:",
            "-" * 80
        ]

        # Group by stage
        by_stage = {}
        for key, info in self.manifest["files"].items():
            stage = info["stage"]
            if stage not in by_stage:
                by_stage[stage] = []
            by_stage[stage].append(info)

        for stage, files in sorted(by_stage.items()):
            report_lines.append(f"\n{stage.upper()} ({len(files)} files):")
            for file_info in sorted(files, key=lambda x: x["timestamp"]):
                file_name = Path(file_info["path"]).name
                report_lines.append(f"  {file_name}")
                report_lines.append(f"    Hash: {file_info['hash'][:16]}...")
                report_lines.append(f"    Size: {file_info['size_bytes']:,} bytes")
                report_lines.append(f"    Time: {file_info['timestamp']}")

        report_lines.append("\n" + "=" * 80)

        return "\n".join(report_lines)

    def export_manifest(self, output_path: str):
        """
        Export manifest to a different location.

        Args:
            output_path: Path to export manifest
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest, f, indent=2)

        self.logger.info(f"Manifest exported to {output_path}")


# Convenience functions
def compute_hash(file_path: str) -> str:
    """
    Compute SHA256 hash of a file (convenience function).

    Args:
        file_path: Path to file

    Returns:
        Hexadecimal hash string
    """
    manager = FileHashManager()
    return manager.compute_file_hash(file_path)


def verify_integrity(file_path: str, expected_hash: str) -> bool:
    """
    Verify file integrity (convenience function).

    Args:
        file_path: Path to file
        expected_hash: Expected hash value

    Returns:
        True if hash matches, False otherwise
    """
    manager = FileHashManager()
    return manager.verify_file_hash(file_path, expected_hash)


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Create hash manager
    manager = FileHashManager("test_manifest.json")

    # Example: Record hash of input file
    # hash_value = manager.record_file_hash(
    #     "data/input/cad_data.xlsx",
    #     stage="input",
    #     metadata={"description": "Raw CAD export"}
    # )

    # Example: Verify file hasn't changed
    # is_valid = manager.verify_file_hash("data/input/cad_data.xlsx", hash_value)

    # Generate report
    print(manager.generate_integrity_report())
