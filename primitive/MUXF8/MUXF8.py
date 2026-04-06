from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "common"))

from ising_primitive_lib import run_named_primitive


if __name__ == "__main__":
    run_named_primitive("MUXF8", Path(__file__).resolve().parent)
