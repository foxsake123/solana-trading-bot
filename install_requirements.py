"""
Script to install all required packages for both simulation and real trading modes
"""
import os
import sys
import subprocess
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('package_installer')

def check_python_version():
    """Check Python version to ensure compatibility"""
    required_version = (3, 9)
    current_version = sys.version_info
    
    logger.info(f"Python version: {current_version.major}.{current_version.minor}.{current_version.micro}")
    
    if current_version < required_version:
        logger.error(f"Python version {required_version[0]}.{required_version[1]} or higher is required")
        return False
    
    return True

def install_packages(requirements_file=None, packages=None):
    """
    Install packages using pip
    
    :param requirements_file: Path to requirements.txt file
    :param packages: List of package names to install
    :return: True if installation was successful, False otherwise
    """
    try:
        # Install from requirements file if provided
        if requirements_file and os.path.exists(requirements_file):
            logger.info(f"Installing packages from {requirements_file}")
            
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", requirements_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Error installing from {requirements_file}: {result.stderr}")
                return False
            
            logger.info(f"Successfully installed packages from {requirements_file}")
        
        # Install individual packages if provided
        if packages:
            for package in packages:
                logger.info(f"Installing {package}")
                
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Error installing {package}: {result.stderr}")
                    return False
                
                logger.info(f"Successfully installed {package}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error installing packages: {e}")
        return False

def main():
    """Main installation process"""
    logger.info("Starting package installation")
    
    # Check Python version
    if not check_python_version():
        logger.error("Python version check failed. Installation aborted.")
        return
    
    # Create a backup of existing requirements.txt
    if os.path.exists("requirements.txt"):
        backup_file = f"requirements_backup_{int(time.time())}.txt"
        try:
            with open("requirements.txt", "r") as src, open(backup_file, "w") as dst:
                dst.write(src.read())
            logger.info(f"Created backup of requirements.txt: {backup_file}")
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
    
    # Create comprehensive requirements.txt
    full_requirements = """
# Core dependencies
solders==0.19.0
solana==0.30.2
anchorpy==0.18.0
base58==2.1.1
construct==2.10.68
typing-extensions>=4.3.0

# API and Web Integration
tweepy>=4.14.0
python-dotenv>=1.0.0
aiohttp>=3.8.5
httpx>=0.25.0
requests>=2.31.0

# Data processing
pandas>=1.5.0
numpy>=1.25.0

# Analysis
vaderSentiment>=3.3.2
scikit-learn>=1.3.0
joblib>=1.3.0

# Dashboard
streamlit>=1.27.0
plotly>=5.16.0
    """
    
    with open("full_requirements.txt", "w") as f:
        f.write(full_requirements.strip())
        
    logger.info("Created full_requirements.txt with all necessary packages")
    
    # Install basic packages first
    basic_packages = ["pip", "setuptools", "wheel", "python-dotenv", "pandas"]
    if not install_packages(packages=basic_packages):
        logger.error("Failed to install basic packages. Installation aborted.")
        return
    
    # Install packages from full requirements
    if not install_packages(requirements_file="full_requirements.txt"):
        logger.error("Failed to install packages from full_requirements.txt")
        
        # Try installing key packages individually
        key_packages = ["solders", "solana", "anchorpy", "base58"]
        if not install_packages(packages=key_packages):
            logger.error("Failed to install key Solana packages. Installation aborted.")
            logger.error("Please ensure Visual C++ Build Tools are installed correctly.")
            return
    
    logger.info("Package installation completed")
    logger.info("Note: If you encounter any issues with Solana packages, please ensure Visual C++ Build Tools are installed correctly.")

if __name__ == "__main__":
    main()
