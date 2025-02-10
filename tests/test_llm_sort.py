from click.testing import CliRunner
import re
import pytest
import llm
from llm.cli import cli

# A fake response class to mimic LLM API responses.
class FakeResponse:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text

# A fake LLM model that “compares” two lines by lexicographical order.
# It parses the prompt to extract the two lines (from "Line A:" and "Line B:")
# and returns "Line A" if the first line is less than or equal to the second,
# or "Line B" otherwise.
class FakeModel:
    needs_key = False
    key = None

    def prompt(self, prompt, system):
        m = re.search(r"Line A:\n(.*?)\n\nLine B:\n(.*?)\n", prompt, re.DOTALL)
        if m:
            lineA = m.group(1).strip()
            lineB = m.group(2).strip()
        else:
            lineA, lineB = "", ""
        # In our fake decision, the lexicographically smaller line is preferred.
        if lineA <= lineB:
            return FakeResponse("Line A")
        else:
            return FakeResponse("Line B")

# ----------------------- Tests -----------------------

def test_sort_allpair(monkeypatch):
    # Override the model with our fake model.
    monkeypatch.setattr(llm, "get_model", lambda model=None: FakeModel())
    runner = CliRunner()
    # Provide unsorted lines.
    input_text = "banana\napple\ncherry\n"
    result = runner.invoke(
        cli,
        ["sort", "--query", "Which is best?", "--method", "allpair"],
        input=input_text,
    )
    # Lexicographically, "apple" < "banana" < "cherry"
    expected = "apple\nbanana\ncherry\n"
    assert result.exit_code == 0, result.output
    assert result.output == expected

def test_sort_sorting(monkeypatch):
    monkeypatch.setattr(llm, "get_model", lambda model=None: FakeModel())
    runner = CliRunner()
    input_text = "delta\nalpha\ncharlie\nbravo\n"
    result = runner.invoke(
        cli,
        ["sort", "--query", "Test", "--method", "sorting"],
        input=input_text,
    )
    # Lexicographical order: "alpha", "bravo", "charlie", "delta"
    expected = "alpha\nbravo\ncharlie\ndelta\n"
    assert result.exit_code == 0, result.output
    assert result.output == expected

def test_sort_sliding(monkeypatch):
    monkeypatch.setattr(llm, "get_model", lambda model=None: FakeModel())
    runner = CliRunner()
    input_text = "zeta\nbeta\ngamma\nalpha\n"
    result = runner.invoke(
        cli,
        ["sort", "--query", "Test", "--method", "sliding"],
        input=input_text,
    )
    # Lexicographical order: "alpha", "beta", "gamma", "zeta"
    expected = "alpha\nbeta\ngamma\nzeta\n"
    assert result.exit_code == 0, result.output
    assert result.output == expected

def test_sort_top_k(monkeypatch):
    monkeypatch.setattr(llm, "get_model", lambda model=None: FakeModel())
    runner = CliRunner()
    input_text = "delta\nalpha\ncharlie\nbravo\n"
    result = runner.invoke(
        cli,
        ["sort", "--query", "Test", "--method", "sorting", "--top-k", "2"],
        input=input_text,
    )
    # When keeping only the top 2 lines, we expect "alpha" and "bravo"
    expected = "alpha\nbravo\n"
    assert result.exit_code == 0, result.output
    assert result.output == expected

def test_sort_file_input(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "get_model", lambda model=None: FakeModel())
    # Create a temporary file with unsorted lines.
    file_content = "dog\ncat\nbird\n"
    file_path = tmp_path / "test.txt"
    file_path.write_text(file_content)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["sort", "--query", "Test", "--method", "sorting", str(file_path)],
    )
    # Lexicographical order: "bird", "cat", "dog"
    expected = "bird\ncat\ndog\n"
    assert result.exit_code == 0, result.output
    assert result.output == expected

def test_sort_no_input(monkeypatch):
    monkeypatch.setattr(llm, "get_model", lambda model=None: FakeModel())
    runner = CliRunner()
    # Invoke the command with no input.
    result = runner.invoke(
        cli,
        ["sort", "--query", "Test", "--method", "sorting"],
        input="",
    )
    # Our plugin writes an error message if no input lines are provided.
    assert result.exit_code == 0
    # The error message is sent to stderr.
    assert "No input lines provided." in result.output
