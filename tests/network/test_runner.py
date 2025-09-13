#!/usr/bin/env python3
"""MTG Commander Game - Network Test Runner

Centralized test runner for all network-related tests.
This runner provides a single entry point to execute all network tests
with appropriate reporting and error handling.
"""

import sys
import os
import unittest
from typing import List, Optional

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

def discover_network_tests() -> unittest.TestSuite:
    """Discover all network test modules and return a combined test suite."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Test modules to include (in execution order)
    test_modules = [
        'test_network_protocols',
        'test_network_components', 
        'test_network_ui'
    ]
    
    # Import tests from parent tests directory
    tests_dir = os.path.join(os.path.dirname(__file__), '..')
    sys.path.insert(0, tests_dir)
    
    for module_name in test_modules:
        try:
            # Import the test module directly
            module = __import__(module_name)
            
            # Load tests from the module
            module_suite = loader.loadTestsFromModule(module)
            suite.addTest(module_suite)
            
            print(f"✓ Loaded tests from {module_name}")
            
        except ImportError as e:
            print(f"⚠ Failed to import {module_name}: {e}")
        except Exception as e:
            print(f"✗ Error loading tests from {module_name}: {e}")
    
    return suite


def run_specific_test_class(class_name: str, module_name: Optional[str] = None) -> bool:
    """Run tests from a specific test class.
    
    Args:
        class_name: Name of the test class to run
        module_name: Optional specific module to search in
        
    Returns:
        True if tests passed, False otherwise
    """
    loader = unittest.TestLoader()
    
    # Import tests from parent tests directory
    tests_dir = os.path.join(os.path.dirname(__file__), '..')
    sys.path.insert(0, tests_dir)
    
    if module_name:
        # Search in specific module
        try:
            module = __import__(module_name)
            if hasattr(module, class_name):
                suite = loader.loadTestsFromTestCase(getattr(module, class_name))
            else:
                print(f"Test class {class_name} not found in {module_name}")
                return False
        except ImportError:
            print(f"Module {module_name} not found")
            return False
    else:
        # Search in all network test modules
        suite = unittest.TestSuite()
        test_modules = ['test_network_protocols', 'test_network_components', 'test_network_ui']
        
        for mod_name in test_modules:
            try:
                module = __import__(mod_name)
                if hasattr(module, class_name):
                    class_suite = loader.loadTestsFromTestCase(getattr(module, class_name))
                    suite.addTest(class_suite)
                    print(f"✓ Found {class_name} in {mod_name}")
                    break
            except ImportError:
                continue
        else:
            print(f"Test class {class_name} not found in any module")
            return False
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


def run_network_tests(verbosity: int = 2, failfast: bool = False) -> bool:
    """Run all network tests with specified options.
    
    Args:
        verbosity: Test output verbosity (0=quiet, 1=normal, 2=verbose)
        failfast: Stop on first failure if True
        
    Returns:
        True if all tests passed, False otherwise
    """
    print("MTG Commander Game - Network Test Suite")
    print("=" * 50)
    
    # Discover all network tests
    suite = discover_network_tests()
    
    if suite.countTestCases() == 0:
        print("⚠ No tests found to run")
        return False
    
    print(f"\nRunning {suite.countTestCases()} network tests...")
    print("-" * 50)
    
    # Run tests with custom runner
    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        failfast=failfast,
        stream=sys.stdout
    )
    
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("✓ All network tests passed!")
    else:
        print("✗ Some network tests failed")
        
        # Show failure details if not verbose
        if verbosity < 2:
            print("\nFailure Details:")
            for test, error in result.failures + result.errors:
                print(f"- {test}: {error.split(chr(10))[0]}")
    
    return result.wasSuccessful()


def run_smoke_tests() -> bool:
    """Run a minimal subset of tests to verify basic functionality.
    
    Returns:
        True if smoke tests passed, False otherwise
    """
    print("Running network smoke tests...")
    
    # Run only basic protocol and component tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Import tests from parent tests directory
    tests_dir = os.path.join(os.path.dirname(__file__), '..')
    sys.path.insert(0, tests_dir)
    
    try:
        # Basic protocol tests
        from test_network_protocols import TestMessageProtocol
        suite.addTest(loader.loadTestsFromName('test_network_message_creation', TestMessageProtocol))
        suite.addTest(loader.loadTestsFromName('test_checksum_creation', TestMessageProtocol))
        
        # Basic component tests  
        from test_network_components import TestNetworkClient
        suite.addTest(loader.loadTestsFromName('test_client_initialization', TestNetworkClient))
        suite.addTest(loader.loadTestsFromName('test_client_state_transitions', TestNetworkClient))
        
        runner = unittest.TextTestRunner(verbosity=1)
        result = runner.run(suite)
        
        return result.wasSuccessful()
        
    except Exception as e:
        print(f"Error running smoke tests: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MTG Commander Network Test Runner")
    parser.add_argument("-v", "--verbosity", type=int, default=2, choices=[0, 1, 2],
                        help="Test output verbosity level (0=quiet, 1=normal, 2=verbose)")
    parser.add_argument("-f", "--failfast", action="store_true",
                        help="Stop on first failure")
    parser.add_argument("-s", "--smoke", action="store_true",
                        help="Run only smoke tests")
    parser.add_argument("-c", "--class", dest="test_class", 
                        help="Run specific test class")
    parser.add_argument("-m", "--module", dest="test_module",
                        help="Specific module to search for test class (use with --class)")
    
    args = parser.parse_args()
    
    success = False
    
    try:
        if args.smoke:
            success = run_smoke_tests()
        elif args.test_class:
            success = run_specific_test_class(args.test_class, args.test_module)
        else:
            success = run_network_tests(args.verbosity, args.failfast)
            
    except KeyboardInterrupt:
        print("\n\nTest execution interrupted by user")
        success = False
    except Exception as e:
        print(f"\nUnexpected error during test execution: {e}")
        success = False
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
