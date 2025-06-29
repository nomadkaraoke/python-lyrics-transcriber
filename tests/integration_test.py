#!/usr/bin/env python3

import pytest
import subprocess
import sys
import os
import re

def test_cli_help_loads():
    """Test that the CLI help text loads successfully after package installation."""
    # Run the CLI with --help flag
    result = subprocess.run(
        [sys.executable, "-m", "lyrics_transcriber.cli.cli_main", "--help"], 
        capture_output=True, 
        text=True
    )
    
    # Check that the command executed successfully
    assert result.returncode == 0, f"CLI help command failed with: {result.stderr}"
    
    # Check that the output contains expected help text
    assert "lyrics-transcriber" in result.stdout, "Expected CLI name not found in help output"
    assert "audio_file" in result.stdout, "Expected parameter not found in help output"
    
    # Check for basic command structure
    assert re.search(r"usage:", result.stdout, re.IGNORECASE), "No usage section found in help output"

def test_package_version():
    """Test that the package version is accessible."""
    try:
        from lyrics_transcriber import __version__
        assert __version__, "Version should not be empty"
        assert re.match(r"^\d+\.\d+\.\d+", __version__), "Version should follow semantic versioning"
    except ImportError:
        pytest.fail("Could not import package version")

if __name__ == "__main__":
    # This allows the file to be run directly for quick testing
    test_cli_help_loads()
    test_package_version()
    print("Integration tests passed!") 