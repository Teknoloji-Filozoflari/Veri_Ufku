"""Repeatable help, core translation and shared accessibility contract gate."""

import argparse
import json
from pathlib import Path

from veri_ufku.learning.audit import audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(Path(__file__).resolve().parents[1])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        f"PASS: {len(result['articles'])} articles; {len(result['accessible_controls'])} named fields; {result['core_english_messages']} finished core English messages"
    )


if __name__ == "__main__":
    main()
