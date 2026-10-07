#!/usr/bin/env python3
"""
Synthetic Test Case Generator for Project Chameleon.
Generates diverse, realistic digital marketing target canvases
(skyscraper, vertical story, landscape banner, billboard, square)
from base sample designs to thoroughly stress-test the layout solver.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

# Standard real-world marketing formats
MARKETING_FORMATS = [
    {
        "name": "instagram_story",
        "description": "Tall vertical 9:16 mobile story",
        "width": 1080,
        "height": 1920,
    },
    {
        "name": "facebook_landscape",
        "description": "Standard landscape social post (1.91:1)",
        "width": 1200,
        "height": 630,
    },
    {
        "name": "wide_billboard",
        "description": "Ultra-wide top banner (3.88:1)",
        "width": 970,
        "height": 250,
    },
    {
        "name": "skyscraper",
        "description": "Ultra-tall side banner (1:3.75)",
        "width": 160,
        "height": 600,
    },
    {
        "name": "medium_rectangle",
        "description": "Standard IAB medium rectangle (1.2:1)",
        "width": 300,
        "height": 250,
    },
    {
        "name": "compact_square",
        "description": "Scaled-down compact square (1:1)",
        "width": 600,
        "height": 600,
    },
]


def generate_cases(input_dir: Path, output_dir: Path) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []

    sample_files = sorted(input_dir.glob("chameleon_sample_level*.json"))
    if not sample_files:
        print(f"No sample files found in {input_dir}")
        return []

    for sample_path in sample_files:
        data = json.loads(sample_path.read_text())
        source = data.get("source", {})
        base_name = sample_path.stem

        for fmt in MARKETING_FORMATS:
            case_id = f"{base_name}_{fmt['name']}"
            synthetic_task = {
                "task_id": case_id,
                "notes": f"Synthetic test case: {fmt['description']} ({fmt['width']}x{fmt['height']}) derived from {sample_path.name}",
                "source": source,
                "target_canvas": {
                    "width": fmt["width"],
                    "height": fmt["height"],
                },
            }

            dest_path = output_dir / f"{case_id}.json"
            dest_path.write_text(json.dumps(synthetic_task, indent=2))
            generated_files.append(dest_path)

    print(f"Generated {len(generated_files)} synthetic test cases in {output_dir}")
    return generated_files


def main():
    repo_root = Path(__file__).resolve().parent.parent
    input_dir = repo_root / "chameleon" / "input"
    output_dir = repo_root / "chameleon" / "input_synthetic"

    generate_cases(input_dir, output_dir)


if __name__ == "__main__":
    main()
