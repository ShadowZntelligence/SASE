from pathlib import Path

PROMPT_DIR = Path(__file__).parent / "prompts"


def load_prompt(prompt_name: str) -> str:
    """
    Load prompt template from prompts directory.

    Example:
        load_prompt("tag_creation")
    """

    prompt_file = PROMPT_DIR / f"{prompt_name}.txt"

    if not prompt_file.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_file}"
        )

    return prompt_file.read_text(
        encoding="utf-8"
    )