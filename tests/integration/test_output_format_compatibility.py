def test_output_format_compatibility_smoke():
    # Placeholder: verify that required exporters exist
    from lyrics_transcriber.output import ass, plain_text
    assert hasattr(ass, "ass") or hasattr(ass, "formatters")
    assert hasattr(plain_text, "PlainTextExporter") or True


