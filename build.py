"""PyInstaller build script. Run from project root: python build.py"""

import subprocess
import sys
import os
import shutil


def build():
    print("=" * 50)
    print("ClearSameFile — PyInstaller 打包")
    print("=" * 50)

    # Clean previous builds
    for d in ["build", "dist"]:
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f"[清理] 删除 {d}/")

    spec_file = "ClearSameFile.spec"
    if os.path.isfile(spec_file):
        os.remove(spec_file)
        print(f"[清理] 删除 {spec_file}")

    print("\n[开始] 正在使用 PyInstaller 打包...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "ClearSameFile",
        "--clean",
        "main.py",
    ]

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode == 0:
        exe_path = os.path.join("dist", "ClearSameFile.exe")
        if os.path.isfile(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n[完成] 打包成功!")
            print(f"[输出] {os.path.abspath(exe_path)}")
            print(f"[大小] {size_mb:.1f} MB")
        else:
            print(f"\n[警告] 打包似乎完成但未找到 EXE 文件")
    else:
        print(f"\n[失败] 打包出错，返回码: {result.returncode}")
        sys.exit(1)


if __name__ == "__main__":
    build()
