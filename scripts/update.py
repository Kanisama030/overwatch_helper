import os
import subprocess
import sys


def main():
    print("⚠️  scripts/update.py 已轉為相容入口，建議改用 scripts/update_data.py。")
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "update_data.py"), *sys.argv[1:]]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
