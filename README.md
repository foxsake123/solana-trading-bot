# Solana Trading Bot

## Project Structure

This project has been organized into the following directory structure:

- `core/`: Core application files (main.py, database.py, etc.)
- `dashboard/`: Dashboard-related files
- `utils/`: Utility scripts and tools
- `patches/`: Patch files to fix issues
- `tests/`: Test files and scripts
- `backups/`: Backup files
- `docs/`: Documentation
- `old_files/`: Old/deprecated files

## Running the Bot

To run the bot:

```
python core/main.py
```

To run the dashboard:

```
streamlit run core/dashboard.py
```

## Setting Up the Environment

Run the setup script to set up the environment:

```
python setup.py
```

This will:
1. Create a virtual environment if needed
2. Install requirements
3. Create symlinks to utility scripts

## Diagnostics

If you encounter issues with the bot, you can run diagnostics:

```
python core/solana_diagnostic.py
```

## Solana Connection Test

To test your Solana connection:

```
python core/solana_connection_test.py
```
