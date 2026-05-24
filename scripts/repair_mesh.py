import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.mesh_repair import repair_mesh_file


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run safe baseline mesh repair for STL/OBJ files.")
    parser.add_argument("--input", required=True, type=Path, help="Input mesh path (.stl or .obj).")
    parser.add_argument("--output", required=True, type=Path, help="Output repaired mesh path.")
    parser.add_argument(
        "--skip-fill-holes",
        action="store_true",
        help="Skip hole-filling step (normal fix and face cleanup still run).",
    )
    parser.add_argument("--summary-out", type=Path, help="Write repair summary JSON to this path.")
    args = parser.parse_args(argv)

    summary = repair_mesh_file(
        input_path=args.input,
        output_path=args.output,
        try_fill_holes=not args.skip_fill_holes,
    )
    if args.summary_out is not None:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
