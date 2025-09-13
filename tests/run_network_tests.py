#!/usr/bin/env python3
"""MTG Commander Game - Network Multiplayer Test Runner

This script runs comprehensive tests for all network multiplayer components,
including protocols, client/server, UI components, and integration scenarios.
"""

import sys
import unittest
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import test modules directly
try:
    from test_network_protocols import TestMessageProtocol, TestNetworkProtocolIntegration
    from test_network_components import (
        TestNetworkClient, TestGameServer, TestNetworkGameController, TestNetworkIntegration
    )
except ImportError:
    # Fallback: try importing with full path
    import importlib.util
    import os
    
    def import_test_module(module_name):
        file_path = os.path.join(os.path.dirname(__file__), f"{module_name}.py")
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    protocols_module = import_test_module("test_network_protocols")
    TestMessageProtocol = protocols_module.TestMessageProtocol
    TestNetworkProtocolIntegration = protocols_module.TestNetworkProtocolIntegration
    
    components_module = import_test_module("test_network_components")
    TestNetworkClient = components_module.TestNetworkClient
    TestGameServer = components_module.TestGameServer
    TestNetworkGameController = components_module.TestNetworkGameController
    TestNetworkIntegration = components_module.TestNetworkIntegration

# Try to import UI tests (may fail if PySide6 is not available)
ui_tests_available = True
try:
    from test_network_ui import TestNetworkLobbyDialog, TestNetworkStatusWidget, TestUIIntegration
except ImportError as e:
    try:
        # Fallback import
        ui_module = import_test_module("test_network_ui")
        TestNetworkLobbyDialog = ui_module.TestNetworkLobbyDialog
        TestNetworkStatusWidget = ui_module.TestNetworkStatusWidget
        TestUIIntegration = ui_module.TestUIIntegration
    except Exception:
        ui_tests_available = False
        print(f"Warning: UI tests not available ({e})")
        print("Install PySide6 to run UI tests: pip install PySide6")


class NetworkTestResult(unittest.TextTestResult):
    """Custom test result class to track network test statistics."""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.test_categories = {
            'protocol': {'passed': 0, 'failed': 0, 'errors': 0},
            'components': {'passed': 0, 'failed': 0, 'errors': 0},
            'ui': {'passed': 0, 'failed': 0, 'errors': 0},
            'integration': {'passed': 0, 'failed': 0, 'errors': 0}
        }
        self.start_time = None
        self.total_time = 0
    
    def startTest(self, test):
        """Called when a test starts."""
        super().startTest(test)
        if self.start_time is None:
            self.start_time = time.time()
    
    def stopTest(self, test):
        """Called when a test stops."""
        super().stopTest(test)
        self.total_time = time.time() - self.start_time if self.start_time else 0
    
    def addSuccess(self, test):
        """Called when a test passes."""
        super().addSuccess(test)
        category = self._get_test_category(test)
        self.test_categories[category]['passed'] += 1
    
    def addError(self, test, err):
        """Called when a test has an error."""
        super().addError(test, err)
        category = self._get_test_category(test)
        self.test_categories[category]['errors'] += 1
    
    def addFailure(self, test, err):
        """Called when a test fails."""
        super().addFailure(test, err)
        category = self._get_test_category(test)
        self.test_categories[category]['failed'] += 1
    
    def _get_test_category(self, test):
        """Determine which category a test belongs to."""
        class_name = test.__class__.__name__
        
        if 'Protocol' in class_name:
            return 'protocol'
        elif any(name in class_name for name in ['Client', 'Server', 'Controller']):
            return 'components'
        elif any(name in class_name for name in ['UI', 'Lobby', 'Widget']):
            return 'ui'
        else:
            return 'integration'
    
    def print_summary(self):
        """Print a detailed test summary."""
        print("\n" + "="*80)
        print("🌐 NETWORK MULTIPLAYER TEST SUMMARY")
        print("="*80)
        
        total_tests = self.testsRun
        total_passed = sum(cat['passed'] for cat in self.test_categories.values())
        total_failed = len(self.failures)
        total_errors = len(self.errors)
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"📊 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {total_passed}")
        print(f"   ❌ Failed: {total_failed}")
        print(f"   🚨 Errors: {total_errors}")
        print(f"   📈 Success Rate: {success_rate:.1f}%")
        print(f"   ⏱️  Total Time: {self.total_time:.2f}s")
        print()
        
        # Category breakdown
        print("📋 Test Category Breakdown:")
        for category, stats in self.test_categories.items():
            total_cat = stats['passed'] + stats['failed'] + stats['errors']
            if total_cat > 0:
                cat_success = (stats['passed'] / total_cat * 100) if total_cat > 0 else 0
                print(f"   🔸 {category.title()}: {stats['passed']}/{total_cat} ({cat_success:.1f}%)")
        print()
        
        # Performance metrics
        avg_time = self.total_time / total_tests if total_tests > 0 else 0
        print(f"⚡ Performance Metrics:")
        print(f"   Average test time: {avg_time:.3f}s")
        if avg_time < 0.1:
            print("   Performance: 🟢 Excellent")
        elif avg_time < 0.5:
            print("   Performance: 🟡 Good")
        else:
            print("   Performance: 🔴 Needs optimization")
        print()
        
        # Failure details
        if self.failures or self.errors:
            print("🚨 Issues Found:")
            for test, error in self.failures:
                print(f"   FAIL: {test}")
            for test, error in self.errors:
                print(f"   ERROR: {test}")
            print()
        
        # Recommendations
        print("💡 Recommendations:")
        if success_rate >= 95:
            print("   🎉 Excellent! Network system is production-ready.")
        elif success_rate >= 80:
            print("   ⚠️  Good coverage. Address remaining failures for production use.")
        else:
            print("   🛠️  Significant issues detected. Review and fix before deployment.")
        
        if not ui_tests_available:
            print("   📦 Install PySide6 to enable complete UI testing coverage.")
        
        print("\n" + "="*80)


class NetworkTestRunner:
    """Main test runner for network multiplayer tests."""
    
    def __init__(self):
        self.test_suites = {
            'protocols': None,
            'components': None,
            'ui': None,
            'integration': None,
            'all': None
        }
        self.setup_test_suites()
    
    def setup_test_suites(self):
        """Set up test suites for different categories."""
        
        # Protocol tests
        protocol_suite = unittest.TestSuite()
        protocol_suite.addTest(unittest.makeSuite(TestMessageProtocol))
        protocol_suite.addTest(unittest.makeSuite(TestNetworkProtocolIntegration))
        self.test_suites['protocols'] = protocol_suite
        
        # Component tests
        components_suite = unittest.TestSuite()
        components_suite.addTest(unittest.makeSuite(TestNetworkClient))
        components_suite.addTest(unittest.makeSuite(TestGameServer))
        components_suite.addTest(unittest.makeSuite(TestNetworkGameController))
        self.test_suites['components'] = components_suite
        
        # Integration tests
        integration_suite = unittest.TestSuite()
        integration_suite.addTest(unittest.makeSuite(TestNetworkIntegration))
        self.test_suites['integration'] = integration_suite
        
        # UI tests (if available)
        if ui_tests_available:
            ui_suite = unittest.TestSuite()
            ui_suite.addTest(unittest.makeSuite(TestNetworkLobbyDialog))
            ui_suite.addTest(unittest.makeSuite(TestNetworkStatusWidget))
            ui_suite.addTest(unittest.makeSuite(TestUIIntegration))
            self.test_suites['ui'] = ui_suite
        
        # All tests combined
        all_suite = unittest.TestSuite()
        for suite in self.test_suites.values():
            if suite is not None:
                all_suite.addTests(suite)
        self.test_suites['all'] = all_suite
    
    def run_tests(self, category='all', verbosity=2):
        """Run tests for a specific category."""
        print("🚀 Starting Network Multiplayer Test Suite")
        print(f"📂 Running category: {category}")
        print("="*60)
        
        if category not in self.test_suites:
            print(f"❌ Unknown test category: {category}")
            print(f"Available categories: {list(self.test_suites.keys())}")
            return False
        
        suite = self.test_suites[category]
        if suite is None:
            print(f"❌ Test suite '{category}' not available")
            return False
        
        # Run the tests
        runner = unittest.TextTestRunner(
            verbosity=verbosity,
            resultclass=NetworkTestResult,
            stream=sys.stdout
        )
        
        result = runner.run(suite)
        
        # Print detailed summary
        if hasattr(result, 'print_summary'):
            result.print_summary()
        
        # Return success status
        return result.wasSuccessful()
    
    def run_quick_test(self):
        """Run a quick smoke test to verify basic functionality."""
        print("🔥 Running Quick Network Smoke Test")
        print("="*40)
        
        # Create a minimal test suite
        quick_suite = unittest.TestSuite()
        
        # Add one test from each category
        quick_suite.addTest(TestMessageProtocol('test_message_type_enum'))
        quick_suite.addTest(TestNetworkClient('test_client_initialization'))
        quick_suite.addTest(TestGameServer('test_server_initialization'))
        quick_suite.addTest(TestNetworkGameController('test_controller_initialization'))
        
        if ui_tests_available:
            # Add basic UI test
            try:
                from PySide6.QtWidgets import QApplication
                if not QApplication.instance():
                    app = QApplication([])
                quick_suite.addTest(TestNetworkStatusWidget('test_widget_initialization'))
            except Exception as e:
                print(f"Skipping UI smoke test: {e}")
        
        # Run quick tests
        runner = unittest.TextTestRunner(verbosity=1)
        result = runner.run(quick_suite)
        
        if result.wasSuccessful():
            print("✅ Quick smoke test passed! Network system looks good.")
        else:
            print("❌ Smoke test failed. Check basic network components.")
        
        return result.wasSuccessful()
    
    def list_available_tests(self):
        """List all available test categories and counts."""
        print("📋 Available Network Test Categories:")
        print("="*50)
        
        for category, suite in self.test_suites.items():
            if suite is not None:
                count = suite.countTestCases()
                print(f"  📂 {category}: {count} tests")
        
        print("\nUsage: python run_network_tests.py [category]")
        print("Example: python run_network_tests.py protocols")


def main():
    """Main entry point for the test runner."""
    
    # Print banner
    print("🌐 MTG Commander Network Multiplayer Test Suite")
    print("="*60)
    print("Testing comprehensive network functionality including:")
    print("• Message protocols and serialization")
    print("• Client/server components")
    print("• UI components and integration")
    print("• End-to-end multiplayer scenarios")
    print()
    
    runner = NetworkTestRunner()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        category = sys.argv[1].lower()
        
        if category == 'list':
            runner.list_available_tests()
            return
        elif category == 'quick':
            success = runner.run_quick_test()
            sys.exit(0 if success else 1)
        else:
            success = runner.run_tests(category)
            sys.exit(0 if success else 1)
    else:
        # Run all tests by default
        print("Running all network tests...")
        success = runner.run_tests('all')
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
