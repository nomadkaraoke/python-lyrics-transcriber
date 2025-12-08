#!/usr/bin/env python3
"""Manage LLM response cache.

This script helps you manage the LLM response cache, which stores
responses to avoid redundant API calls during development.

Usage:
    python scripts/manage_llm_cache.py stats
    python scripts/manage_llm_cache.py clear
    python scripts/manage_llm_cache.py prune --days 30
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lyrics_transcriber.correction.agentic.providers.response_cache import ResponseCache


def show_stats(cache: ResponseCache):
    """Show cache statistics."""
    stats = cache.get_stats()
    
    print(f"\n📊 LLM Response Cache Statistics")
    print(f"=" * 50)
    print(f"Cache file: {stats['cache_file']}")
    print(f"Status: {'Enabled' if stats['enabled'] else 'Disabled'}")
    print(f"Total entries: {stats['total_entries']}")
    
    if stats['total_entries'] > 0:
        print(f"\nBy model:")
        for model, count in stats['by_model'].items():
            print(f"  - {model}: {count} responses")
        
        if stats.get('oldest') and stats.get('newest'):
            print(f"\nDate range:")
            print(f"  - Oldest: {stats['oldest']}")
            print(f"  - Newest: {stats['newest']}")
    else:
        print("\n(Cache is empty)")
    
    print()


def clear_cache(cache: ResponseCache):
    """Clear all cache entries."""
    count = cache.clear()
    print(f"\n✅ Cleared {count} cached responses\n")


def prune_cache(cache: ResponseCache, days: int):
    """Prune old cache entries."""
    count = cache.prune_old_entries(days)
    print(f"\n✅ Pruned {count} entries older than {days} days\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage LLM response cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show cache statistics
  python scripts/manage_llm_cache.py stats
  
  # Clear entire cache
  python scripts/manage_llm_cache.py clear
  
  # Remove entries older than 30 days
  python scripts/manage_llm_cache.py prune --days 30
  
  # Use custom cache directory
  python scripts/manage_llm_cache.py stats --cache-dir /path/to/cache
"""
    )
    
    parser.add_argument(
        "command",
        choices=["stats", "clear", "prune"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--cache-dir",
        default=os.path.join(os.path.expanduser("~"), "lyrics-transcriber-cache"),
        help="Cache directory (default: ~/lyrics-transcriber-cache)"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Days threshold for prune command (default: 30)"
    )
    
    args = parser.parse_args()
    
    # Initialize cache
    cache = ResponseCache(storage_dir=args.cache_dir)
    
    # Execute command
    if args.command == "stats":
        show_stats(cache)
    elif args.command == "clear":
        clear_cache(cache)
    elif args.command == "prune":
        prune_cache(cache, args.days)


if __name__ == "__main__":
    main()

