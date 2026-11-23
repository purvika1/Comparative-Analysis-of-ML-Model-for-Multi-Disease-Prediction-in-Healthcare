"""
Tesseract OCR Diagnostic Script
Run this script as Administrator to test Tesseract accessibility
"""
import os
import subprocess
import sys

def test_tesseract():
    """Test Tesseract OCR installation and accessibility."""
    print("=" * 60)
    print("Tesseract OCR Diagnostic Test")
    print("=" * 60)
    print()
    
    # Check if running as administrator (on Windows)
    if sys.platform == 'win32':
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                print("⚠️  WARNING: Not running as Administrator!")
                print("   Some tests may fail due to permissions.")
                print("   Right-click PowerShell/CMD → 'Run as Administrator'")
                print()
        except:
            pass
    
    # Find Tesseract executable
    tesseract_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
    ]
    
    tesseract_found = False
    tesseract_path = None
    
    print("1. Checking for Tesseract installation...")
    for path in tesseract_paths:
        if os.path.exists(path):
            print(f"   ✅ Found: {path}")
            tesseract_path = path
            tesseract_found = True
            break
    
    if not tesseract_found:
        # Try PATH
        import shutil
        tesseract_cmd = shutil.which('tesseract')
        if tesseract_cmd:
            print(f"   ✅ Found in PATH: {tesseract_cmd}")
            tesseract_path = tesseract_cmd
            tesseract_found = True
    
    if not tesseract_found:
        print("   ❌ Tesseract not found!")
        print("   Please install from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    
    print()
    print("2. Testing Tesseract execution...")
    try:
        result = subprocess.run(
            [tesseract_path, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("   ✅ Tesseract version command succeeded!")
            print(f"   Version info:\n{result.stdout}")
        else:
            print(f"   ❌ Tesseract returned error code: {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False
    except PermissionError as e:
        print(f"   ❌ Permission Error: {str(e)}")
        print("   This indicates Windows is blocking subprocess execution.")
        print("   Solutions:")
        print("   - Run this script as Administrator")
        print("   - Add Tesseract folder to Windows Defender exclusions")
        print("   - Check antivirus settings")
        return False
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    print()
    print("3. Testing file permissions...")
    tesseract_dir = os.path.dirname(tesseract_path)
    if os.access(tesseract_dir, os.R_OK | os.X_OK):
        print(f"   ✅ Read/Execute permissions OK on: {tesseract_dir}")
    else:
        print(f"   ❌ Permission issue with: {tesseract_dir}")
        return False
    
    print()
    print("4. Testing subprocess with CREATE_NO_WINDOW flag...")
    try:
        creation_flags = 0
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creation_flags = subprocess.CREATE_NO_WINDOW
        
        result = subprocess.run(
            [tesseract_path, '--list-langs'],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=creation_flags
        )
        if result.returncode == 0:
            print("   ✅ Subprocess with CREATE_NO_WINDOW succeeded!")
            langs = result.stdout.strip().split('\n')
            print(f"   Available languages: {', '.join(langs[:5])}...")
        else:
            print(f"   ⚠️  Subprocess returned code: {result.returncode}")
    except PermissionError as e:
        print(f"   ❌ Permission Error: {str(e)}")
        return False
    except Exception as e:
        print(f"   ⚠️  Error: {str(e)}")
    
    print()
    print("=" * 60)
    print("✅ All tests passed! Tesseract should work in your application.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_tesseract()
    if not success:
        print()
        print("=" * 60)
        print("TROUBLESHOOTING STEPS:")
        print("=" * 60)
        print("1. Run this script as Administrator")
        print("2. Add 'C:\\Program Files\\Tesseract-OCR' to Windows Defender exclusions")
        print("3. Check if antivirus is blocking subprocess execution")
        print("4. Ensure you have read/execute permissions on Tesseract folder")
        print("5. Try reinstalling Tesseract from:")
        print("   https://github.com/UB-Mannheim/tesseract/wiki")
        sys.exit(1)
    else:
        sys.exit(0)

