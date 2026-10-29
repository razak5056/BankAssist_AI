"""
Lightweight environment and configuration loader for BankAssist AI.
Reads key-value pairs from .env in the project root without external dependencies.
"""

from pathlib import Path
import os


def load_env_file():
    """Reads .env from project root and populates os.environ if not already set."""
    root_dir = Path(__file__).resolve().parents[3]
    env_path = root_dir / ".env"
    if not env_path.is_file():
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key:
                    os.environ[key] = val
    except Exception:
        pass


# Automatically load on import
load_env_file()

