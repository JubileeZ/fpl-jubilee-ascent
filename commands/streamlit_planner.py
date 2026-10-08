"""Launch the Streamlit Transfer Planner locally."""

import subprocess
import sys
from pathlib import Path


def main() -> None:
    script = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(script), *sys.argv[1:]]))


if __name__ == "__main__":
    main()
