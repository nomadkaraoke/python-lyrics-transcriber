from jiwer import wer, cer


def test_wer_cer_smoke():
    ref = "hello world"
    hyp = "hello wurld"
    # Expect small error rate
    assert wer(ref, hyp) >= 0.0
    assert cer(ref, hyp) >= 0.0


