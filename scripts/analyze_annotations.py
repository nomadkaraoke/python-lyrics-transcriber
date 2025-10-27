#!/usr/bin/env python3
"""Analyze correction annotations to generate insights and reports.

This script analyzes all collected correction annotations from the human
feedback loop and generates a comprehensive Markdown report.

Usage:
    python scripts/analyze_annotations.py [--cache-dir cache]
"""

import argparse
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any

# Add parent directory to path to import lyrics_transcriber modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from lyrics_transcriber.correction.feedback.store import FeedbackStore
from lyrics_transcriber.correction.feedback.schemas import CorrectionAnnotation


def analyze_annotations(store: FeedbackStore) -> Dict[str, Any]:
    """Analyze all annotations and generate statistics.
    
    Args:
        store: FeedbackStore instance
    
    Returns:
        Dictionary with analysis results
    """
    annotations = store.get_all_annotations()
    
    if not annotations:
        return {
            "total": 0,
            "message": "No annotations found"
        }
    
    # Basic counts
    total = len(annotations)
    unique_songs = len(set(a.audio_hash for a in annotations))
    unique_artists = len(set(a.artist for a in annotations))
    
    # By category
    by_type = Counter(a.annotation_type for a in annotations)
    by_action = Counter(a.action_taken for a in annotations)
    
    # Confidence analysis
    confidences = [a.confidence for a in annotations]
    avg_confidence = sum(confidences) / len(confidences)
    high_confidence = len([c for c in confidences if c >= 4])
    
    # Agentic AI performance
    with_agentic = [a for a in annotations if a.agentic_proposal is not None]
    if with_agentic:
        agentic_agreement_rate = sum(1 for a in with_agentic if a.agentic_agreed) / len(with_agentic)
        
        # Agreement by category
        agreement_by_category = {}
        for category in set(a.annotation_type for a in with_agentic):
            cat_annotations = [a for a in with_agentic if a.annotation_type == category]
            if cat_annotations:
                agreement = sum(1 for a in cat_annotations if a.agentic_agreed) / len(cat_annotations)
                agreement_by_category[category] = {
                    "count": len(cat_annotations),
                    "agreement_rate": agreement
                }
    else:
        agentic_agreement_rate = 0.0
        agreement_by_category = {}
    
    # Common error patterns
    error_patterns = defaultdict(list)
    for a in annotations:
        if a.action_taken != "NO_ACTION" and a.original_text != a.corrected_text:
            pattern = f"{a.original_text} → {a.corrected_text}"
            error_patterns[pattern].append(a)
    
    most_common_errors = [
        {
            "pattern": pattern,
            "count": len(anns),
            "type": anns[0].annotation_type,
            "avg_confidence": sum(a.confidence for a in anns) / len(anns),
            "examples": [
                {
                    "artist": a.artist,
                    "title": a.title,
                    "reasoning": a.reasoning
                } for a in anns[:3]  # Show up to 3 examples
            ]
        }
        for pattern, anns in sorted(error_patterns.items(), key=lambda x: len(x[1]), reverse=True)[:20]
    ]
    
    # Frequently misheard words
    misheard_words = defaultdict(lambda: defaultdict(int))
    for a in annotations:
        if a.annotation_type == "SOUND_ALIKE" and a.original_text and a.corrected_text:
            orig_words = a.original_text.lower().split()
            corr_words = a.corrected_text.lower().split()
            # Simple word-level comparison
            for orig in orig_words:
                for corr in corr_words:
                    if orig != corr and len(orig) > 2 and len(corr) > 2:
                        misheard_words[orig][corr] += 1
    
    top_misheard = [
        {
            "original": orig,
            "commonly_corrected_to": dict(sorted(corrections.items(), key=lambda x: x[1], reverse=True))
        }
        for orig, corrections in sorted(misheard_words.items(), key=lambda x: sum(x[1].values()), reverse=True)[:15]
    ]
    
    # Reference lyrics quality
    ref_source_usage = Counter()
    for a in annotations:
        for source in a.reference_sources_consulted:
            ref_source_usage[source] += 1
    
    # Time analysis
    if annotations:
        first_annotation = min(annotations, key=lambda a: a.timestamp)
        last_annotation = max(annotations, key=lambda a: a.timestamp)
        date_range = (last_annotation.timestamp - first_annotation.timestamp).days
    else:
        date_range = 0
    
    return {
        "total": total,
        "unique_songs": unique_songs,
        "unique_artists": unique_artists,
        "date_range_days": date_range,
        "by_type": dict(by_type),
        "by_action": dict(by_action),
        "avg_confidence": avg_confidence,
        "high_confidence_count": high_confidence,
        "high_confidence_percentage": (high_confidence / total) * 100,
        "agentic_coverage": len(with_agentic),
        "agentic_agreement_rate": agentic_agreement_rate,
        "agreement_by_category": agreement_by_category,
        "most_common_errors": most_common_errors,
        "top_misheard_words": top_misheard,
        "reference_source_usage": dict(ref_source_usage)
    }


def generate_markdown_report(analysis: Dict[str, Any]) -> str:
    """Generate a Markdown report from analysis results.
    
    Args:
        analysis: Analysis results dictionary
    
    Returns:
        Markdown formatted report
    """
    if analysis.get("total", 0) == 0:
        return f"# Correction Analysis Report\n\n{analysis.get('message', 'No data available')}\n"
    
    report = []
    report.append("# Correction Analysis Report")
    report.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Overview
    report.append("## Overview\n")
    report.append(f"- **Total Annotations:** {analysis['total']}")
    report.append(f"- **Unique Songs:** {analysis['unique_songs']}")
    report.append(f"- **Unique Artists:** {analysis['unique_artists']}")
    report.append(f"- **Date Range:** {analysis['date_range_days']} days")
    report.append(f"- **Average Confidence:** {analysis['avg_confidence']:.2f}/5.0")
    report.append(f"- **High Confidence (4-5):** {analysis['high_confidence_count']} ({analysis['high_confidence_percentage']:.1f}%)\n")
    
    # Annotation breakdown
    report.append("## Annotations by Type\n")
    for type_name, count in sorted(analysis['by_type'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / analysis['total']) * 100
        report.append(f"- **{type_name}:** {count} ({percentage:.1f}%)")
    report.append("")
    
    report.append("## Actions Taken\n")
    for action, count in sorted(analysis['by_action'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / analysis['total']) * 100
        report.append(f"- **{action}:** {count} ({percentage:.1f}%)")
    report.append("")
    
    # Agentic AI performance
    if analysis['agentic_coverage'] > 0:
        report.append("## Agentic AI Performance\n")
        report.append(f"- **Coverage:** {analysis['agentic_coverage']} annotations with AI proposals ({(analysis['agentic_coverage'] / analysis['total'] * 100):.1f}%)")
        report.append(f"- **Overall Agreement Rate:** {analysis['agentic_agreement_rate']:.1%}\n")
        
        if analysis['agreement_by_category']:
            report.append("### Agreement by Category\n")
            for category, stats in sorted(analysis['agreement_by_category'].items(), key=lambda x: x[1]['count'], reverse=True):
                report.append(f"- **{category}:** {stats['agreement_rate']:.1%} ({stats['count']} samples)")
            report.append("")
    
    # Common error patterns
    if analysis['most_common_errors']:
        report.append("## Most Common Error Patterns\n")
        for i, error in enumerate(analysis['most_common_errors'][:10], 1):
            report.append(f"### {i}. `{error['pattern']}` ({error['count']} occurrences)")
            report.append(f"- **Type:** {error['type']}")
            report.append(f"- **Average Confidence:** {error['avg_confidence']:.2f}/5.0")
            if error['examples']:
                report.append("- **Examples:**")
                for ex in error['examples']:
                    report.append(f"  - {ex['artist']} - {ex['title']}: {ex['reasoning'][:100]}...")
            report.append("")
    
    # Top misheard words
    if analysis['top_misheard_words']:
        report.append("## Frequently Misheard Words (Sound-Alike Errors)\n")
        for item in analysis['top_misheard_words'][:10]:
            report.append(f"### `{item['original']}`")
            report.append("Commonly corrected to:")
            for corrected, count in list(item['commonly_corrected_to'].items())[:5]:
                report.append(f"- `{corrected}` ({count}x)")
            report.append("")
    
    # Reference source usage
    if analysis['reference_source_usage']:
        report.append("## Reference Source Usage\n")
        total_refs = sum(analysis['reference_source_usage'].values())
        for source, count in sorted(analysis['reference_source_usage'].items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_refs) * 100
            report.append(f"- **{source}:** {count} ({percentage:.1f}%)")
        report.append("")
    
    # Recommendations
    report.append("## Recommendations\n")
    
    # Check if any category has low agreement
    if analysis.get('agreement_by_category'):
        low_agreement = [
            (cat, stats) for cat, stats in analysis['agreement_by_category'].items()
            if stats['agreement_rate'] < 0.5 and stats['count'] >= 5
        ]
        if low_agreement:
            report.append("### Categories Needing Improvement\n")
            for cat, stats in low_agreement:
                report.append(f"- **{cat}:** Only {stats['agreement_rate']:.1%} agreement ({stats['count']} samples)")
                report.append(f"  - Action: Review and improve few-shot examples for this category")
            report.append("")
    
    # Check if high-confidence data available for training
    if analysis['high_confidence_count'] >= 20:
        report.append("### Training Data Available\n")
        report.append(f"- You have {analysis['high_confidence_count']} high-confidence annotations")
        report.append("- Recommendation: Run `scripts/generate_few_shot_examples.py` to update classifier prompts")
        report.append("- Future: Consider fine-tuning a custom model with this data\n")
    
    return "\n".join(report)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze correction annotations")
    parser.add_argument(
        "--cache-dir",
        default="cache",
        help="Directory containing correction_annotations.jsonl"
    )
    parser.add_argument(
        "--output",
        default="CORRECTION_ANALYSIS.md",
        help="Output file for the report"
    )
    
    args = parser.parse_args()
    
    # Initialize store
    store = FeedbackStore(storage_dir=args.cache_dir)
    
    print(f"Loading annotations from: {store.annotations_file}")
    
    # Run analysis
    analysis = analyze_annotations(store)
    
    if analysis.get("total", 0) == 0:
        print("No annotations found.")
        print(f"Annotations will be stored in: {store.annotations_file}")
        print("Make corrections in the UI to start collecting data.")
        return
    
    print(f"Analyzed {analysis['total']} annotations from {analysis['unique_songs']} songs")
    
    # Generate report
    report = generate_markdown_report(analysis)
    
    # Write to file
    output_path = Path(args.output)
    output_path.write_text(report, encoding='utf-8')
    
    print(f"\n✅ Report generated: {output_path}")
    print(f"\nKey Findings:")
    print(f"  - Most common type: {max(analysis['by_type'].items(), key=lambda x: x[1])[0]}")
    print(f"  - Most common action: {max(analysis['by_action'].items(), key=lambda x: x[1])[0]}")
    if analysis.get('agentic_agreement_rate'):
        print(f"  - AI agreement rate: {analysis['agentic_agreement_rate']:.1%}")


if __name__ == "__main__":
    main()

