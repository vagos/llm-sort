import click
import llm
import sys
from functools import cmp_to_key

# This default prompt template is used to ask the LLM which of two lines is more relevant
# given a query. It expects the answer to start with "Passage A" or "Passage B".
DEFAULT_PAIRWISE_PROMPT = """
Given the query:
{query}

Compare the following two lines:

Line A:
{docA}

Line B:
{docB}

Which line is more relevant to the query? Please answer with "Line A" or "Line B".
""".strip()


@llm.hookimpl
def register_commands(cli):
    @cli.command(context_settings=dict(ignore_unknown_options=True))
    @click.option(
        "--query",
        required=True,
        help="The query to use for semantic sorting. Lines will be sorted based on this query."
    )
    @click.option(
        "--method",
        type=click.Choice(["allpair", "sorting", "sliding"]),
        default="sorting",
        help="Semantic sorting method to use:\n"
             "  allpair  - Compare every pair and aggregate scores.\n"
             "  sorting  - Use a sorting algorithm with pairwise comparisons.\n"
             "  sliding  - Use a sliding-window (bubble sort) approach."
    )
    @click.option(
        "--top-k",
        type=int,
        default=0,
        help="Only keep the top K sorted lines (0 to keep all)."
    )
    @click.option("-m", "--model", help="LLM model to use for semantic sorting.")
    @click.option("--prompt", help="Custom pairwise ranking prompt template.")
    @click.argument("files", type=click.File("r"), nargs=-1)
    def sort(query, method, top_k, model, prompt, files):
        """
        Sort input lines semantically

        This command reads lines either from the FILES provided as arguments or, if no files
        are given, from standard input. Each line is treated as a separate document. The lines are then
        sorted semantically using an LLM with one of three pairwise ranking methods:

          • allpair  — PRP-Allpair: Compare every pair of lines and aggregate scores.
          • sorting  — PRP-Sorting: Use pairwise comparision with a sorting algorithm.
          • sliding  — PRP-Sliding-K: Perform a sliding-window (bubble sort) pass repeatedly.

        Example usage:
            llm sort --query "Which name is more suitable for a pet monkey?" names.txt

        The sorted lines are written to standard output.
        """
        # If no files are provided, default to reading from standard input.
        if not files:
            files = [sys.stdin]

        documents = []
        for f in files:
            for line in f:
                # Remove the trailing newline (but preserve other whitespace)
                line = line.rstrip("\n")
                # Only add non-empty lines.
                if line:
                    documents.append({"id": str(len(documents)), "content": line})

        if not documents:
            click.echo("No input lines provided.", err=True)
            return

        # Initialize the LLM model.
        from llm.cli import get_default_model
        from llm import get_key
        model_obj = llm.get_model(model or get_default_model())
        if model_obj.needs_key:
            model_obj.key = get_key("", model_obj.needs_key, model_obj.key_env_var)

        # Use the custom prompt if provided; otherwise, use the default.
        prompt_template = prompt or DEFAULT_PAIRWISE_PROMPT

        # Define a helper function that compares two lines (documents) by calling the LLM twice
        # (swapping the order to mitigate bias) and returning:
        #   1  => First line is preferred.
        #  -1  => Second line is preferred.
        #   0  => Tie or inconclusive.
        def pairwise_decision(query, docA, docB):
            # First prompt: (docA, docB)
            prompt1 = prompt_template.format(query=query, docA=docA, docB=docB)
            response1 = model_obj.prompt(prompt1, system="You are a helpful assistant.").text().strip()

            # Second prompt: (docB, docA)
            prompt2 = prompt_template.format(query=query, docA=docB, docB=docA)
            response2 = model_obj.prompt(prompt2, system="You are a helpful assistant.").text().strip()

            # Normalize responses.
            resp1 = response1.lower()
            resp2 = response2.lower()

            if resp1.startswith("line a") and resp2.startswith("line b"):
                return 1   # docA is preferred
            elif resp1.startswith("line b") and resp2.startswith("line a"):
                return -1  # docB is preferred
            else:
                return 0   # Tie or inconclusive

        # Sort the documents using the selected method.
        sorted_docs = []
        if method == "allpair":
            # PRP-Allpair: Compare every pair and aggregate scores.
            for doc in documents:
                doc["score"] = 0.0
            n = len(documents)
            for i in range(n):
                for j in range(i + 1, n):
                    decision = pairwise_decision(query, documents[i]["content"], documents[j]["content"])
                    if decision == 1:
                        documents[i]["score"] += 1.0
                    elif decision == -1:
                        documents[j]["score"] += 1.0
                    else:
                        documents[i]["score"] += 0.5
                        documents[j]["score"] += 0.5
            sorted_docs = sorted(documents, key=lambda d: d["score"], reverse=True)

        elif method == "sorting":
            # PRP-Sorting: Use a custom comparator with a sorting algorithm.
            def compare_docs(a, b):
                decision = pairwise_decision(query, a["content"], b["content"])
                if decision == 1:
                    return -1  # a should come before b
                elif decision == -1:
                    return 1   # b should come before a
                else:
                    return 0
            sorted_docs = sorted(documents, key=cmp_to_key(compare_docs))

        elif method == "sliding":
            # PRP-Sliding-K: Perform K sliding-window passes (similar to bubble sort).
            sorted_docs = documents[:]
            n = len(sorted_docs)
            for _ in range(top_k or n):
                # Traverse from right to left.
                for i in reversed(range(n - 1)):
                    decision = pairwise_decision(query, sorted_docs[i]["content"], sorted_docs[i + 1]["content"])
                    if decision == -1:
                        sorted_docs[i], sorted_docs[i + 1] = sorted_docs[i + 1], sorted_docs[i]
        else:
            click.echo("Invalid sorting method specified.", err=True)
            return

        if top_k > 0:
            sorted_docs = sorted_docs[:top_k]

        # Output the sorted lines to standard output.
        for doc in sorted_docs:
            click.echo(doc["content"])
