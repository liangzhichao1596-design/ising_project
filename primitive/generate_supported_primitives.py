from __future__ import annotations

import json
from pathlib import Path

from common.ising_primitive_lib import PRIMITIVES, run_named_primitive, wrapper_script_text, write_supported_manifest


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
PDF_PATH = PROJECT_ROOT / "ug953-vivado-7series-libraries-en-us-2024.1.pdf"


def write_readme() -> None:
    manifest_path = ROOT / "supported_primitives.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    supported = [row["primitive"] for row in payload if row["status"] == "supported"]
    unsupported = [row for row in payload if row["status"] == "unsupported"]

    lines = [
        "# Primitive Ising Reports",
        "",
        "This directory contains Chapter 5 UG953 primitive wrappers and generated `.log` reports.",
        "",
        "Implemented primitives:",
        *[f"- {name}" for name in supported],
        "",
        "Unsupported primitives in this pass:",
        *[f"- {row['primitive']}: {row['reason']}" for row in unsupported],
        "",
        "LUT notes:",
        "- `LUT1`..`LUT6` scripts accept `--init`.",
        "- `LUT6_2` also uses `--init`; the default value realizes O5=AND5 and O6=AND6.",
    ]
    (ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    write_supported_manifest(ROOT, PDF_PATH)
    for primitive_name in sorted(PRIMITIVES):
        primitive_dir = ROOT / primitive_name
        primitive_dir.mkdir(parents=True, exist_ok=True)
        script_path = primitive_dir / f"{primitive_name}.py"
        script_path.write_text(wrapper_script_text(primitive_name), encoding="utf-8")
        run_named_primitive(primitive_name, primitive_dir, argv=[])
    write_readme()


if __name__ == "__main__":
    main()
