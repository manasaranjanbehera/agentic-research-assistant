"""CLI entry point: generate a researched, reviewed report on a topic.

Usage:
    uv run python -m src.main "AWS Bedrock agentic AI patterns"

Requires AWS credentials with Bedrock model access configured in your
environment (see README.md for setup).
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from .agents import ResearchPipeline


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic", help="Topic to research and report on")
    parser.add_argument("--max-revisions", type=int, default=2)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    pipeline = ResearchPipeline()
    result = pipeline.run(args.topic, max_revisions=args.max_revisions)

    print(f"\n=== Final Report: {result.topic} ===\n")
    print(result.final_report)
    print(f"\n(revision rounds used: {result.revision_rounds})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
