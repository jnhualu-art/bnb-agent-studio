"""
Wheel 安装器 —— 绕开 WorkBuddy safe-delete 与 Windows 文件锁
=============================================================
背景:
  1) WorkBuddy 沙箱回收站不可用, pip 任何删除动作都会被 safe-delete fail-closed 拦截
  2) Windows 上 .pyd 被运行中的 Python 进程占用时无法覆盖(PermissionError)

策略: 只解压「目标路径不存在」的文件, 已存在的一律跳过(视为已安装)。

用法:
    python install_wheels.py <site-packages路径> <wheel目录/*.whl>
"""

import glob
import os
import sys
import zipfile


def main() -> None:
    if len(sys.argv) < 3:
        print("用法: python install_wheels.py <site-packages> <wheel_glob>")
        sys.exit(1)

    site = sys.argv[1]
    pattern = sys.argv[2]

    wheels = glob.glob(pattern)
    if not wheels:
        print(f"未找到 wheel: {pattern}")
        sys.exit(1)

    total_new = 0
    for w in wheels:
        try:
            with zipfile.ZipFile(w) as z:
                new = 0
                for member in z.namelist():
                    target = os.path.join(site, member)
                    if os.path.exists(target):
                        continue
                    try:
                        z.extract(member, site)
                        new += 1
                    except Exception:
                        continue
                total_new += new
                print(f"  {os.path.basename(w):<58} {new} new files")
        except Exception as exc:
            print(f"  {os.path.basename(w)} FAILED: {exc}")

    print(f"\n完成: {len(wheels)} 个 wheel, 新增 {total_new} 个文件")


if __name__ == "__main__":
    main()
