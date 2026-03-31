#!/usr/bin/env python3
"""
NSU Degree Audit - Load Test Runner
====================================
Convenient script to run load tests with preset configurations.

Usage:
  python tests/run_load_test.py              # Run default test (20 users, 2 min)
  python tests/run_load_test.py --quick      # Quick test (5 users, 30 sec)
  python tests/run_load_test.py --stress     # Stress test (50 users, 5 min)
  python tests/run_load_test.py --local      # Test against localhost
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# Default configuration
DEFAULT_HOST = "https://ocrapi.nsunexus.app"
LOCAL_HOST = "http://localhost:8080"

# Test presets
PRESETS = {
    "default": {
        "users": 20,
        "spawn_rate": 2,
        "run_time": "2m",
        "description": "Standard test: 20 concurrent users for 2 minutes"
    },
    "quick": {
        "users": 5,
        "spawn_rate": 1,
        "run_time": "30s",
        "description": "Quick smoke test: 5 users for 30 seconds"
    },
    "stress": {
        "users": 50,
        "spawn_rate": 5,
        "run_time": "5m",
        "description": "Stress test: 50 concurrent users for 5 minutes"
    },
    "concurrent20": {
        "users": 20,
        "spawn_rate": 20,  # All at once
        "run_time": "3m",
        "description": "20 Concurrent Users test (all spawned at once)"
    }
}


def ensure_reports_dir():
    """Create reports directory if it doesn't exist."""
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    return reports_dir


def run_load_test(host: str, preset: str = "default", html_report: bool = True):
    """Run locust load test with given configuration."""
    
    config = PRESETS.get(preset, PRESETS["default"])
    
    print("\n" + "="*70)
    print("NSU DEGREE AUDIT - AUTOMATED LOAD TEST")
    print("="*70)
    print(f"Preset:      {preset}")
    print(f"Description: {config['description']}")
    print(f"Host:        {host}")
    print(f"Users:       {config['users']}")
    print(f"Spawn Rate:  {config['spawn_rate']} users/sec")
    print(f"Duration:    {config['run_time']}")
    print("="*70 + "\n")
    
    # Build locust command
    locustfile = Path(__file__).parent / "locustfile.py"
    
    cmd = [
        sys.executable, "-m", "locust",
        "-f", str(locustfile),
        f"--host={host}",
        "--headless",
        f"--users={config['users']}",
        f"--spawn-rate={config['spawn_rate']}",
        f"--run-time={config['run_time']}",
    ]
    
    # Add HTML report
    if html_report:
        reports_dir = ensure_reports_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"load_test_{preset}_{timestamp}.html"
        cmd.append(f"--html={report_file}")
        print(f"Report will be saved to: {report_file}\n")
    
    # Add CSV output for CI parsing
    if html_report:
        csv_prefix = reports_dir / f"load_test_{preset}_{timestamp}"
        cmd.append(f"--csv={csv_prefix}")
    
    # Run the test
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
        return result.returncode
    except FileNotFoundError:
        print("\n❌ ERROR: Locust not installed!")
        print("Install with: pip install locust")
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        return 130


def main():
    parser = argparse.ArgumentParser(
        description="Run NSU Degree Audit load tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tests/run_load_test.py                    # Standard 20 user test
  python tests/run_load_test.py --quick            # Quick 5 user test
  python tests/run_load_test.py --stress           # Heavy 50 user test
  python tests/run_load_test.py --concurrent20     # All 20 users at once
  python tests/run_load_test.py --local            # Test localhost:8080
  python tests/run_load_test.py --host http://localhost:5000  # Custom host
        """
    )
    
    # Preset flags
    parser.add_argument("--quick", action="store_true", help="Quick smoke test (5 users, 30s)")
    parser.add_argument("--stress", action="store_true", help="Stress test (50 users, 5min)")
    parser.add_argument("--concurrent20", action="store_true", help="20 users spawned at once")
    
    # Host options
    parser.add_argument("--local", action="store_true", help="Test against localhost:8080")
    parser.add_argument("--host", type=str, help="Custom host URL")
    
    # Report options
    parser.add_argument("--no-report", action="store_true", help="Skip HTML report generation")
    
    args = parser.parse_args()
    
    # Determine preset
    if args.quick:
        preset = "quick"
    elif args.stress:
        preset = "stress"
    elif args.concurrent20:
        preset = "concurrent20"
    else:
        preset = "default"
    
    # Determine host
    if args.host:
        host = args.host
    elif args.local:
        host = LOCAL_HOST
    else:
        host = DEFAULT_HOST
    
    # Run the test
    exit_code = run_load_test(
        host=host,
        preset=preset,
        html_report=not args.no_report
    )
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
