# llm-sort

[LLM](https://llm.datasette.io/) plugin for semantically sorting lines.

## Installation

Install this plugin in the same environment as LLM.
```bash
llm install llm-sort
```

## Usage

The plugin adds a new command, `llm sort`. This command has an interface
similar to the GNU `sort` command, but instead of sorting lines based on
alphabetical order, it input lines based on some semantic ranking criteria.

Lines can be provided via files or standard input. For example:
```bash
# Sort lines from a file using the "sorting" method (default)
llm sort --query "Which line is most inspiring?" unsorted.txt

# Read from standard input
cat unsorted.txt | llm sort --query "Which line is most inspiring?"

# Use a different method, limit the output to the top 5 lines, and specify a custom model and prompt:
llm sort --query "Rank these slogans" --method sliding --top-k 5 --model gpt-4 \
  --prompt 'Decide which line is more compelling. Answer with "Line A" or "Line B" Query: {query} Lines: {docA} {docB}.' unsorted.txt
```

**Note**: The prompt template variables are `{query}`, `{docA}`, and `{docB}`.

The default prompt used is:

> Given the query:
> {query}
> 
> Compare the following two lines:
> 
> Line A:
> {docA}
> 
> Line B:
> {docB}
> 
> Which line is more relevant to the query? Please answer with "Line A" or "Line B".

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd llm-sort
python3 -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
pip install -e '.[test]'
```
To run the tests:
```bash
python -m pytest
```
