import pytest

from app.taxonomy import extract_pubpeer_url


@pytest.mark.parametrize(("notes", "expected"), [
    (None, None),
    ("No link", None),
    ("https://pubpeer.com/about", None),
    ("https://pubpeer.com/search", None),
    ("https://pubpeer.com/search?q=", None),
    ("https://pubpeer.com.evil.test/publications/ABC123", None),
    ("https://pubpeer.com/publications/ABC-123", None),
    ("See (http://www.pubpeer.com/publications/ABC123).", "https://pubpeer.com/publications/ABC123"),
    ("https://pubpeer.com/publications/ABC123#comment1", "https://pubpeer.com/publications/ABC123"),
    ("https://pubpeer.com/search?q=10.1000/example", "https://pubpeer.com/search?q=10.1000/example"),
    ("https://pubpeer.com/search?q=10.1000%2Fexample;", "https://pubpeer.com/search?q=10.1000%2Fexample"),
    ("See (https://pubpeer.com/search?q=10.1000/example(foo)).", "https://pubpeer.com/search?q=10.1000/example(foo)"),
    ("https://pubpeer.com/search?q=some+title", "https://pubpeer.com/search?q=some+title"),
    ("https://pubpeer.com/about https://pubpeer.com/publications/ABC123", "https://pubpeer.com/publications/ABC123"),
    ("https://pubpeer.com/search?q=title https://pubpeer.com/publications/ABC123", "https://pubpeer.com/publications/ABC123"),
])
def test_pubpeer_links_are_preserved_without_inventing_publications(notes, expected):
    assert extract_pubpeer_url(notes) == expected
