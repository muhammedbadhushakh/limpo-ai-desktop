"""
build_exe.py — Run this ONCE on your PC to build the portable .exe
Usage: python build_exe.py
Output: dist/PortableAI/  ← copy this whole folder to your USB
"""

import subprocess, sys, os

# Install dependencies if missing
deps = ["flask", "requests", "pyinstaller"]
for dep in deps:
    subprocess.run([sys.executable, "-m", "pip", "install", dep, "--quiet"], check=True)

# Use "python -m PyInstaller" instead of calling pyinstaller directly
# This fixes the PATH/FileNotFoundError on Windows
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onedir",
    "--windowed",
    "--name", "PortableAI",
    "--add-data", "templates;templates",
    "app.py"
]

print("Building PortableAI.exe...")
print("This may take 1-2 minutes, please wait...\n")
result = subprocess.run(cmd)

if result.returncode == 0:
    print("\n✅ Build complete!")
    print("📁 Your portable app is in: dist\\PortableAI\\")
    print("🔌 Copy the entire 'PortableAI' folder to your USB drive.")
    print("▶️  To run: double-click PortableAI.exe")
else:
    print("\n❌ Build failed. See errors above.")