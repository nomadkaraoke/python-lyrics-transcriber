#!/usr/bin/env python3
"""Generate few-shot examples from high-confidence annotations.

This script converts collected human annotations into few-shot examples
that can be used to improve the gap classifier's accuracy.

Usage:
    python scripts/generate_few_shot_examples.py [--cache-dir cache] [--min-confidence 4.0]
"""

import argparse
import sys
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lyrics_transcriber.correction.feedback.store import FeedbackStore
from lyrics_transcriber.correction.feedback.schemas import CorrectionAnnotation
import yaml


def select_examples_by_category(
    annotations: List[CorrectionAnnotation],
    min_confidence: float = 4.0,
    max_per_category: int = 5
) -> Dict[str, List[Dict]]:
    """Select best examples for each category.
    
    Args:
        annotations: All annotations
        min_confidence: Minimum confidence score to include
        max_per_category: Maximum examples per category
    
    Returns:
        Dictionary mapping category name to list of examples
    """
    # Filter to high-confidence annotations
    high_confidence = [a for a in annotations if a.confidence >= min_confidence]
    
    # Group by category
    by_category = defaultdict(list)
    for annotation in high_confidence:
        by_category[annotation.annotation_type].append(annotation)
    
    # Convert to few-shot format
    examples_by_category = {}
    
    for category, anns in by_category.items():
        # Sort by confidence and take top N
        sorted_anns = sorted(anns, key=lambda a: a.confidence, reverse=True)[:max_per_category]
        
        examples = []
        for ann in sorted_anns:
            example = {
                "gap_text": ann.original_text,
                "corrected_text": ann.corrected_text,
                "action": ann.action_taken,
                "reasoning": ann.reasoning,
                "confidence": ann.confidence,
                "artist": ann.artist,
                "title": ann.title
            }
            
            # Add reference context if available
            if ann.reference_sources_consulted:
                example["reference_sources"] = ann.reference_sources_consulted
            
            # Add agentic comparison if available
            if ann.agentic_proposal:
                example["agentic_agreed"] = ann.agentic_agreed
                example["agentic_action"] = ann.agentic_proposal.get("action")
            
            examples.append(example)
        
        # Use lowercase category name for YAML consistency
        category_key = category.lower()
        examples_by_category[category_key] = examples
    
    return examples_by_category


def generate_yaml_content(examples_by_category: Dict[str, List[Dict]]) -> str:
    """Generate YAML content with examples.
    
    Args:
        examples_by_category: Examples organized by category
    
    Returns:
        YAML formatted string
    """
    content = {
        "metadata": {
            "generated_at": str(Path(__file__).parent.parent / "cache" / "correction_annotations.jsonl"),
            "total_examples": sum(len(exs) for exs in examples_by_category.values()),
            "categories": list(examples_by_category.keys())
        },
        "examples_by_category": examples_by_category
    }
    
    return yaml.dump(content, default_flow_style=False, allow_unicode=True, width=120, sort_keys=False)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate few-shot examples from annotations")
    parser.add_argument(
        "--cache-dir",
        default="cache",
        help="Directory containing correction_annotations.jsonl"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=4.0,
        help="Minimum confidence score to include (1-5)"
    )
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=5,
        help="Maximum examples per category"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file (default: lyrics_transcriber/correction/agentic/prompts/examples.yaml)"
    )
    
    args = parser.parse_args()
    
    # Initialize store
    store = FeedbackStore(storage_dir=args.cache_dir)
    
    print(f"Loading annotations from: {store.annotations_file}")
    annotations = store.get_all_annotations()
    
    if not annotations:
        print("No annotations found.")
        print(f"Annotations will be stored in: {store.annotations_file}")
        print("Make corrections in the UI to start collecting data.")
        return
    
    print(f"Found {len(annotations)} total annotations")
    
    # Select examples
    examples = select_examples_by_category(
        annotations,
        min_confidence=args.min_confidence,
        max_per_category=args.max_per_category
    )
    
    if not examples:
        print(f"No annotations with confidence >= {args.min_confidence} found.")
        print("Lower --min-confidence or collect more high-quality annotations.")
        return
    
    total_examples = sum(len(exs) for exs in examples.values())
    print(f"\nSelected {total_examples} high-confidence examples across {len(examples)} categories:")
    for category, exs in examples.items():
        print(f"  - {category}: {len(exs)} examples")
    
    # Generate YAML
    yaml_content = generate_yaml_content(examples)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(__file__).parent.parent / "lyrics_transcriber" / "correction" / "agentic" / "prompts" / "examples.yaml"
    
    # Write file
    output_path.write_text(yaml_content, encoding='utf-8')
    
    print(f"\n✅ Few-shot examples generated: {output_path}")
    print(f"\nNext steps:")
    print(f"  1. Review the generated examples in {output_path}")
    print(f"  2. The classifier will automatically load these examples on next run")
    print(f"  3. Monitor improvement in AI agreement rate over time")


if __name__ == "__main__":
    main()

