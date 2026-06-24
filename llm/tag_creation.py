import re
from string import Template
from pathlib import Path

from openai import OpenAI

client = OpenAI()

TAG_PATTERN = re.compile(
    r"/\*\s*SASE_TAG:\s*([A-Z0-9_]+)\s*\*/"
)


class SemanticTagCreationError(Exception):
    pass


def load_prompt() -> str:
    """
    Load tag creation prompt template.
    """

    prompt_path = (
        Path(__file__).parent
        / "prompts"
        / "tag_creation.txt"
    )

    return prompt_path.read_text(
        encoding="utf-8"
    )


def build_prompt(
    function_name: str,
    source_code: str,
    call_context: str,
) -> str:
    """
    Fill prompt template.
    """

    template = Template(load_prompt())

    return template.safe_substitute(
        function_name=function_name,
        source_code=source_code,
        call_context=call_context,
    )


def create_tags(
    function_name: str,
    source_code: str,
    call_context: str,
    model: str = "gpt-4.1",
) -> str:
    """
    Generate annotated source code.

    Returns:
        Annotated source code containing
        SASE_TAG comments.
    """

    prompt = build_prompt(
        function_name=function_name,
        source_code=source_code,
        call_context=call_context,
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content":
                    "You are an expert in symbolic execution and program analysis."
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    annotated_code = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    if not annotated_code:
        raise SemanticTagCreationError(
            "LLM returned empty response."
        )

    return annotated_code


def extract_tags(
    annotated_code: str,
):
    """
    Extract tags and source locations.

    Returns:

    [
        {
            "tag": "...",
            "line": 10
        }
    ]
    """

    results = []

    lines = annotated_code.splitlines()

    for line_no, line in enumerate(
        lines,
        start=1,
    ):
        match = TAG_PATTERN.search(line)

        if not match:
            continue

        results.append(
            {
                "tag": match.group(1),
                "line": line_no,
            }
        )

    return results


def create_tags_and_extract(
    function_name: str,
    source_code: str,
    call_context: str,
):
    """
    Complete semantic tag creation workflow.

    Returns:

    {
        "annotated_code": "...",
        "tags": [...]
    }
    """

    annotated_code = create_tags(
        function_name=function_name,
        source_code=source_code,
        call_context=call_context,
    )

    tags = extract_tags(
        annotated_code
    )

    return {
        "annotated_code": annotated_code,
        "tags": tags,
    }