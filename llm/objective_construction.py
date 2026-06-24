import json
from pathlib import Path
from string import Template
from typing import Dict
from typing import List
from typing import Optional

from openai import OpenAI

client = OpenAI()


class ObjectiveConstructionError(Exception):
    pass


class RAGRetriever:
    """
    Simple document retriever.

    Can later be replaced by:
    - FAISS
    - Chroma
    - Milvus
    - Elasticsearch
    """

    def __init__(
        self,
        knowledge_dir: str,
    ):
        self.knowledge_dir = Path(
            knowledge_dir
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> str:
        """
        Simple keyword retrieval.

        Replace with embedding search
        in production.
        """

        if not self.knowledge_dir.exists():
            return ""

        candidates = []

        for file_path in self.knowledge_dir.rglob("*"):

            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

            except Exception:
                continue

            score = 0

            query_tokens = (
                query.lower()
                .replace("\n", " ")
                .split()
            )

            text_lower = content.lower()

            for token in query_tokens:

                if token in text_lower:
                    score += 1

            if score > 0:
                candidates.append(
                    (
                        score,
                        content,
                    )
                )

        candidates.sort(
            key=lambda x: x[0],
            reverse=True,
        )

        selected = candidates[:top_k]

        return "\n\n".join(
            x[1]
            for x in selected
        )


class ObjectiveConstructor:

    def __init__(
        self,
        model: str = "gpt-4.1",
        prompt_path: Optional[str] = None,
        use_rag: bool = False,
        knowledge_dir: Optional[str] = None,
    ):
        self.model = model

        if prompt_path is None:
            prompt_path = (
                Path(__file__).parent
                / "prompts"
                / "objective_construction.txt"
            )

        self.prompt_path = Path(
            prompt_path
        )

        self.use_rag = use_rag

        self.retriever = None

        if use_rag and knowledge_dir:
            self.retriever = RAGRetriever(
                knowledge_dir
            )

    def load_prompt(self) -> str:

        return self.prompt_path.read_text(
            encoding="utf-8"
        )

    def build_retrieval_query(
        self,
        function_name: str,
        semantic_tags: List[str],
        source_code: str,
    ) -> str:
        """
        Build retrieval query.
        """

        return f"""
Function:
{function_name}

Semantic Tags:
{" ".join(semantic_tags)}

Source:
{source_code[:4000]}
"""

    def retrieve_domain_knowledge(
        self,
        function_name: str,
        semantic_tags: List[str],
        source_code: str,
    ) -> str:

        if not self.use_rag:
            return ""

        if self.retriever is None:
            return ""

        query = self.build_retrieval_query(
            function_name=function_name,
            semantic_tags=semantic_tags,
            source_code=source_code,
        )

        return self.retriever.retrieve(
            query=query,
            top_k=5,
        )

    def build_prompt(
        self,
        function_name: str,
        source_code: str,
        call_context: str,
        semantic_tags: List[str],
        manual: str,
        input_spec: str,
        retrieved_knowledge: str,
    ) -> str:

        template = Template(
            self.load_prompt()
        )

        return template.safe_substitute(
            function_name=function_name,
            source_code=source_code,
            call_context=call_context,
            semantic_tags=json.dumps(
                semantic_tags,
                indent=2,
            ),
            manual=manual,
            input_spec=input_spec,
            retrieved_knowledge=retrieved_knowledge,
        )

    def construct(
        self,
        function_name: str,
        source_code: str,
        call_context: str,
        semantic_tags: List[str],
        manual: str,
        input_spec: str,
    ) -> Dict:
        """
        Paper E.c

        Input:
            source code
            call stack context
            semantic tags
            manual
            input specification

        Output:
            ranked semantic objectives
        """

        retrieved_knowledge = (
            self.retrieve_domain_knowledge(
                function_name=function_name,
                semantic_tags=semantic_tags,
                source_code=source_code,
            )
        )

        prompt = self.build_prompt(
            function_name=function_name,
            source_code=source_code,
            call_context=call_context,
            semantic_tags=semantic_tags,
            manual=manual,
            input_spec=input_spec,
            retrieved_knowledge=retrieved_knowledge,
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
                            "You are an expert "
                            "in symbolic execution, "
                            "program analysis, "
                            "vulnerability discovery, "
                            "protocol analysis, "
                            "and semantic reasoning."
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

            raise ObjectiveConstructionError(
                f"Invalid JSON returned:\n{content}"
            ) from e

        return result


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
    High-level API.

    Supports:

    Mode 1:
        No RAG

    Mode 2:
        RAG-assisted
    """

    constructor = ObjectiveConstructor(
        use_rag=use_rag,
        knowledge_dir=knowledge_dir,
    )

    return constructor.construct(
        function_name=function_name,
        source_code=source_code,
        call_context=call_context,
        semantic_tags=semantic_tags,
        manual=manual,
        input_spec=input_spec,
    )