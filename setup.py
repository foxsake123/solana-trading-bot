#!/usr/bin/env python
# setup.py - Setup script for Solana trading bot environment

import os
import sys
import shutil
import subprocess

def create_symlinks():
    """Create symlinks to utility scripts"""
    # Core directory
    core_dir = 'core'
    
    # Utility directories to link from
    util_dirs = ['utils', 'dashboard', 'patches']
    
    # Create links in core directory
    for util_dir in util_dirs:
        if not os.path.exists(util_dir):
            continue
            
        for file in os.listdir(util_dir):
            if file.endswith('.py'):
                # Source and destination paths
                src = os.path.abspath(os.path.join(util_dir, file))
                dst = os.path.abspath(os.path.join(core_dir, file))
                
                # Create symlink
                try:
                    if os.path.exists(dst):
                        os.remove(dst)
                    os.symlink(src, dst)
                    print(f"Created link to {src} in {dst}")
                except Exception as e:
                    print(f"Error creating link for {file}: {e}")

def setup_environment():
    """Set up Python environment"""
    # Check if venv exists
    if not os.path.exists('venv'):
        print("Creating virtual environment...")
        try:
            subprocess.run([sys.executable, '-m', 'venv', 'venv'])
            print("Virtual environment created successfully")
        except Exception as e:
            print(f"Error creating virtual environment: {e}")
            return False
    
    # Activate virtual environment and install requirements
    if os.path.exists('venv'):
        if sys.platform == 'win32':
            pip_path = os.path.join('venv', 'Scripts', 'pip')
        else:
            pip_path = os.path.join('venv', 'bin', 'pip')
            
        # Install requirements if they exist
        req_files = ['requirements.txt', 'requirements_solana.txt']
        for req_file in req_files:
            if os.path.exists(req_file):
                print(f"Installing {req_file}...")
                try:
                    subprocess.run([pip_path, 'install', '-r', req_file])
                    print(f"Installed {req_file} successfully")
                except Exception as e:
                    print(f"Error installing {req_file}: {e}")
    
    return True

def main():
    """Main setup function"""
    print("Setting up Solana trading bot environment...")
    
    # Set up Python environment
    setup_environment()
    
    # Create symlinks to utility scripts
    create_symlinks()
    
    print("Setup complete!")
    print("To run the bot, use: python core/main.py")
    print("To run the dashboard, use: streamlit run core/dashboard.py")

if __name__ == "__main__":
    main()
