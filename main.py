"""RISC-V Architectural Parameter Extractor CLI.

Two-Stage LLM Extraction & Verification Pipeline using OpenAI:
Stage 1: Extract candidate parameters from specification snippets.
Stage 2: Verify candidates against grounding & variability rules to prune hallucinations/false positives.
Output: Validated structured YAML saved to results.yaml.
"""

import json
import os
import sys
import yaml
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

from snippets import SNIPPETS
from prompts import REFINED_EXTRACTOR_PROMPT, VERIFIER_PROMPT

# Load environment variables from .env file
load_dotenv()


class Parameter(BaseModel):
    name: str = Field(description="Concise snake_case parameter identifier")
    description: str = Field(description="Clear explanation of the parameter's role")
    type: str = Field(description="Category of variability (e.g. implementation-specific, optional)")
    constraints: List[str] = Field(default_factory=list, description="Explicit constraints from text")


class ParameterList(BaseModel):
    parameters: List[Parameter] = Field(default_factory=list, description="List of extracted parameters")


def get_openai_client() -> tuple[OpenAI, str]:
    """Initializes OpenAI client and retrieves configured model."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[!] ERROR: OPENAI_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)
    return client, model


def call_openai_structured(client: OpenAI, model: str, prompt: str) -> ParameterList:
    """Invokes OpenAI API with structured Pydantic schema enforcement."""
    try:
        response = client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format=ParameterList,
            temperature=0.0,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("OpenAI returned null structured output.")
        return parsed
    except Exception as e:
        print(f"[!] OpenAI API call failed: {e}")
        sys.exit(1)


def process_snippet(client: OpenAI, model: str, snippet: Dict[str, str]) -> Dict[str, Any]:
    """Runs the two-stage extraction and verification pipeline for a single snippet."""
    source = snippet["source"]
    text = snippet["text"]

    print(f"\n--- Processing: {source} ---")

    # STAGE 1: Candidate Extraction
    extractor_prompt = REFINED_EXTRACTOR_PROMPT.format(snippet=text)
    stage1_result = call_openai_structured(client, model, extractor_prompt)
    print(f"[Stage 1] Extracted {len(stage1_result.parameters)} candidate parameter(s).")
    for p in stage1_result.parameters:
        print(f"  - Candidate: {p.name} ({p.type})")

    # STAGE 2: Verification & Hallucination Pruning
    candidates_json = json.dumps([p.model_dump() for p in stage1_result.parameters], indent=2)
    verifier_prompt = VERIFIER_PROMPT.format(snippet=text, candidates_json=candidates_json)
    stage2_result = call_openai_structured(client, model, verifier_prompt)
    print(f"[Stage 2] Verified {len(stage2_result.parameters)} parameter(s) post-audit.")
    for p in stage2_result.parameters:
        print(f"  ✓ Validated: {p.name}")

    return {
        "source": source,
        "parameters": [p.model_dump() for p in stage2_result.parameters],
    }


def main():
    print("==================================================")
    print("RISC-V Architectural Parameter Extractor Pipeline")
    print("==================================================")

    client, model = get_openai_client()
    print(f"Provider: OpenAI | Model: {model}")

    results = []
    for snippet in SNIPPETS:
        result = process_snippet(client, model, snippet)
        results.append(result)

    output_data = {"results": results}

    # Format and validate YAML string
    yaml_str = yaml.dump(output_data, sort_keys=False, default_flow_style=False)

    try:
        yaml.safe_load(yaml_str)
        print("\n[✓] YAML output verified successfully.")
    except Exception as e:
        print(f"\n[!] YAML validation failed: {e}")
        sys.exit(1)

    output_path = "results.yaml"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)

    print(f"[✓] Results written to {output_path}")
    print("==================================================")


if __name__ == "__main__":
    main()
