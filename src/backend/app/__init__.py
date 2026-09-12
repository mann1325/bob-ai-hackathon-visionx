import sys
from pathlib import Path

# Ensure src/ and src/backend/ are in sys.path
backend_dir = Path(__file__).resolve().parent.parent
src_dir = backend_dir.parent

for p in [str(src_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)
