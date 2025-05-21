#!/usr/bin/env python
import subprocess
import sys
import os

print("Starting fixed dashboard...")
try:
    subprocess.run(['streamlit', 'run', 'dashboard_wrapper.py'])
except Exception as e:
    print(f"Error: {e}")
    print("If Streamlit is not installed, run: pip install streamlit")
