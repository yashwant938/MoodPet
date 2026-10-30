"""Build with a minimal Windows PATH to avoid bundling unrelated Qt/ICU DLLs."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    if sys.platform != "win32":
        raise SystemExit("MoodPet packaging currently supports Windows only")
    root = Path(__file__).resolve().parents[1]
    windows = Path(os.environ["SystemRoot"])
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(map(str, [Path(sys.executable).parent, Path(sys.base_prefix), windows / "System32", windows]))
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir", "--name", "MoodPet", "--specpath", "build", "main.py"], cwd=root, env=env, check=True)
    # Qt uses Windows' ICU. A same-named DLL from Poppler/Conda can shadow it.
    if (root / "dist/MoodPet/_internal/icuuc.dll").exists():
        raise SystemExit("Unexpected bundled ICU DLL; inspect the build environment before distributing")


if __name__ == "__main__":
    main()
