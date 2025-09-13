#!/usr/bin/env python3
"""Validate Requirements - Check if all dependencies are installed and compatible.

This script validates that the MTG Commander Game has all required dependencies
installed and that they are compatible with the current Python version.
"""

import sys
import os
import importlib
import subprocess
from typing import List, Tuple, Optional

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def check_python_version() -> bool:
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    
    major, minor = sys.version_info[:2]
    required_major, required_minor = 3, 8
    
    if major < required_major or (major == required_major and minor < required_minor):
        print(f"❌ Python {major}.{minor} detected. Requires Python >= {required_major}.{required_minor}")
        return False
    
    print(f"✅ Python {major}.{minor} detected - compatible")
    return True


def check_package_installed(package_name: str, min_version: Optional[str] = None) -> Tuple[bool, str]:
    """Check if a package is installed and optionally check version."""
    try:
        module = importlib.import_module(package_name)
        
        if hasattr(module, '__version__'):
            version = module.__version__
        else:
            # For some packages, try to get version from package metadata
            try:
                import pkg_resources
                version = pkg_resources.get_distribution(package_name).version
            except:
                version = "unknown"
        
        if min_version and version != "unknown":
            # Simple version comparison (assumes semantic versioning)
            installed_parts = [int(x) for x in version.split('.')[:3]]
            required_parts = [int(x) for x in min_version.split('.')[:3]]
            
            # Pad with zeros if needed
            while len(installed_parts) < 3:
                installed_parts.append(0)
            while len(required_parts) < 3:
                required_parts.append(0)
            
            if installed_parts < required_parts:
                return False, f"v{version} (requires >= {min_version})"
        
        return True, f"v{version}"
    
    except ImportError:
        return False, "not installed"


def check_core_dependencies() -> bool:
    """Check core dependencies required for the game to run."""
    print("\n📦 Checking core dependencies...")
    
    core_deps = [
        ("PySide6", "6.7.2"),
        ("PIL", "10.4.0"),  # Pillow imports as PIL
    ]
    
    all_ok = True
    
    for package, min_version in core_deps:
        installed, version_info = check_package_installed(package, min_version)
        
        if installed:
            print(f"   ✅ {package} {version_info}")
        else:
            print(f"   ❌ {package} {version_info}")
            all_ok = False
    
    return all_ok


def check_optional_dependencies() -> bool:
    """Check optional dependencies."""
    print("\n📦 Checking optional dependencies...")
    
    optional_deps = [
        ("mtgsdk", None, "Enhanced card data fetching from MTG API"),
    ]
    
    for package, min_version, description in optional_deps:
        installed, version_info = check_package_installed(package, min_version)
        
        if installed:
            print(f"   ✅ {package} {version_info} - {description}")
        else:
            print(f"   ⚠️  {package} {version_info} - {description} (optional)")
    
    return True  # Optional deps don't affect core functionality


def check_dev_dependencies() -> bool:
    """Check development dependencies."""
    print("\n🛠️  Checking development dependencies...")
    
    dev_deps = [
        ("pyinstaller", None, "Building executable distributions"),
        ("black", None, "Code formatting"),
        ("flake8", None, "Code linting"),
        ("mypy", None, "Type checking"),
    ]
    
    for package, min_version, description in dev_deps:
        installed, version_info = check_package_installed(package, min_version)
        
        if installed:
            print(f"   ✅ {package} {version_info} - {description}")
        else:
            print(f"   ⚠️  {package} {version_info} - {description} (dev only)")
    
    return True  # Dev deps don't affect core functionality


def test_core_imports() -> bool:
    """Test that core game modules can be imported."""
    print("\n🧪 Testing core game imports...")
    
    core_modules = [
        "engine.game_controller",
        "engine.card_engine", 
        "engine.mana",
        "ui.game_app_api",
        "main",
    ]
    
    all_ok = True
    
    for module_name in core_modules:
        try:
            importlib.import_module(module_name)
            print(f"   ✅ {module_name}")
        except ImportError as e:
            print(f"   ❌ {module_name}: {e}")
            all_ok = False
    
    return all_ok


def main():
    """Run all validation checks."""
    print("🔍 MTG Commander Game - Requirements Validation")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Core Dependencies", check_core_dependencies),
        ("Optional Dependencies", check_optional_dependencies), 
        ("Development Dependencies", check_dev_dependencies),
        ("Core Imports", test_core_imports),
    ]
    
    all_passed = True
    results = []
    
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
            if not result and name in ["Python Version", "Core Dependencies", "Core Imports"]:
                all_passed = False
        except Exception as e:
            print(f"❌ Error during {name} check: {e}")
            results.append((name, False))
            if name in ["Python Version", "Core Dependencies", "Core Imports"]:
                all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    if all_passed:
        print("\n🎉 All core requirements satisfied!")
        print("🚀 The MTG Commander Game should run without issues.")
        return True
    else:
        print("\n⚠️  Some core requirements are missing.")
        print("📥 Install missing dependencies with:")
        print("   pip install -r requirements.txt")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
