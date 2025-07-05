#!/usr/bin/env python3
"""
Manual test for Musixmatch lyrics provider using real API.

This test is not part of the regular test suite and must be run manually.
It requires a real RapidAPI key and makes actual network requests.

To run this test:
1. Set your environment variable:
   export RAPIDAPI_KEY="your-real-rapidapi-key"

2. Run the test:
   python tests/manual/test_musixmatch_provider.py

Or run with pytest (skipping regular tests):
   python -m pytest tests/manual/test_musixmatch_provider.py::test_musixmatch_provider -v -s
"""

import os
import pytest
import logging
from typing import Optional
from lyrics_transcriber.lyrics.musixmatch import MusixmatchProvider
from lyrics_transcriber.lyrics.base_lyrics_provider import LyricsProviderConfig
from lyrics_transcriber.types import LyricsData


def test_musixmatch_provider():
    """
    Test Musixmatch provider with real API to validate it returns valid lyrics.
    
    This test validates that the Musixmatch provider correctly:
    1. Makes API requests to the Musixmatch RapidAPI endpoint
    2. Parses the complex nested response structure
    3. Converts the response to standardized LyricsData format
    4. Returns valid lyrics content
    """
    # Skip if running in automated test environment
    if not os.getenv("RAPIDAPI_KEY"):
        pytest.skip("Manual test - requires RAPIDAPI_KEY environment variable")
    
    # Test song - using ABBA Waterloo as it was in the example
    artist = "ABBA"
    title = "Waterloo"
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print(f"\n🎵 Testing Musixmatch provider for {artist} - {title}")
    print("=" * 60)
    
    # Create provider with real API key
    config = LyricsProviderConfig(rapidapi_key=os.getenv("RAPIDAPI_KEY"))
    provider = MusixmatchProvider(config=config, logger=logger)
    
    print(f"✅ Provider initialized with API key: {config.rapidapi_key[:10]}...")
    
    # Test the full workflow
    print("\n📡 Fetching lyrics from Musixmatch...")
    try:
        result = provider.fetch_lyrics(artist, title)
        
        if result:
            print("✅ Lyrics fetch successful!")
            
            # Validate the result structure
            assert isinstance(result, LyricsData), "Result should be LyricsData instance"
            assert result.source == "musixmatch", "Source should be 'musixmatch'"
            assert len(result.segments) > 0, "Should have lyrics segments"
            
            # Get full text
            full_text = result.get_full_text()
            assert len(full_text) > 0, "Lyrics text should not be empty"
            
            print(f"📝 Lyrics length: {len(full_text)} characters")
            print(f"📄 Number of segments: {len(result.segments)}")
            
            # Validate metadata
            metadata = result.metadata
            assert metadata.source == "musixmatch", "Metadata source should be 'musixmatch'"
            assert metadata.track_name, "Track name should not be empty"
            assert metadata.artist_names, "Artist names should not be empty"
            assert metadata.lyrics_provider == "musixmatch", "Lyrics provider should be 'musixmatch'"
            assert metadata.lyrics_provider_id, "Lyrics provider ID should not be empty"
            
            print(f"🎤 Track: {metadata.track_name}")
            print(f"🎨 Artist: {metadata.artist_names}")
            print(f"💿 Album: {metadata.album_name or 'N/A'}")
            print(f"⏱️  Duration: {metadata.duration_ms/1000 if metadata.duration_ms else 'N/A'} seconds")
            print(f"🔞 Explicit: {metadata.explicit}")
            print(f"🌐 Language: {metadata.language or 'N/A'}")
            print(f"🔄 Synced: {metadata.is_synced}")
            print(f"🆔 Provider ID: {metadata.lyrics_provider_id}")
            
            # Validate provider-specific metadata
            provider_metadata = metadata.provider_metadata
            assert provider_metadata.get("api_source") == "rapidapi_musixmatch", "API source should be correct"
            
            print(f"🔢 Musixmatch Track ID: {provider_metadata.get('musixmatch_track_id', 'N/A')}")
            print(f"🔢 Musixmatch Lyrics ID: {provider_metadata.get('musixmatch_lyrics_id', 'N/A')}")
            print(f"⭐ Track Rating: {provider_metadata.get('track_rating', 'N/A')}")
            print(f"❤️  Favourites: {provider_metadata.get('num_favourite', 'N/A')}")
            print(f"🎵 Spotify ID: {provider_metadata.get('spotify_id', 'N/A')}")
            print(f"🏷️  ISRC: {provider_metadata.get('isrc', 'N/A')}")
            
            # Show first few words of lyrics (being careful not to reproduce copyrighted content)
            words = full_text.split()
            if len(words) > 0:
                print(f"🎼 First few words: {' '.join(words[:5])}...")
            
            # Test segments structure
            if result.segments:
                first_segment = result.segments[0]
                assert first_segment.id, "Segment should have ID"
                assert first_segment.text, "Segment should have text"
                assert len(first_segment.words) > 0, "Segment should have words"
                
                # Test word structure
                first_word = first_segment.words[0]
                assert first_word.id, "Word should have ID"
                assert first_word.text, "Word should have text"
                assert first_word.confidence is not None, "Word should have confidence"
                
                print(f"🔤 First segment: {len(first_segment.words)} words")
                print(f"🔤 First word: '{first_word.text}' (confidence: {first_word.confidence})")
            
            print("\n✅ All validation checks passed!")
            
        else:
            print("❌ No lyrics returned from Musixmatch")
            pytest.fail("Musixmatch provider returned no lyrics")
            
    except Exception as e:
        print(f"❌ Error during lyrics fetch: {str(e)}")
        print("\n🔍 Error details:")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Musixmatch provider failed with error: {str(e)}")


def test_musixmatch_provider_no_results():
    """Test Musixmatch provider with a song that likely doesn't exist."""
    if not os.getenv("RAPIDAPI_KEY"):
        pytest.skip("Manual test - requires RAPIDAPI_KEY environment variable")
    
    # Use a very unlikely song name
    artist = "NonExistentArtist12345"
    title = "NonExistentSong98765"
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print(f"\n🔍 Testing Musixmatch provider with non-existent song: {artist} - {title}")
    print("=" * 60)
    
    config = LyricsProviderConfig(rapidapi_key=os.getenv("RAPIDAPI_KEY"))
    provider = MusixmatchProvider(config=config, logger=logger)
    
    try:
        result = provider.fetch_lyrics(artist, title)
        
        if result is None:
            print("✅ Correctly returned None for non-existent song")
        else:
            print(f"⚠️  Unexpectedly found lyrics for non-existent song: {result.get_full_text()[:100]}...")
            
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        pytest.fail(f"Provider should handle non-existent songs gracefully, but got error: {str(e)}")


def test_musixmatch_provider_metadata_validation():
    """Test that provider metadata is correctly populated."""
    if not os.getenv("RAPIDAPI_KEY"):
        pytest.skip("Manual test - requires RAPIDAPI_KEY environment variable")
    
    artist = "ABBA"
    title = "Waterloo"
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    print(f"\n🔍 Testing Musixmatch provider metadata validation for {artist} - {title}")
    print("=" * 60)
    
    config = LyricsProviderConfig(rapidapi_key=os.getenv("RAPIDAPI_KEY"))
    provider = MusixmatchProvider(config=config, logger=logger)
    
    result = provider.fetch_lyrics(artist, title)
    
    if result:
        metadata = result.metadata
        
        # Check required fields
        required_fields = [
            "source", "track_name", "artist_names", "lyrics_provider", 
            "lyrics_provider_id", "is_synced", "provider_metadata"
        ]
        
        for field in required_fields:
            value = getattr(metadata, field, None)
            print(f"✅ {field}: {value}")
            assert value is not None, f"Required field '{field}' should not be None"
        
        # Check provider-specific metadata
        provider_metadata = metadata.provider_metadata
        expected_keys = [
            "api_source", "musixmatch_track_id", "musixmatch_lyrics_id"
        ]
        
        for key in expected_keys:
            value = provider_metadata.get(key)
            print(f"✅ provider_metadata.{key}: {value}")
            assert value is not None, f"Provider metadata key '{key}' should not be None"
        
        print("\n✅ All metadata validation checks passed!")
        
    else:
        pytest.skip("No lyrics returned - cannot validate metadata")


if __name__ == "__main__":
    """Run the tests directly."""
    try:
        print("🧪 Running Musixmatch provider manual tests...")
        
        test_musixmatch_provider()
        print("\n" + "="*60)
        
        test_musixmatch_provider_no_results()
        print("\n" + "="*60)
        
        test_musixmatch_provider_metadata_validation()
        print("\n" + "="*60)
        
        print("\n🎉 All manual tests completed successfully!")
        
    except pytest.skip.Exception as e:
        print(f"Tests skipped: {e}")
    except Exception as e:
        print(f"Tests failed: {e}")
        raise 