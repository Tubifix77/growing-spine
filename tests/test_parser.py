"""test_parser.py — tests for executive/parser.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from executive.parser import parse_bash_blocks

def test_basic_bash():
    text = "Here is a command:\n```bash\necho hello\n```\nDone."
    blocks = parse_bash_blocks(text)
    assert blocks == ["echo hello"], f"got {blocks}"
    print("  test_basic_bash: PASS")

def test_sh_lang():
    text = "```sh\nls -la\n```"
    blocks = parse_bash_blocks(text)
    assert blocks == ["ls -la"], f"got {blocks}"
    print("  test_sh_lang: PASS")

def test_multiple_blocks():
    text = "```bash\necho one\n```\nsome text\n```bash\necho two\n```"
    blocks = parse_bash_blocks(text)
    assert blocks == ["echo one", "echo two"], f"got {blocks}"
    print("  test_multiple_blocks: PASS")

def test_ignores_python():
    text = "```python\nprint('hi')\n```\n```bash\necho yes\n```"
    blocks = parse_bash_blocks(text)
    assert blocks == ["echo yes"], f"got {blocks}"
    print("  test_ignores_python: PASS")

def test_empty_block_skipped():
    text = "```bash\n\n```"
    blocks = parse_bash_blocks(text)
    assert blocks == [], f"got {blocks}"
    print("  test_empty_block_skipped: PASS")

def test_no_blocks():
    text = "Just some plain text with no code blocks."
    blocks = parse_bash_blocks(text)
    assert blocks == [], f"got {blocks}"
    print("  test_no_blocks: PASS")

def test_multiline_command():
    text = "```bash\necho line1\necho line2\necho line3\n```"
    blocks = parse_bash_blocks(text)
    assert len(blocks) == 1
    assert "echo line1" in blocks[0]
    assert "echo line3" in blocks[0]
    print("  test_multiline_command: PASS")
