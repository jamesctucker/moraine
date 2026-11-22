"""Tests for scripts/workspace/lib.py and scripts/workspace/frontmatter.py."""

from frontmatter import ParseErrorKind, parse, parse_detailed
from test_helpers import load_module


class TestParseFrontmatter:
    """Tests the consolidated frontmatter module (scripts/workspace/frontmatter.py)."""

    def test_valid_frontmatter(self):
        content = """---
name: test
value: 42
---
Body here."""
        fm, body = parse(content)
        assert fm == {"name": "test", "value": 42}
        assert body.strip() == "Body here."

    def test_missing_frontmatter(self):
        content = "# No frontmatter\nBody here."
        fm, body = parse(content)
        assert fm is None
        assert body == content

        result = parse_detailed(content)
        assert result.frontmatter is None
        assert result.error is None  # absence is not an error

    def test_malformed_frontmatter(self):
        content = "---\nname: test\n"
        fm, body = parse(content)
        assert fm is None  # common case: returns None
        assert body == content  # entire content is body

        result = parse_detailed(content)
        assert result.error is not None
        assert "MALFORMED" in result.error.kind.name

    def test_invalid_yaml(self):
        content = "---\n: invalid yaml\n---\nBody"
        fm, body = parse(content)
        assert fm is None
        assert body.strip() == "Body"

        result = parse_detailed(content)
        assert result.error is not None
        assert result.error.kind.name == "INVALID_YAML"

    def test_not_a_mapping(self):
        content = "---\n[list, not, dict]\n---\nBody"
        fm, body = parse(content)
        assert fm is None
        assert body.strip() == "Body"

        result = parse_detailed(content)
        assert result.error is not None
        assert result.error.kind.name == "NOT_A_MAPPING"

    def test_empty_frontmatter(self):
        content = "---\n{}\n---\nBody"
        fm, body = parse(content)
        assert fm == {}
        assert body.strip() == "Body"

    def test_strips_surrounding_whitespace(self):
        content = "---\ntags: [a, b]\n---\n\n# Session\n\nBody"
        fm, _body = parse(content)
        assert fm == {"tags": ["a", "b"]}


class TestLineAnchoredDelimiters:
    """Dashes inside a scalar or body must never truncate frontmatter."""

    def test_plain_scalar_containing_dashes(self):
        content = "---\ntitle: a---b\n---\nBody"
        fm, body = parse(content)
        assert fm == {"title": "a---b"}
        assert body == "Body"

    def test_quoted_scalar_containing_dashes(self):
        content = '---\ntitle: "a---b"\n---\nBody'
        fm, body = parse(content)
        assert fm == {"title": "a---b"}
        assert body == "Body"

    def test_crlf_file_parsed_and_body_preserved(self):
        content = "---\r\nname: crlf\r\n---\r\nLine one\r\nLine two\r\n"
        fm, body = parse(content)
        assert fm == {"name": "crlf"}
        assert body == "Line one\r\nLine two\r\n"

    def test_body_horizontal_rule_stays_in_body(self):
        content = "---\nname: x\n---\nBody\n\n---\n\nAfter the rule"
        fm, body = parse(content)
        assert fm == {"name": "x"}
        assert body.startswith("Body")
        assert "---" in body
        assert "After the rule" in body

    def test_malformed_opening_text_on_delimiter_line(self):
        content = "--- name: inline\n---\nBody"
        result = parse_detailed(content)
        assert result.frontmatter is None
        assert result.error is not None
        assert "MALFORMED" in result.error.kind.name
        assert result.body == content

    def test_malformed_opening_longer_rule(self):
        content = "----\nname: x\n----\nBody"
        result = parse_detailed(content)
        assert result.frontmatter is None
        assert result.error is not None
        assert "MALFORMED" in result.error.kind.name

    def test_delimiter_with_trailing_whitespace_accepted(self):
        content = "--- \nname: padded\n---\t\nBody"
        fm, body = parse(content)
        assert fm == {"name": "padded"}
        assert body == "Body"

    def test_opening_without_closing_still_malformed(self):
        content = "---\nname: x\n"
        result = parse_detailed(content)
        assert result.error is not None
        assert result.error.kind is ParseErrorKind.MALFORMED_DELIMITER

    def test_empty_frontmatter_mapping(self):
        content = "---\n---\nBody"
        result = parse_detailed(content)
        assert result.error is not None
        assert result.error.kind is ParseErrorKind.NOT_A_MAPPING


class TestWorkspace:
    def test_workspace_path_exists(self, scripts_dir):
        lib = load_module("lib", scripts_dir / "lib.py")
        assert lib.WORKSPACE.exists()
        assert (lib.WORKSPACE / "scripts" / "workspace").is_dir()

    def test_workspace_is_absolute(self, scripts_dir):
        lib = load_module("lib", scripts_dir / "lib.py")
        assert lib.WORKSPACE.is_absolute()
