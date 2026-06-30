from src.services.clean import normalize


def test_collapses_repeats():
    assert normalize("heyyyyy") == "heyy"


def test_urls_become_link():
    assert normalize("look https://example.com/x here") == "look link here"


def test_custom_emoji_reads_as_name():
    assert normalize("nice <:big_smile:123456>") == "nice big smile"


def test_unresolved_mentions_dropped():
    assert normalize("hi <@123> and <#456>") == "hi and"


def test_resolved_mention_prefix_stripped():
    assert normalize("hi @Nick") == "hi Nick"


def test_spoiler_hidden():
    assert normalize("the ending is ||he dies||") == "the ending is spoiler"


def test_pronunciation_replacements_applied():
    out = normalize("gg wp", replacements={"gg": "good game", "wp": "well played"})
    assert out == "good game well played"


def test_length_cap_adds_ellipsis():
    out = normalize("word " * 100, max_chars=20)
    assert out.endswith("...")
    assert len(out) <= 24


def test_markdown_stripped():
    assert normalize("**bold** and _italic_") == "bold and italic"


def test_code_block_summarized():
    assert normalize("see ```print(1)``` ok") == "see code block ok"
