# AI-Assisted Extraction of Architectural Parameters from RISC-V Specifications

A clean, reproducible Python project for the LFX Mentorship coding challenge. It demonstrates LLM-based structured information extraction, prompt engineering, hallucination control, and structured YAML generation using the OpenAI API.

---

## Challenge Objective

Extract implementation-variable architectural parameters (such as cache capacities, block sizes, optional extensions) from RISC-V specification snippets while strictly ignoring fixed ISA constants, standard encoding rules, and fixed bit-widths.

---

## Pipeline Architecture

```text
RISC-V Specification Snippet
             ↓
    Stage 1: Extractor LLM
             ↓
    Candidate Parameters
             ↓
    Stage 2: Verifier LLM (Hallucination Control)
             ↓
    Validated Parameters
             ↓
       results.yaml
```

---

## Setup Instructions

1. **Clone & Navigate**:

   ```bash
   git clone https://github.com/dhruvil-codes/riscv-parameter-extractor.git
   cd riscv-parameter-extractor
   ```

2. **Create & Activate Virtual Environment** (Optional but recommended):

   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and set your OpenAI API key:
   ```bash
   cp .env.example .env
   ```
   Set `OPENAI_API_KEY` in `.env`:
   ```env
   OPENAI_API_KEY=your_actual_api_key_here
   OPENAI_MODEL=gpt-4o-mini
   ```

---

## How to Run

Execute the pipeline CLI:

```bash
python main.py
```

The script will process all snippets in `snippets.py`, execute the 2-stage OpenAI LLM pipeline, validate the output schema, and generate `results.yaml`.

---

## LLM Details

- **Provider**: OpenAI (`openai` Python SDK)
- **Configured Model**: `gpt-4o-mini` (configurable via `OPENAI_MODEL`)
- **Context Window**: 128,000 tokens (official OpenAI specification)
- **Temperature**: `0.0` (Deterministic generation for maximum reproducibility and precision)
- **Selection Rationale**: High reasoning speed, native JSON schema support for structured output via `client.beta.chat.completions.parse`, cost efficiency, and strong zero-shot instruction adherence.

---

## Prompt Design & Refinement

### Initial Approach

A basic single-pass prompt (`INITIAL_EXTRACTOR_PROMPT` in `prompts.py`) instructed the model to extract architectural parameters based on keyword indicators like _"may"_, _"optional"_, _"should"_, and _"implementation-specific"_.

### Problem Identified

Keyword-driven extraction produced false positives. Descriptive architectural facts and fixed numbers (e.g. 12-bit encoding spaces, CSR privilege mapping rules) were incorrectly extracted as configurable parameters simply because they appeared in the text.

### Refinement (`REFINED_EXTRACTOR_PROMPT`)

The prompt was rewritten to explicitly enforce the core conceptual distinction:

- **Parameter**: A property, value, capability, presence, or size that _varies between conforming implementations_.
- **Fixed Constant / ISA Rule**: A mandated specification property (e.g. CSR 12-bit address space) that is invariant.

### Additional Safeguard (`VERIFIER_PROMPT`)

A second LLM verification stage was added to audit candidates. The verifier verifies grounding in text, checks for implementation variability, prunes fixed constants, and enforces strict schema compliance.

---

## Hallucination-Control Strategy

The two-stage design provides robust hallucination mitigation:

1. **Zero External Knowledge Grounding**: Prompts strictly instruct the model not to invent or infer parameters outside the text.
2. **Deterministic Sampling**: Generation temperature is set to `0.0`.
3. **Structured Schema Enforcement**: Output is constrained to Pydantic schemas (`ParameterList`).
4. **Independent Audit Pass (Stage 2)**: The Verifier LLM re-evaluates all candidate parameters against the source snippet, filtering out unsupported claims, over-inferences, or fixed ISA constants.

---

## Output Format Example (`results.yaml`)

```yaml
results:
  - source: Privileged Spec 19.3.1
    parameters:
      - name: cache_capacity
        description: The total amount of data that can be stored in the cache...
        type: implementation-specific
        constraints: []
      - name: cache_organization
        description: The structure and arrangement of the cache...
        type: implementation-specific
        constraints: []
      - name: cache_block_size
        description: The size of each cache block...
        type: implementation-specific
        constraints:
          - Shall be uniform throughout system in initial CMO extensions
  - source: Privileged Spec 2.1
    parameters: []
  - source: Custom Test Spec 3.1
    parameters:
      - name: vector_register_length
        description: The length of the vector registers...
        type: implementation-defined
        constraints:
          - Must be a power of two
          - Must be between 32 and 65536 bits
```

---

## Observations & Key Results

- **Snippet 1 (Spec 19.3.1)**: Successfully identifies genuine implementation-variable properties (`cache_capacity`, `cache_organization`, `cache_block_size`) while extracting constraints such as system uniformity.
- **Snippet 2 (Spec 2.1)**: Correctly identifies that standard 12-bit CSR encoding spaces and privilege mapping conventions are fixed ISA specifications rather than implementation parameters, returning `[]` without hardcoding.
- **Snippet 3 (Custom Test 3.1)**: Dynamically extracts vector register length (`vector_register_length`) and correctly parses both power-of-two and bit-width range constraints.
