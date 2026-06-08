"""
Bengaluru Urban Forestry — pipeline orchestrator.

Runs the three analysis stages in dependency order:

    Stage 1  extract_trees    PDFs        -> tree CSVs
    Stage 2  ward_health      ward stats  -> health score + ranking
    Stage 3  pocket_forests   geometry    -> candidate planting sites

Usage:
    python main.py                # run the whole pipeline
    python main.py ward_health    # run a single stage
    python -m src.ward_health     # equivalently, run a stage module directly
"""
import sys

from src import config, extract_trees, ward_health, pocket_forests

STAGES = {
    "extract_trees": extract_trees.run,
    "ward_health": ward_health.run,
    "pocket_forests": pocket_forests.run,
}


def main(argv: list[str]) -> int:
    config.ensure_output_dir()

    if len(argv) > 1:
        stage = argv[1]
        if stage not in STAGES:
            print(f"Unknown stage {stage!r}. Choose from: {', '.join(STAGES)}")
            return 1
        print(f"=== Running single stage: {stage} ===")
        STAGES[stage]()
        return 0

    for name, fn in STAGES.items():
        print(f"\n=== Stage: {name} ===")
        fn()

    print(f"\nPipeline complete. Outputs written to {config.OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
