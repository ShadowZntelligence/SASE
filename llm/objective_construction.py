from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI


###############################################################################
# Configuration
###############################################################################

OPENAI_MODEL = "gpt-4o"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

_client = OpenAI(api_key=OPENAI_API_KEY)


###############################################################################
# Prompt Loader
###############################################################################

def _load_prompt(prompt_name: str) -> str:
    """
    Load a prompt template from the prompts directory.
    """

    prompt_dir = Path(__file__).parent / "prompts"

    prompt_path = prompt_dir / prompt_name

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


###############################################################################
# LLM Helper
###############################################################################

def _call_llm(
    prompt: str,
    user_content: str,
    temperature: float = 0.2,
) -> str:
    """
    Invoke the OpenAI Chat Completion API.
    """

    response = _client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=temperature,
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
    )

    return response.choices[0].message.content.strip()


###############################################################################
# JSON Helper
###############################################################################

def _parse_json(text: str):
    """
    Parse JSON returned by the LLM.

    Markdown code fences are automatically removed.
    """

    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return json.loads(text)


###############################################################################
# RAG
###############################################################################

def _retrieve_knowledge(
    semantic_profile: Dict,
    manual: str,
    input_spec: str,
    use_rag: bool,
    knowledge_dir: Optional[str],
) -> str:
    """
    Retrieve domain knowledge.

    Non-RAG mode:
        Directly concatenate the manual and specification.

    RAG mode:
        Retrieve the most relevant documents from knowledge_dir.
    """

    #
    # Non-RAG mode
    #
    if not use_rag:

        return (
            "# Program Manual\n\n"
            + manual
            + "\n\n"
            + "# Input Specification\n\n"
            + input_spec
        )

    #
    # Fallback
    #
    if knowledge_dir is None:

        return (
            "# Program Manual\n\n"
            + manual
            + "\n\n"
            + "# Input Specification\n\n"
            + input_spec
        )

    if not os.path.isdir(knowledge_dir):

        return (
            "# Program Manual\n\n"
            + manual
            + "\n\n"
            + "# Input Specification\n\n"
            + input_spec
        )

    #
    # Simple keyword-based retrieval.
    #
    keywords = []

    keywords.extend(
        semantic_profile.get("major_components", [])
    )

    keywords.extend(
        semantic_profile.get("major_behaviors", [])
    )

    keywords.extend(
        semantic_profile.get("important_objects", [])
    )

    documents = []

    for filename in os.listdir(knowledge_dir):

        if not filename.endswith(".txt"):
            continue

        path = os.path.join(
            knowledge_dir,
            filename,
        )

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            text = f.read()

        score = 0

        lower = text.lower()

        for keyword in keywords:

            score += lower.count(keyword.lower())

        documents.append(
            (
                score,
                filename,
                text,
            )
        )

    documents.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    #
    # Keep Top-5 documents.
    #
    selected = []

    for _, filename, text in documents[:5]:

        selected.append(
            f"# {filename}\n\n{text}"
        )

    #
    # Always include the original manual/specification.
    #
    selected.append(
        "# Program Manual\n\n"
        + manual
    )

    selected.append(
        "# Input Specification\n\n"
        + input_spec
    )

    return "\n\n".join(selected)


###############################################################################
# Stage 1
###############################################################################

def _build_semantic_profile(
    function_name: str,
    source_code: str,
    call_context: str,
    semantic_tags: List[str],
) -> Dict:
    """
    Stage 1.

    Generate the semantic profile of the target function.
    """

    prompt = _load_prompt(
        "profile_generation.txt"
    )

    user = f"""
Function:

{function_name}

==================================================

Source Code:

{source_code}

==================================================

Call Context:

{call_context}

==================================================

Semantic Tags:

{json.dumps(semantic_tags, indent=2)}
"""

    response = _call_llm(
        prompt,
        user,
    )

    return _parse_json(response)

###############################################################################
# Stage 2
###############################################################################

def _build_domain_knowledge(
    semantic_profile: Dict,
    manual: str,
    input_spec: str,
    use_rag: bool,
    knowledge_dir: Optional[str],
) -> Dict:
    """
    Stage 2.

    Build domain knowledge conditioned on the semantic profile.

    The paper first derives a semantic profile, and then incorporates
    the program manual and the input specification to obtain
    domain-specific knowledge.

    Two modes are supported:

        1. Direct mode (manual + specification)

        2. RAG-assisted mode
    """

    prompt = _load_prompt(
        "domain_knowledge.txt"
    )

    knowledge = _retrieve_knowledge(
        semantic_profile,
        manual,
        input_spec,
        use_rag,
        knowledge_dir,
    )

    user = f"""
Semantic Profile

{json.dumps(semantic_profile, indent=2)}

==================================================

Retrieved Knowledge

{knowledge}
"""

    response = _call_llm(
        prompt,
        user,
    )

    return _parse_json(response)


###############################################################################
# Stage 3
###############################################################################

def _infer_behavior_progressions(
    function_name: str,
    semantic_profile: Dict,
    domain_knowledge: Dict,
) -> List[Dict]:
    """
    Stage 3.

    Infer semantically meaningful behavioral progressions.

    Each progression is still represented in natural language.
    Semantic trace encoding is performed later by trace_encoding.py.
    """

    prompt = _load_prompt(
        "behavior_progression.txt"
    )

    user = f"""
Function

{function_name}

==================================================

Semantic Profile

{json.dumps(semantic_profile, indent=2)}

==================================================

Domain Knowledge

{json.dumps(domain_knowledge, indent=2)}
"""

    response = _call_llm(
        prompt,
        user,
    )

    result = _parse_json(response)

    if isinstance(result, dict):

        if "progressions" in result:
            return result["progressions"]

        if "behaviors" in result:
            return result["behaviors"]

    return result


###############################################################################
# Stage 4
###############################################################################

def _rank_objectives(
    function_name: str,
    semantic_profile: Dict,
    progressions: List[Dict],
) -> List[Dict]:
    """
    Stage 4.

    Rank the inferred behavioral progressions.

    Higher-ranked objectives should contribute more to

        - behavioral diversity

        - vulnerability discovery

    as described in the paper.
    """

    prompt = _load_prompt(
        "objective_ranking.txt"
    )

    user = f"""
Function

{function_name}

==================================================

Semantic Profile

{json.dumps(semantic_profile, indent=2)}

==================================================

Behavior Progressions

{json.dumps(progressions, indent=2)}
"""

    response = _call_llm(
        prompt,
        user,
    )

    ranked = _parse_json(response)

    if isinstance(ranked, dict):

        if "objectives" in ranked:
            ranked = ranked["objectives"]

        elif "results" in ranked:
            ranked = ranked["results"]

    #
    # Normalize ranking.
    #
    for index, obj in enumerate(ranked):

        if "rank" not in obj:
            obj["rank"] = index

    return ranked

###############################################################################
# Public API
###############################################################################

def construct_objectives(
    function_name: str,
    source_code: str,
    call_context: str,
    semantic_tags: List[str],
    manual: str,
    input_spec: str,
    use_rag: bool = False,
    knowledge_dir: Optional[str] = None,
) -> Dict:
    """
    Construct semantic exploration objectives.

    This function implements Section III-E.c of the paper.

    Pipeline:

        Stage 1
            Semantic Profile Generation

        Stage 2
            Domain Knowledge Construction

        Stage 3
            Behavioral Progression Inference

        Stage 4
            Objective Ranking

    Parameters
    ----------
    function_name
        Target function name.

    source_code
        Source code of the target function.

    call_context
        Source code of relevant caller/callee functions.

    semantic_tags
        Semantic tags generated during Tag Creation.

    manual
        Program manual.

    input_spec
        Program input specification.

    use_rag
        Whether to enable RAG-based retrieval.

    knowledge_dir
        Directory containing external knowledge (.txt).

    Returns
    -------
    dict

        {
            "semantic_profile": {...},

            "domain_knowledge": {...},

            "behavior_progressions": [...],

            "objectives": [...]
        }

    The returned "objectives" are still natural-language semantic
    objectives.

    They should be passed to trace_encoding.py to generate the final
    guidance traces.
    """

    #
    # Stage 1
    #
    semantic_profile = _build_semantic_profile(
        function_name=function_name,
        source_code=source_code,
        call_context=call_context,
        semantic_tags=semantic_tags,
    )

    #
    # Stage 2
    #
    domain_knowledge = _build_domain_knowledge(
        semantic_profile=semantic_profile,
        manual=manual,
        input_spec=input_spec,
        use_rag=use_rag,
        knowledge_dir=knowledge_dir,
    )

    #
    # Stage 3
    #
    behavior_progressions = _infer_behavior_progressions(
        function_name=function_name,
        semantic_profile=semantic_profile,
        domain_knowledge=domain_knowledge,
    )

    #
    # Stage 4
    #
    objectives = _rank_objectives(
        function_name=function_name,
        semantic_profile=semantic_profile,
        progressions=behavior_progressions,
    )

    return {
        "function": function_name,
        "semantic_profile": semantic_profile,
        "domain_knowledge": domain_knowledge,
        "behavior_progressions": behavior_progressions,
        "objectives": objectives,
    }


__all__ = [
    "construct_objectives",
]