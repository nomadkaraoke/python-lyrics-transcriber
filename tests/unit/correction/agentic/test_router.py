from lyrics_transcriber.correction.agentic.router import ModelRouter


def test_model_router_returns_strings():
    r = ModelRouter()
    m1 = r.choose_model("gap", 0.2)
    m2 = r.choose_model("gap", 0.8)
    assert isinstance(m1, str) and isinstance(m2, str)


