
import os
import shutil
import subprocess
import sys
import platform
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent.parent
    builder_dir = root_dir / "builder"
    temp_dir = builder_dir / "temp"
    output_dir = builder_dir / "output"
    spec_file = root_dir / "LivingScroll.spec"

    print(f"[Build] Root: {root_dir}")
    print(f"[Build] Output: {output_dir}")

    # Ensure running in venv might be good, but let's assume user knows or we are called via python
    # Check for pyinstaller
    pyinstaller_cmd = shutil.which("pyinstaller")
    if not pyinstaller_cmd:
        print("Error: 'pyinstaller' not found. Please run 'pip install .[build]'")
        sys.exit(1)

    # Clean previous build artifacts
    if temp_dir.exists():
        print("[Build] Cleaning contents of temp directory...")
        shutil.rmtree(temp_dir)
    if output_dir.exists():
         print("[Build] Cleaning output directory...")
         shutil.rmtree(output_dir)
    
    # Create required directories
    # PyInstaller creates workpath/distpath, we just need to make sure we don't error
    output_dir.mkdir(parents=True, exist_ok=True)

    # PyInstaller Arguments
    # --distpath: Where the final app goes (initially temp, then we move)
    # --workpath: Where intermediate build files go
    # --clean: Clean cache
    # --noconfirm: Don't ask to overwrite
    cmd = [
        pyinstaller_cmd,
        "--clean",
        "--noconfirm",
        "--distpath", str(temp_dir / "dist"),
        "--workpath", str(temp_dir / "build"),
        str(spec_file)
    ]

    print(f"[Build] Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Build failed with code {e.returncode}")
        sys.exit(e.returncode)

    # Move artifact to output
    dist_dir = temp_dir / "dist" / "LivingScroll"
    # If one-file mode, it might be a file. But our spec uses COLLECT, so it's likely a dir.
    # Let's check.
    
    # Logic for Directory-based build (onedir)
    if dist_dir.exists():
        destination = output_dir / "LivingScroll"
        print(f"[Build] Moving artifact to {destination}")
        shutil.move(str(dist_dir), str(destination))
    else:
        # Fallback for onefile or different name
        # Spec name is LivingScroll
        dist_file = temp_dir / "dist" / "LivingScroll.exe" # Windows
        if not dist_file.exists():
             dist_file = temp_dir / "dist" / "LivingScroll" # Linux/Mac binary
        
        if dist_file.exists():
             print(f"[Build] Moving artifact to {output_dir}")
             shutil.move(str(dist_file), str(output_dir))
        else:
             print("Error: Could not locate built artifact in dist path.")
             sys.exit(1)

    # Cleanup Temp
    print("[Build] Cleaning up temporary build files...")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    
    # Remove spec file if it was generated? No, ours is permanent.
    
    print("[Build] Success!")
    print(f"[Build] Artifact available at: {output_dir / 'LivingScroll'}")

if __name__ == "__main__":
    main()
