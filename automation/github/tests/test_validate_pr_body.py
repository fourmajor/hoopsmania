from automation.github.validate_pr_body import validate_content


def test_validate_content_accepts_real_newlines() -> None:
    body = "## Summary\n- one\n\n## Policy\nCloses #123\nAI Employee: pipewire\n"
    ok, msg = validate_content(body)
    assert ok, msg


def test_validate_content_rejects_literal_backslash_n() -> None:
    body = "## Summary\\n- one\\n\\n## Policy\\nCloses #123\\nAI Employee: pipewire"
    ok, msg = validate_content(body)
    assert not ok
    assert "literal escaped newline" in msg
