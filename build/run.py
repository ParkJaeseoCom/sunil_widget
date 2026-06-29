import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from teacher_widgets.main import main

if __name__ == "__main__":
    raise SystemExit(main())
