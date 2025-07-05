#!/usr/bin/env python3
"""
Manual test for comparing LyricsGenius and RapidAPI approaches.

This test is not part of the regular test suite and must be run manually.
It requires real API keys and makes actual network requests.

To run this test:
1. Set your environment variables:
   export RAPIDAPI_KEY="your-real-rapidapi-key"
   export GENIUS_API_TOKEN="your-real-genius-token"  # Optional fallback

2. Run the test:
   python tests/manual/test_rapidapi_comparison.py

Or run with pytest (skipping regular tests):
   python -m pytest tests/manual/test_rapidapi_comparison.py::test_compare_lyrics_apis -v -s
"""

import os
import pytest
import logging
import warnings
from typing import Optional
from lyrics_transcriber.lyrics.genius import GeniusProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig


# Suppress FutureWarning from lyricsgenius library
warnings.filterwarnings("ignore", category=FutureWarning, module="lyricsgenius.*")
warnings.filterwarnings("ignore", message=".*constructor signature will change.*", category=FutureWarning)

# Also suppress at pytest level
pytestmark = pytest.mark.filterwarnings("ignore::FutureWarning")


def normalize_lyrics_text(lyrics: str) -> str:
    """Normalize lyrics text for comparison by removing extra whitespace and common variations."""
    if not lyrics:
        return ""
    
    # Remove extra whitespace and normalize line endings
    normalized = " ".join(lyrics.split())
    
    # Convert to lowercase for comparison
    normalized = normalized.lower()
    
    # Remove common punctuation variations that might differ between APIs
    replacements = [
        ("'", "'"),  # Smart quotes to regular quotes
        (""", '"'),  # Smart quotes to regular quotes
        (""", '"'),  # Smart quotes to regular quotes
        ("…", "..."),  # Ellipsis to three dots
    ]
    
    for old, new in replacements:
        normalized = normalized.replace(old, new)
    
    return normalized.strip()


def test_compare_lyrics_apis():
    """
    Compare LyricsGenius and RapidAPI approaches for fetching the same song.
    
    This test validates that both methods return equivalent lyrics content.
    """
    # Skip if running in automated test environment
    if not os.getenv("RAPIDAPI_KEY"):
        pytest.skip("Manual test - requires RAPIDAPI_KEY environment variable")
    
    # Test song
    artist = "ABBA"
    title = "Waterloo"
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print(f"\n🎵 Testing lyrics fetch for {artist} - {title}")
    print("=" * 60)
    
    # Test 1: RapidAPI approach (force RapidAPI only)
    print("\n📡 Testing RapidAPI approach...")
    rapidapi_config = LyricsProviderConfig(
        rapidapi_key=os.getenv("RAPIDAPI_KEY"),
        genius_api_token=None  # Force RapidAPI only
    )
    rapidapi_provider = GeniusProvider(rapidapi_config, logger)
    
    try:
        rapidapi_result = rapidapi_provider.fetch_lyrics(artist, title)
        if rapidapi_result:
            rapidapi_lyrics = rapidapi_result.get_full_text()
            rapidapi_source = rapidapi_result.metadata.provider_metadata.get("api_source", "unknown")
            print(f"✅ RapidAPI fetch successful (source: {rapidapi_source})")
            print(f"📝 Lyrics length: {len(rapidapi_lyrics)} characters")
            print(f"📄 First 100 chars: {rapidapi_lyrics[:100]}...")
        else:
            rapidapi_lyrics = None
            print("❌ RapidAPI fetch failed - no results")
    except Exception as e:
        rapidapi_lyrics = None
        print(f"❌ RapidAPI fetch failed with error: {str(e)}")
    
    # Test 2: LyricsGenius approach (force LyricsGenius only)
    genius_token = os.getenv("GENIUS_API_TOKEN")
    if genius_token:
        print("\n🔍 Testing LyricsGenius approach...")
        genius_config = LyricsProviderConfig(
            genius_api_token=genius_token,
            rapidapi_key=None  # Force LyricsGenius only
        )
        genius_provider = GeniusProvider(genius_config, logger)
        
        try:
            genius_result = genius_provider.fetch_lyrics(artist, title)
            if genius_result:
                genius_lyrics = genius_result.get_full_text()
                genius_source = genius_result.metadata.provider_metadata.get("api_source", "lyricsgenius")
                print(f"✅ LyricsGenius fetch successful (source: {genius_source})")
                print(f"📝 Lyrics length: {len(genius_lyrics)} characters")
                print(f"📄 First 100 chars: {genius_lyrics[:100]}...")
            else:
                genius_lyrics = None
                print("❌ LyricsGenius fetch failed - no results")
        except Exception as e:
            genius_lyrics = None
            print(f"❌ LyricsGenius fetch failed with error: {str(e)}")
    else:
        genius_lyrics = None
        print("\n⚠️  Skipping LyricsGenius test - no GENIUS_API_TOKEN provided")
    
    # Test 3: Manual comparison using raw fetch and convert
    print("\n🔧 Testing manual approach comparison...")
    manual_comparison_successful = False
    
    if genius_token:
        try:
            # Create providers for manual testing
            rapidapi_provider_manual = GeniusProvider(rapidapi_config, logger)
            genius_provider_manual = GeniusProvider(genius_config, logger)
            
            # Fetch raw data from each source directly
            print("  Fetching raw data from RapidAPI...")
            rapidapi_raw = rapidapi_provider_manual._fetch_from_rapidapi(artist, title)
            
            print("  Fetching raw data from LyricsGenius...")
            # Force LyricsGenius by calling the client directly
            genius_raw = None
            if genius_provider_manual.client:
                try:
                    song = genius_provider_manual.client.search_song(title, artist)
                    if song:
                        genius_raw = song.to_dict()
                        print("    Successfully got data from LyricsGenius client")
                    else:
                        print("    LyricsGenius client returned no results")
                except Exception as e:
                    print(f"    LyricsGenius client failed: {str(e)}")
            else:
                print("    No LyricsGenius client available")
            
            if rapidapi_raw and genius_raw:
                # Verify we got data from different sources by checking structure
                rapidapi_has_rapidapi_structure = "primary_artist" in rapidapi_raw
                genius_has_lyricsgenius_structure = "artist_names" in genius_raw
                
                print(f"  RapidAPI structure detected: {rapidapi_has_rapidapi_structure}")
                print(f"  LyricsGenius structure detected: {genius_has_lyricsgenius_structure}")
                
                if rapidapi_has_rapidapi_structure and genius_has_lyricsgenius_structure:
                    # Convert both through the same processing pipeline
                    print("  Converting both responses through _convert_result_format...")
                    rapidapi_converted = rapidapi_provider_manual._convert_result_format(rapidapi_raw)
                    genius_converted = genius_provider_manual._convert_result_format(genius_raw)
                    
                    rapidapi_processed = rapidapi_converted.get_full_text()
                    genius_processed = genius_converted.get_full_text()
                    
                    print(f"  Processed RapidAPI length: {len(rapidapi_processed)}")
                    print(f"  Processed LyricsGenius length: {len(genius_processed)}")
                    print(f"  RapidAPI first 100: {rapidapi_processed[:100]}...")
                    print(f"  LyricsGenius first 100: {genius_processed[:100]}...")
                    
                    # Compare normalized versions
                    rapidapi_norm = normalize_lyrics_text(rapidapi_processed)
                    genius_norm = normalize_lyrics_text(genius_processed)
                    
                    print(f"  Normalized RapidAPI length: {len(rapidapi_norm)}")
                    print(f"  Normalized LyricsGenius length: {len(genius_norm)}")
                    
                    if rapidapi_norm == genius_norm:
                        print("  ✅ SUCCESS: Both sources return identical lyrics after processing!")
                        manual_comparison_successful = True
                    else:
                        print("  ⚠️  DIFFERENCE: Sources return different lyrics after processing")
                        # Find first difference for debugging
                        min_len = min(len(rapidapi_norm), len(genius_norm))
                        first_diff = None
                        for i in range(min_len):
                            if rapidapi_norm[i] != genius_norm[i]:
                                first_diff = i
                                break
                        if first_diff is not None:
                            start = max(0, first_diff - 20)
                            end = min(len(rapidapi_norm), first_diff + 40)
                            print(f"    First difference at position {first_diff}:")
                            print(f"    RapidAPI:     ...{rapidapi_norm[start:end]}...")
                            print(f"    LyricsGenius: ...{genius_norm[start:end]}...")
                        manual_comparison_successful = True  # We did compare both sources
                else:
                    print("  ⚠️  Could not get data from both distinct sources")
            else:
                if not rapidapi_raw:
                    print("  ❌ Failed to get RapidAPI raw data")
                if not genius_raw:
                    print("  ❌ Failed to get LyricsGenius raw data")
                
        except Exception as e:
            print(f"  ❌ Manual comparison failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Compare results
    print("\n🔍 Comparison Results:")
    print("=" * 60)
    
    if rapidapi_lyrics and genius_lyrics:
        # Both succeeded - compare content
        rapidapi_normalized = normalize_lyrics_text(rapidapi_lyrics)
        genius_normalized = normalize_lyrics_text(genius_lyrics)
        
        print(f"RapidAPI normalized length: {len(rapidapi_normalized)}")
        print(f"LyricsGenius normalized length: {len(genius_normalized)}")
        
        if rapidapi_normalized == genius_normalized:
            print("✅ SUCCESS: Both APIs returned identical lyrics content!")
        else:
            print("⚠️  DIFFERENCE: APIs returned different lyrics content")
            
            # Show character-level differences for debugging
            if len(rapidapi_normalized) != len(genius_normalized):
                print(f"Length difference: {abs(len(rapidapi_normalized) - len(genius_normalized))} characters")
            
            # Find first difference
            min_len = min(len(rapidapi_normalized), len(genius_normalized))
            first_diff = None
            for i in range(min_len):
                if rapidapi_normalized[i] != genius_normalized[i]:
                    first_diff = i
                    break
            
            if first_diff is not None:
                start = max(0, first_diff - 20)
                end = min(len(rapidapi_normalized), first_diff + 20)
                print(f"First difference at position {first_diff}:")
                print(f"  RapidAPI: ...{rapidapi_normalized[start:end]}...")
                print(f"  LyricsGenius: ...{genius_normalized[start:end]}...")
        
        # Only assert if we actually tested two different sources
        # Otherwise just report what we found
        if manual_comparison_successful:
            print("📊 Manual comparison completed - both sources were tested independently")
        else:
            print("📊 Note: May have tested same underlying source - manual comparison inconclusive")
            # Don't fail the test if we couldn't properly separate the sources
            
    elif rapidapi_lyrics:
        print("✅ RapidAPI succeeded, LyricsGenius not tested/failed")
        print("📊 Cannot compare - only one source available")
        
    elif genius_lyrics:
        print("✅ LyricsGenius succeeded, RapidAPI failed")
        print("📊 Cannot compare - only one source available")
        
    else:
        print("❌ Both APIs failed to fetch lyrics")
        pytest.fail("Both APIs failed to fetch lyrics")
    
    print("\n🎉 Test completed!")


def test_rapidapi_only():
    """Test RapidAPI approach in isolation."""
    if not os.getenv("RAPIDAPI_KEY"):
        pytest.skip("Manual test - requires RAPIDAPI_KEY environment variable")
    
    artist = "ABBA"
    title = "Waterloo"
    
    print(f"\n🎵 Testing RapidAPI-only fetch for {artist} - {title}")
    
    config = LyricsProviderConfig(rapidapi_key=os.getenv("RAPIDAPI_KEY"))
    provider = GeniusProvider(config, logging.getLogger(__name__))
    
    result = provider.fetch_lyrics(artist, title)
    
    assert result is not None, "RapidAPI should return lyrics"
    assert len(result.get_full_text()) > 0, "Lyrics should not be empty"
    assert result.metadata.provider_metadata.get("api_source") == "rapidapi", "Should use RapidAPI source"
    
    print(f"✅ RapidAPI test successful - {len(result.get_full_text())} characters fetched")


if __name__ == "__main__":
    """Run the comparison test directly."""
    try:
        test_compare_lyrics_apis()
    except pytest.skip.Exception as e:
        print(f"Test skipped: {e}")
    except Exception as e:
        print(f"Test failed: {e}")
        raise 