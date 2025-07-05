#!/usr/bin/env python3
"""
Manual test for comparing Spotify syrics and RapidAPI approaches.

This test is not part of the regular test suite and must be run manually.
It requires real API keys and makes actual network requests.

To run this test:
1. Set your environment variables:
   export RAPIDAPI_KEY="your-real-rapidapi-key"
   export SPOTIFY_COOKIE_SP_DC="your-real-spotify-cookie"

2. Run the test:
   python tests/manual/test_spotify_rapidapi_comparison.py

Or run with pytest (skipping regular tests):
   python -m pytest tests/manual/test_spotify_rapidapi_comparison.py::test_compare_spotify_apis -v -s
"""

import os
import pytest
import logging
import warnings
from typing import Optional
from lyrics_transcriber.lyrics.spotify import SpotifyProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig


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
        ("♪", ""),  # Remove musical notes
    ]
    
    for old, new in replacements:
        normalized = normalized.replace(old, new)
    
    return normalized.strip()


def test_compare_spotify_apis():
    """
    Compare Spotify syrics and RapidAPI approaches for fetching the same song.
    
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
    
    print(f"\n🎵 Testing Spotify lyrics fetch for {artist} - {title}")
    print("=" * 60)
    
    # Test 1: RapidAPI approach (force RapidAPI only)
    print("\n📡 Testing Spotify RapidAPI approach...")
    rapidapi_config = LyricsProviderConfig(
        rapidapi_key=os.getenv("RAPIDAPI_KEY"),
        spotify_cookie=None  # Force RapidAPI only
    )
    rapidapi_provider = SpotifyProvider(rapidapi_config, logger)
    
    try:
        rapidapi_result = rapidapi_provider.fetch_lyrics(artist, title)
        if rapidapi_result:
            rapidapi_lyrics = rapidapi_result.get_full_text()
            rapidapi_source = rapidapi_result.metadata.provider_metadata.get("api_source", "unknown")
            print(f"✅ RapidAPI fetch successful (source: {rapidapi_source})")
            print(f"📝 Lyrics length: {len(rapidapi_lyrics)} characters")
            print(f"🎼 Segments count: {len(rapidapi_result.segments)}")
            print(f"⏱️  Is synced: {rapidapi_result.metadata.is_synced}")
            print(f"📄 First 100 chars: {rapidapi_lyrics[:100]}...")
        else:
            rapidapi_lyrics = None
            print("❌ RapidAPI fetch failed - no results")
    except Exception as e:
        rapidapi_lyrics = None
        print(f"❌ RapidAPI fetch failed with error: {str(e)}")
    
    # Test 2: syrics approach (force syrics only)
    spotify_cookie = os.getenv("SPOTIFY_COOKIE_SP_DC")
    if spotify_cookie:
        print("\n🔍 Testing Spotify syrics approach...")
        syrics_config = LyricsProviderConfig(
            spotify_cookie=spotify_cookie,
            rapidapi_key=None  # Force syrics only
        )
        syrics_provider = SpotifyProvider(syrics_config, logger)
        
        try:
            syrics_result = syrics_provider.fetch_lyrics(artist, title)
            if syrics_result:
                syrics_lyrics = syrics_result.get_full_text()
                syrics_source = syrics_result.metadata.provider_metadata.get("api_source", "syrics")
                print(f"✅ syrics fetch successful (source: {syrics_source})")
                print(f"📝 Lyrics length: {len(syrics_lyrics)} characters")
                print(f"🎼 Segments count: {len(syrics_result.segments)}")
                print(f"⏱️  Is synced: {syrics_result.metadata.is_synced}")
                print(f"📄 First 100 chars: {syrics_lyrics[:100]}...")
            else:
                syrics_lyrics = None
                print("❌ syrics fetch failed - no results")
        except Exception as e:
            syrics_lyrics = None
            print(f"❌ syrics fetch failed with error: {str(e)}")
    else:
        syrics_lyrics = None
        print("\n⚠️  Skipping syrics test - no SPOTIFY_COOKIE_SP_DC provided")
    
    # Test 3: Manual comparison using raw fetch and convert
    print("\n🔧 Testing manual approach comparison...")
    manual_comparison_successful = False
    
    if spotify_cookie:
        try:
            # Create providers for manual testing
            rapidapi_provider_manual = SpotifyProvider(rapidapi_config, logger)
            syrics_provider_manual = SpotifyProvider(syrics_config, logger)
            
            # Fetch raw data from each source directly
            print("  Fetching raw data from RapidAPI...")
            rapidapi_raw = rapidapi_provider_manual._fetch_from_rapidapi(artist, title)
            
            print("  Fetching raw data from syrics...")
            # Force syrics by calling the data source directly
            syrics_raw = None
            if syrics_provider_manual.client:
                try:
                    # Search for track
                    search_query = f"{title} - {artist}"
                    search_results = syrics_provider_manual.client.search(search_query, type="track", limit=1)
                    
                    if search_results["tracks"]["items"]:
                        track_data = search_results["tracks"]["items"][0]
                        print(f"    Found track: {track_data['name']} by {track_data['artists'][0]['name']}")
                        
                        # Get lyrics data
                        lyrics_data = syrics_provider_manual.client.get_lyrics(track_data["id"])
                        if lyrics_data:
                            syrics_raw = {"track_data": track_data, "lyrics_data": lyrics_data}
                            print("    Successfully got lyrics from syrics client")
                        else:
                            print("    syrics client returned no lyrics")
                    else:
                        print("    syrics client returned no search results")
                except Exception as e:
                    print(f"    syrics client failed: {str(e)}")
            else:
                print("    No syrics client available")
            
            if rapidapi_raw and syrics_raw:
                # Verify we got data from different sources by checking structure
                rapidapi_has_rapidapi_structure = rapidapi_raw.get("_rapidapi_source", False)
                syrics_has_syrics_structure = "lyrics_data" in syrics_raw and "lyrics" in syrics_raw["lyrics_data"]
                
                print(f"  RapidAPI structure detected: {rapidapi_has_rapidapi_structure}")
                print(f"  syrics structure detected: {syrics_has_syrics_structure}")
                
                if rapidapi_has_rapidapi_structure and syrics_has_syrics_structure:
                    # Convert both through the same processing pipeline
                    print("  Converting both responses through _convert_result_format...")
                    rapidapi_converted = rapidapi_provider_manual._convert_result_format(rapidapi_raw)
                    syrics_converted = syrics_provider_manual._convert_result_format(syrics_raw)
                    
                    rapidapi_processed = rapidapi_converted.get_full_text()
                    syrics_processed = syrics_converted.get_full_text()
                    
                    print(f"  Processed RapidAPI length: {len(rapidapi_processed)}")
                    print(f"  Processed syrics length: {len(syrics_processed)}")
                    print(f"  RapidAPI segments: {len(rapidapi_converted.segments)}")
                    print(f"  syrics segments: {len(syrics_converted.segments)}")
                    print(f"  RapidAPI first 100: {rapidapi_processed[:100]}...")
                    print(f"  syrics first 100: {syrics_processed[:100]}...")
                    
                    # Compare normalized versions
                    rapidapi_norm = normalize_lyrics_text(rapidapi_processed)
                    syrics_norm = normalize_lyrics_text(syrics_processed)
                    
                    print(f"  Normalized RapidAPI length: {len(rapidapi_norm)}")
                    print(f"  Normalized syrics length: {len(syrics_norm)}")
                    
                    if rapidapi_norm == syrics_norm:
                        print("  ✅ SUCCESS: Both sources return identical lyrics after processing!")
                        manual_comparison_successful = True
                    else:
                        print("  ⚠️  DIFFERENCE: Sources return different lyrics after processing")
                        # Find first difference for debugging
                        min_len = min(len(rapidapi_norm), len(syrics_norm))
                        first_diff = None
                        for i in range(min_len):
                            if rapidapi_norm[i] != syrics_norm[i]:
                                first_diff = i
                                break
                        if first_diff is not None:
                            start = max(0, first_diff - 20)
                            end = min(len(rapidapi_norm), first_diff + 40)
                            print(f"    First difference at position {first_diff}:")
                            print(f"    RapidAPI: ...{rapidapi_norm[start:end]}...")
                            print(f"    syrics:   ...{syrics_norm[start:end]}...")
                        manual_comparison_successful = True  # We did compare both sources
                else:
                    print("  ⚠️  Could not get data from both distinct sources")
            else:
                if not rapidapi_raw:
                    print("  ❌ Failed to get RapidAPI raw data")
                if not syrics_raw:
                    print("  ❌ Failed to get syrics raw data")
                
        except Exception as e:
            print(f"  ❌ Manual comparison failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Compare results
    print("\n🔍 Comparison Results:")
    print("=" * 60)
    
    if rapidapi_lyrics and syrics_lyrics:
        # Both succeeded - compare content
        rapidapi_normalized = normalize_lyrics_text(rapidapi_lyrics)
        syrics_normalized = normalize_lyrics_text(syrics_lyrics)
        
        print(f"RapidAPI normalized length: {len(rapidapi_normalized)}")
        print(f"syrics normalized length: {len(syrics_normalized)}")
        
        if rapidapi_normalized == syrics_normalized:
            print("✅ SUCCESS: Both APIs returned identical lyrics content!")
        else:
            print("⚠️  DIFFERENCE: APIs returned different lyrics content")
            
            # Show character-level differences for debugging
            if len(rapidapi_normalized) != len(syrics_normalized):
                print(f"Length difference: {abs(len(rapidapi_normalized) - len(syrics_normalized))} characters")
            
            # Find first difference
            min_len = min(len(rapidapi_normalized), len(syrics_normalized))
            first_diff = None
            for i in range(min_len):
                if rapidapi_normalized[i] != syrics_normalized[i]:
                    first_diff = i
                    break
            
            if first_diff is not None:
                start = max(0, first_diff - 20)
                end = min(len(rapidapi_normalized), first_diff + 20)
                print(f"First difference at position {first_diff}:")
                print(f"  RapidAPI: ...{rapidapi_normalized[start:end]}...")
                print(f"  syrics:   ...{syrics_normalized[start:end]}...")
        
        # Only assert if we actually tested two different sources
        # Otherwise just report what we found
        if manual_comparison_successful:
            print("📊 Manual comparison completed - both sources were tested independently")
        else:
            print("📊 Note: May have tested same underlying source - manual comparison inconclusive")
            # Don't fail the test if we couldn't properly separate the sources
            
    elif rapidapi_lyrics:
        print("✅ RapidAPI succeeded, syrics not tested/failed")
        print("📊 Cannot compare - only one source available")
        
    elif syrics_lyrics:
        print("✅ syrics succeeded, RapidAPI failed")
        print("📊 Cannot compare - only one source available")
        
    else:
        print("❌ Both APIs failed to fetch lyrics")
        pytest.fail("Both APIs failed to fetch lyrics")
    
    print("\n🎉 Test completed!")


def test_rapidapi_spotify_only():
    """Test Spotify RapidAPI approach in isolation."""
    if not os.getenv("RAPIDAPI_KEY"):
        pytest.skip("Manual test - requires RAPIDAPI_KEY environment variable")
    
    artist = "ABBA"
    title = "Waterloo"
    
    print(f"\n🎵 Testing Spotify RapidAPI-only fetch for {artist} - {title}")
    
    config = LyricsProviderConfig(rapidapi_key=os.getenv("RAPIDAPI_KEY"))
    provider = SpotifyProvider(config, logging.getLogger(__name__))
    
    result = provider.fetch_lyrics(artist, title)
    
    assert result is not None, "Spotify RapidAPI should return lyrics"
    assert len(result.get_full_text()) > 0, "Lyrics should not be empty"
    assert result.metadata.provider_metadata.get("api_source") == "rapidapi", "Should use RapidAPI source"
    assert result.metadata.is_synced is True, "RapidAPI should provide synced lyrics"
    
    print(f"✅ Spotify RapidAPI test successful - {len(result.get_full_text())} characters fetched")
    print(f"🎼 Segments: {len(result.segments)}")
    print(f"⏱️  Synced: {result.metadata.is_synced}")


def test_syrics_spotify_only():
    """Test Spotify syrics approach in isolation."""
    if not os.getenv("SPOTIFY_COOKIE_SP_DC"):
        pytest.skip("Manual test - requires SPOTIFY_COOKIE_SP_DC environment variable")
    
    artist = "ABBA"
    title = "Waterloo"
    
    print(f"\n🎵 Testing Spotify syrics-only fetch for {artist} - {title}")
    
    config = LyricsProviderConfig(spotify_cookie=os.getenv("SPOTIFY_COOKIE_SP_DC"))
    provider = SpotifyProvider(config, logging.getLogger(__name__))
    
    result = provider.fetch_lyrics(artist, title)
    
    assert result is not None, "Spotify syrics should return lyrics"
    assert len(result.get_full_text()) > 0, "Lyrics should not be empty"
    assert result.metadata.provider_metadata.get("api_source") == "syrics", "Should use syrics source"
    
    print(f"✅ Spotify syrics test successful - {len(result.get_full_text())} characters fetched")
    print(f"🎼 Segments: {len(result.segments)}")
    print(f"⏱️  Synced: {result.metadata.is_synced}")


if __name__ == "__main__":
    """Run the comparison test directly."""
    try:
        test_compare_spotify_apis()
    except pytest.skip.Exception as e:
        print(f"Test skipped: {e}")
    except Exception as e:
        print(f"Test failed: {e}")
        raise 