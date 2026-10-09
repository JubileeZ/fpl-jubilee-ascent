"""Alternate launcher for the complete Streamlit dashboard."""

import subprocess
import sys
from pathlib import Path


def launch(arguments: list[str]) -> int:
    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(script), "--server.address=127.0.0.1", *arguments])


def main() -> None:
    raise SystemExit(launch(sys.argv[1:]))


if __name__ == "__main__":
    main()
