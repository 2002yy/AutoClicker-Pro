import argparse
import os
import subprocess
import sys
from pathlib import Path

SOURCE_FILE = "main.py"
EXE_NAME = "AutoClickerPro"


def install_deps() -> None:
    """Install local packaging dependencies for an interactive developer build."""
    required = {
        "PyInstaller": "pyinstaller",
        "pynput": "pynput",
        "cryptography": "cryptography",
    }
    for module_name, package_name in required.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"Installing missing package: {package_name}")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package_name]
            )


def build() -> Path:
    """Build the same single-file, windowed executable locally and in CI."""
    source = Path(SOURCE_FILE)
    if not source.is_file():
        raise FileNotFoundError(
            f"Cannot find {SOURCE_FILE}. Run this script from the repository root."
        )

    import PyInstaller.__main__

    # 1. 组装 PyInstaller 参数（单文件、无控制台窗口）
    # 注意：应用使用标准 tkinter/ttk，不依赖 customtkinter，故不收集该包
    args = [
        str(source),
        f"--name={EXE_NAME}",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--clean",
    ]

    icon = Path("icon.ico")
    if icon.is_file():
        args.append(f"--icon={icon}")

    print(f"Building {EXE_NAME} from {SOURCE_FILE}...")
    PyInstaller.__main__.run(args)

    suffix = ".exe" if os.name == "nt" else ""
    artifact = Path("dist") / f"{EXE_NAME}{suffix}"
    if not artifact.is_file() or artifact.stat().st_size == 0:
        raise RuntimeError(f"Build completed without a valid artifact: {artifact}")

    print(f"Build artifact: {artifact} ({artifact.stat().st_size} bytes)")
    return artifact


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build AutoClickerPro with PyInstaller")
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Do not install packages or wait for interactive input.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if not args.ci:
            install_deps()
        build()
        return 0
    except Exception as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = main()
    if "--ci" not in sys.argv:
        input("Press Enter to exit...")
    raise SystemExit(exit_code)
