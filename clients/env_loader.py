import os
import sys
from pathlib import Path

def configure_utf8_stdio() -> None:
    # ponytail: reconfigure stdio to UTF-8 so non-ASCII player names (é, ć, ø, ñ)
    # don't crash on Windows cp1252 consoles. No-op where stdout is already UTF-8 (mac/linux).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

def load_env(env_path: Path | None = None) -> None:
    """Loads environment variables from a .env file if it exists."""
    if env_path is None:
        env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if key and key not in os.environ:
                os.environ[key] = val
