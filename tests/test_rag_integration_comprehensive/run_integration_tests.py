#!/usr/bin/env python3
"""
Integration test runner for RAG document processing.

This script runs the comprehensive integration test suite for RAG document
processing integration, including end-to-end workflow tests, regression tests,
performance tests, and stress tests.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def run_test_suite(test_module, verbose=False, capture=True):
    """Run a specific test suite."""
    cmd = [
        sys.executable, "-m", "pytest",
        str(Path(__file__).parent / f"{test_module}.py"),
        "-v" if verbose else "-q",
    ]
    
    if not capture:
        cmd.append("-s")
    
    print(f"\n{'='*60}")
    print(f"Running {test_module}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True)
        
        if capture:
            print(result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {test_module}: {e}")
        return False


def run_all_tests(verbose=False, capture=True, quick=False):
    """Run all integration test suites."""
    test_suites = [
        ("base_test_classes", "Base Test Infrastructure"),
        ("test_end_to_end_workflow", "End-to-End Workflow Tests"),
        ("test_regression", "Regression Tests"),
        ("test_comprehensive_integration", "Comprehensive Integration Tests"),
    ]
    
    if not quick:
        test_suites.append(("test_performance_stress", "Performance and Stress Tests"))
    
    results = {}
    
    print("RAG Integration Test Suite")
    print("=" * 60)
    print(f"Running {len(test_suites)} test suites...")
    
    for test_module, description in test_suites:
        print(f"\n{description}...")
        success = run_test_suite(test_module, verbose, capture)
        results[test_module] = success
        
        if success:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED")
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for test_module, success in results.items():
        status = "PASSED" if success else "FAILED"
        print(f"{test_module:<40} {status}")
    
    print(f"\nOverall: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        return True
    else:
        print("⚠️  Some integration tests failed.")
        return False


def run_specific_test(test_name, verbose=False, capture=True):
    """Run a specific test by name."""
    test_modules = [
        "base_test_classes",
        "test_end_to_end_workflow", 
        "test_regression",
        "test_performance_stress",
        "test_comprehensive_integration"
    ]
    
    # Find matching test module
    matching_modules = [m for m in test_modules if test_name.lower() in m.lower()]
    
    if not matching_modules:
        print(f"No test module found matching '{test_name}'")
        print(f"Available modules: {', '.join(test_modules)}")
        return False
    
    if len(matching_modules) > 1:
        print(f"Multiple modules match '{test_name}': {', '.join(matching_modules)}")
        print("Please be more specific.")
        return False
    
    test_module = matching_modules[0]
    return run_test_suite(test_module, verbose, capture)


def check_dependencies():
    """Check if required dependencies are available."""
    required_modules = [
        "pytest",
        "psutil",  # For performance tests
    ]
    
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print("Missing required dependencies:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\nInstall missing dependencies with:")
        print(f"  pip install {' '.join(missing_modules)}")
        return False
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run RAG integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_integration_tests.py                    # Run all tests
  python run_integration_tests.py --quick            # Run all tests except performance
  python run_integration_tests.py --test workflow    # Run workflow tests only
  python run_integration_tests.py --test regression  # Run regression tests only
  python run_integration_tests.py --verbose          # Run with verbose output
        """
    )
    
    parser.add_argument(
        "--test", "-t",
        help="Run specific test suite (workflow, regression, performance, comprehensive)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--no-capture", "-s",
        action="store_true",
        help="Don't capture output (useful for debugging)"
    )
    
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Skip performance tests (faster execution)"
    )
    
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check dependencies and exit"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    if args.check_deps:
        if check_dependencies():
            print("All dependencies are available.")
            return 0
        else:
            return 1
    
    if not check_dependencies():
        return 1
    
    # Run tests
    if args.test:
        success = run_specific_test(
            args.test,
            verbose=args.verbose,
            capture=not args.no_capture
        )
    else:
        success = run_all_tests(
            verbose=args.verbose,
            capture=not args.no_capture,
            quick=args.quick
        )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())