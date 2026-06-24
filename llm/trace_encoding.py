import json
from pathlib import Path
from string import Template
from typing import Dict
from typing import List
from typing import Optional

from openai import OpenAI

client = OpenAI()


class TraceEncodingError(Exception):
    pass


class TraceEncoder:
    """
    Semantic Trace Encoding.

    Paper Section E.d:

    Convert ranked behavioral progressions
    into structured semantic guidance traces.

    Output:

        Gf = {
            (rank, objective, semantic_trace)
        }
    """

    def __init__(
        self,
        model: str = "gpt-4.1",
        prompt_path: Optional[str] = None,
    ):
        self.model = model

        if prompt_path is None:
            prompt_path = (
                Path(__file__).parent
                / "prompts"
                / "trace_encoding.txt"
            )

        self.prompt_path = Path(
            prompt_path
        )

    def load_prompt(self) -> str:
        return self.prompt_path.read_text(
            encoding="utf-8"
        )

    def build_prompt(
        self,
        semantic_tags: List[str],
        semantic_profile: Dict,
        objectives: List[Dict],
    ) -> str:
        """
        Fill prompt template.
        """

        template = Template(
            self.load_prompt()
        )

        return template.safe_substitute(
            semantic_tags=json.dumps(
                semantic_tags,
                indent=2,
                ensure_ascii=False,
            ),
            semantic_profile=json.dumps(
                semantic_profile,
                indent=2,
                ensure_ascii=False,
            ),
            objectives=json.dumps(
                objectives,
                indent=2,
                ensure_ascii=False,
            ),
        )

    def encode(
        self,
        semantic_tags: List[str],
        semantic_profile: Dict,
        objectives: List[Dict],
    ) -> Dict:
        """
        Paper E.d

        Input:

            semantic tags

            semantic profile

            ranked objectives

        Output:

            {
                guidance_traces:
                [
                    {
                        rank,
                        objective,
                        trace
                    }
                ]
            }
        """

        prompt = self.build_prompt(
            semantic_tags=semantic_tags,
            semantic_profile=semantic_profile,
            objectives=objectives,
        )

        response = (
            client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                messages=[
                    {
                        "role": "system",
                        "content":
                        (
                            "You are an expert in "
                            "symbolic execution, "
                            "semantic-guided exploration, "
                            "protocol analysis, "
                            "parser analysis, "
                            "and software behavior modeling."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            )
        )

        content = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        try:

            result = json.loads(
                content
            )

        except Exception as e:

            raise TraceEncodingError(
                f"Invalid JSON returned:\n{content}"
            ) from e

        self.validate(
            result,
            semantic_tags,
        )

        return result

    def validate(
        self,
        result: Dict,
        semantic_tags: List[str],
    ) -> None:
        """
        Validate traces.

        Paper requirement:

        Every trace element must come
        from generated semantic tags.
        """

        if "guidance_traces" not in result:

            raise TraceEncodingError(
                "Missing guidance_traces field."
            )

        tag_set = set(
            semantic_tags
        )

        for item in result[
            "guidance_traces"
        ]:

            if "trace" not in item:

                raise TraceEncodingError(
                    "Trace missing."
                )

            trace = item["trace"]

            if not isinstance(
                trace,
                list,
            ):
                raise TraceEncodingError(
                    "Trace must be list."
                )

            for tag in trace:

                if tag not in tag_set:

                    raise TraceEncodingError(
                        f"Unknown semantic tag: {tag}"
                    )

    def convert_to_cache_format(
        self,
        encoded_result: Dict,
    ) -> List[Dict]:
        """
        Convert to internal SASE format.

        Paper:

        Gf = {
          (rank, objective, ST)
        }
        """

        guidance = []

        for item in encoded_result[
            "guidance_traces"
        ]:

            guidance.append(
                {
                    "rank":
                        item["rank"],

                    "objective":
                        item["objective"],

                    "semantic_trace":
                        item["trace"],
                }
            )

        return guidance

    def save_guidance(
        self,
        function_name: str,
        encoded_result: Dict,
        output_dir: str,
    ) -> str:
        """
        Save encoded guidance traces.

        Cache key will later be:

            (current_semantic_trace,
             function_name)
        """

        output_dir = Path(
            output_dir
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = (
            output_dir
            / f"{function_name}.guidance.json"
        )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                encoded_result,
                f,
                indent=2,
                ensure_ascii=False,
            )

        return str(
            output_path
        )


def encode_traces(
    semantic_tags: List[str],
    semantic_profile: Dict,
    objectives: List[Dict],
    model: str = "gpt-4.1",
) -> Dict:
    """
    High-level API.
    """

    encoder = TraceEncoder(
        model=model
    )

    return encoder.encode(
        semantic_tags=semantic_tags,
        semantic_profile=semantic_profile,
        objectives=objectives,
    )


def encode_and_cache(
    function_name: str,
    semantic_tags: List[str],
    semantic_profile: Dict,
    objectives: List[Dict],
    cache_dir: str,
    model: str = "gpt-4.1",
):
    """
    Complete paper workflow.

        Semantic Profile
                +
        Ranked Objectives
                +
        Semantic Tags

                ↓

        Trace Encoding

                ↓

        Guidance Traces

                ↓

        Cache
    """

    encoder = TraceEncoder(
        model=model
    )

    result = encoder.encode(
        semantic_tags=semantic_tags,
        semantic_profile=semantic_profile,
        objectives=objectives,
    )

    cache_file = encoder.save_guidance(
        function_name=function_name,
        encoded_result=result,
        output_dir=cache_dir,
    )

    return {
        "guidance": result,
        "cache_file": cache_file,
    }