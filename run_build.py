#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run([sys.executable, 'scripts/build_app_data.py'], cwd=r'e:\projects\overwatch_helper')
sys.exit(result.returncode)
