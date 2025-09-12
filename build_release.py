#!/usr/bin/env python3
"""Build script for creating distributable MTG Commander Game releases."""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required build tools are installed."""
    required_tools = ["pyinstaller"]
    missing = []
    
    for tool in required_tools:
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(tool)
    
    if missing:
        print(f"❌ Missing required tools: {', '.join(missing)}")
        print("Install with: pip install pyinstaller")
        return False
    
    return True

def clean_build_dirs():
    """Clean previous build directories."""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    
    for dirname in dirs_to_clean:
        if os.path.exists(dirname):
            print(f"🧹 Cleaning {dirname}/")
            shutil.rmtree(dirname)
    
    # Clean .pyc files
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".pyc"):
                os.remove(os.path.join(root, file))

def create_spec_file():
    """Create PyInstaller spec file for advanced configuration."""
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

block_cipher = None

# Get the current directory
current_dir = Path.cwd()

# Data files to include
datas = [
    (str(current_dir / 'data'), 'data'),
    (str(current_dir / 'ui' / 'theme.py'), 'ui'),
    ('README.md', '.'),
    ('QUICKSTART.md', '.'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtWidgets',
    'PySide6.QtGui',
    'engine',
    'engine.game_controller',
    'engine.game_state',
    'engine.mana',
    'engine.card_engine',
    'engine.casting_system',
    'engine.abilities_system',
    'engine.combat',
    'engine.stack_system',
    'engine.rules_engine',
    'ui',
    'ui.theme',
    'ai',
    'ai.basic_ai',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MTG-Commander',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)
'''
    
    with open("mtg_commander.spec", "w") as f:
        f.write(spec_content.strip())
    
    print("📝 Created PyInstaller spec file")

def build_executable():
    """Build the executable using PyInstaller."""
    print("🔨 Building executable...")
    
    try:
        # Use spec file for more control
        result = subprocess.run([
            "pyinstaller",
            "--clean",
            "mtg_commander.spec"
        ], check=True, capture_output=True, text=True)
        
        print("✅ Executable built successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def create_installer_batch():
    """Create a simple batch file installer for Windows."""
    batch_content = '''@echo off
title MTG Commander Game Installer

echo ================================
echo   MTG Commander Game Installer
echo ================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as administrator...
) else (
    echo Warning: Not running as administrator. Some features may not work.
    echo.
)

echo Installing MTG Commander Game...
echo.

REM Create program directory if it doesn't exist
if not exist "%ProgramFiles%\\MTG Commander" (
    mkdir "%ProgramFiles%\\MTG Commander"
)

REM Copy files
echo Copying application files...
xcopy /E /Y "." "%ProgramFiles%\\MTG Commander\\"

REM Create desktop shortcut
echo Creating desktop shortcut...
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\\Desktop\\MTG Commander.lnk'); $Shortcut.TargetPath = '%ProgramFiles%\\MTG Commander\\MTG-Commander.exe'; $Shortcut.Save()"

REM Create start menu shortcut
echo Creating start menu shortcut...
if not exist "%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\Games" (
    mkdir "%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\Games"
)
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%ProgramData%\\Microsoft\\Windows\\Start Menu\\Programs\\Games\\MTG Commander.lnk'); $Shortcut.TargetPath = '%ProgramFiles%\\MTG Commander\\MTG-Commander.exe'; $Shortcut.Save()"

echo.
echo ================================
echo   Installation Complete!
echo ================================
echo.
echo You can now run MTG Commander from:
echo - Desktop shortcut
echo - Start Menu ^> Games ^> MTG Commander
echo - "%ProgramFiles%\\MTG Commander\\MTG-Commander.exe"
echo.
pause
'''
    
    with open("dist/install.bat", "w") as f:
        f.write(batch_content)
    
    print("📦 Created installer batch file")

def create_release_package():
    """Create the final release package."""
    print("📦 Creating release package...")
    
    if not os.path.exists("dist/MTG-Commander.exe"):
        print("❌ Executable not found in dist/")
        return False
    
    # Create release directory
    release_dir = "dist/MTG-Commander-v1.0.0"
    os.makedirs(release_dir, exist_ok=True)
    
    # Copy executable
    shutil.copy("dist/MTG-Commander.exe", release_dir)
    
    # Copy essential files
    essential_files = ["README.md", "QUICKSTART.md"]
    for file in essential_files:
        if os.path.exists(file):
            shutil.copy(file, release_dir)
    
    # Copy data directory
    if os.path.exists("data"):
        shutil.copytree("data", f"{release_dir}/data", dirs_exist_ok=True)
    
    # Create installer
    create_installer_batch()
    shutil.copy("dist/install.bat", release_dir)
    
    # Create ZIP archive
    shutil.make_archive(release_dir, 'zip', 'dist', 'MTG-Commander-v1.0.0')
    
    print(f"✅ Release package created: {release_dir}.zip")
    return True

def main():
    """Main build process."""
    print("🚀 MTG Commander Game Release Builder")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Clean previous builds
    clean_build_dirs()
    
    # Create spec file
    create_spec_file()
    
    # Build executable
    if not build_executable():
        sys.exit(1)
    
    # Create release package
    if not create_release_package():
        sys.exit(1)
    
    print("\n🎉 Build completed successfully!")
    print("📁 Release package: dist/MTG-Commander-v1.0.0.zip")
    print("💡 Run install.bat in the extracted folder to install on Windows")

if __name__ == "__main__":
    main()
