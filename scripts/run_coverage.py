#!/usr/bin/env python
"""
Test Coverage Report Generator

This script runs the test suite with coverage analysis and generates
detailed reports in multiple formats.

Usage:
    python run_coverage.py [--format {text,html,xml,all}] [--open]

Options:
    --format FORMAT    Coverage report format (default: all)
    --open             Open HTML report in browser when complete
    --min-coverage PCT Minimum required coverage percentage (default: 80)
    --fail-under       Exit with error if coverage is below minimum
"""

import os
import sys
import argparse
import subprocess
import webbrowser
from pathlib import Path

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Generate test coverage reports")
    parser.add_argument(
        "--format", 
        choices=["text", "html", "xml", "all"], 
        default="all",
        help="Coverage report format (default: all)"
    )
    parser.add_argument(
        "--open", 
        action="store_true",
        help="Open HTML report in browser when complete"
    )
    parser.add_argument(
        "--min-coverage", 
        type=float,
        default=80.0,
        help="Minimum required coverage percentage (default: 80)"
    )
    parser.add_argument(
        "--fail-under", 
        action="store_true",
        help="Exit with error if coverage is below minimum"
    )
    
    return parser.parse_args()

def run_tests_with_coverage(args):
    """Run tests with coverage collection"""
    print("Running tests with coverage collection...")
    
    # Build pytest command
    pytest_cmd = ["pytest"]
    
    # Add coverage options based on format
    if args.format == "all" or args.format == "xml":
        pytest_cmd.extend(["--cov-report=xml"])
    
    if args.format == "all" or args.format == "html":
        pytest_cmd.extend(["--cov-report=html"])
    
    if args.format == "all" or args.format == "text":
        pytest_cmd.extend(["--cov-report=term-missing"])
    
    # Add coverage target
    pytest_cmd.extend(["--cov=ModularMind", "--cov-branch"])
    
    # Run the tests
    result = subprocess.run(pytest_cmd, capture_output=True, text=True)
    
    # Print test output
    print(result.stdout)
    
    if result.stderr:
        print("Errors:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    
    return result.returncode

def extract_coverage_percentage(coverage_output):
    """Extract the coverage percentage from the coverage output"""
    # This is a simple approach and might need adjustments based on your coverage tool's output format
    for line in coverage_output.splitlines():
        if "TOTAL" in line and "%" in line:
            # Example line: "TOTAL                    3981    140    96%"
            parts = line.split()
            for part in parts:
                if "%" in part:
                    return float(part.replace("%", ""))
    return None

def open_html_report():
    """Open the HTML coverage report in the default browser"""
    report_path = Path("coverage_html_report/index.html")
    if report_path.exists():
        print(f"Opening HTML report: {report_path.absolute()}")
        webbrowser.open(f"file://{report_path.absolute()}")
    else:
        print(f"HTML report not found at {report_path.absolute()}")

def main():
    """Main function"""
    args = parse_args()
    
    # Run tests with coverage
    return_code = run_tests_with_coverage(args)
    
    # Open HTML report if requested
    if args.open and (args.format == "all" or args.format == "html"):
        open_html_report()
    
    # Check coverage percentage if required
    if args.fail_under:
        try:
            # Read the coverage XML report
            from xml.etree import ElementTree
            tree = ElementTree.parse("coverage.xml")
            root = tree.getroot()
            
            # Extract the coverage percentage
            line_rate = float(root.attrib.get("line-rate", 0)) * 100
            
            print(f"Overall coverage: {line_rate:.2f}%")
            print(f"Minimum required: {args.min_coverage:.2f}%")
            
            if line_rate < args.min_coverage:
                print(f"ERROR: Coverage {line_rate:.2f}% is below the minimum required {args.min_coverage:.2f}%")
                sys.exit(1)
            else:
                print(f"SUCCESS: Coverage {line_rate:.2f}% meets the minimum requirement of {args.min_coverage:.2f}%")
        except Exception as e:
            print(f"Failed to check coverage percentage: {e}")
            if return_code != 0:
                sys.exit(return_code)
    
    # Exit with the return code from pytest
    sys.exit(return_code)

if __name__ == "__main__":
    main()