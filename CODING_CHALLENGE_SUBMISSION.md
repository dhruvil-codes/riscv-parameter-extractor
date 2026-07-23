# AI-Assisted Extraction of Architectural Parameters from RISC-V Specifications

**Coding Challenge Submission**  
**Applicant:** Dhruvil Mistry  
**GitHub Repository:** [https://github.com/dhruvil-codes/riscv-parameter-extractor](https://github.com/dhruvil-codes/riscv-parameter-extractor)

---

## 1. Objective

The objective of this challenge was to develop an automated, LLM-based pipeline to extract implementation-variable architectural parameters from RISC-V Instruction Set Architecture (ISA) specification snippets into machine-readable YAML format.

In specification text, words such as *“may”*, *“might”*, *“should”*, *“optional”*, *“optionally”*, *“implementation-defined”*, and *“implementation-specific”* often serve as linguistic indicators that a parameter exists. However, these keywords must not automatically classify a statement as an architectural parameter. 

The core conceptual requirement of this challenge is enforcing the distinction between:
1. **Implementation-Variable Architectural Parameters**: Properties, capacities, block sizes, organizations, or optional capabilities that vary between conforming hardware implementations of the RISC-V specification.
2. **Fixed Architectural Facts / Constants**: Invariant specification rules, fixed bit-width encodings, register address allocations, or privilege conventions mandated by the standard.

The developed solution ensures that fixed ISA constants are not extracted as configurable parameters and every extracted item is grounded directly in the provided source snippet.

---

## 2. LLM Details

The extraction pipeline is built using the official OpenAI Python SDK.

- **Provider**: OpenAI
- **Configured Model**: `gpt-4o-mini` (configurable via `OPENAI_MODEL` environment variable, defaulting to `gpt-4o-mini`)
- **Context Window**: 128,000 tokens (verified from official OpenAI documentation)
- **Sampling Temperature**: `0.0` (used to reduce output variability and favor consistent extraction)
- **Structured Output Mechanism**: Native OpenAI Pydantic schema enforcement via `client.beta.chat.completions.parse(..., response_format=ParameterList)`
- **Selection Rationale**: `gpt-4o-mini` offers high inference speed, strict compliance with structured JSON/Pydantic schemas, cost efficiency, and strong instruction adherence for structured extraction tasks.

---

## 3. Approach

The project uses a clean, two-stage extraction and verification pipeline designed for high accuracy and hallucination control.

```text
RISC-V ISA Specification Snippet
                ↓
    Stage 1: OpenAI Extractor
                ↓
      Candidate Parameters
                ↓
    Stage 2: OpenAI Verifier
                ↓
      Validated Parameters
                ↓
    Pydantic Schema Validation
                ↓
           results.yaml
```

### Pipeline Flow

1. **Stage 1 — Extractor**: Passes the RISC-V specification snippet to `gpt-4o-mini` with `REFINED_EXTRACTOR_PROMPT`. The model identifies candidate implementation-variable parameters, outputting structured Pydantic objects containing parameter names, descriptions, variability types, and explicit constraints.
2. **Stage 2 — Verifier (Hallucination Control)**: Passes the original snippet together with Stage 1's candidate parameters to `gpt-4o-mini` with `VERIFIER_PROMPT`. The verifier independently audits each candidate against strict variability and textual grounding rules, pruning unsupported extractions or false positives.
3. **Pydantic Validation & YAML Serialization**: The verified `ParameterList` object is validated in Python and serialized directly into standard YAML (`results.yaml`). The generated YAML string is validated using `yaml.safe_load()` prior to saving.

---

## 4. Prompt Development and Refinement

### Initial Approach

The initial baseline prompt (`INITIAL_EXTRACTOR_PROMPT`) relied primarily on keyword matching, instructing the LLM to search for indicator words such as *“may”*, *“optional”*, *“implementation-defined”*, and *“implementation-specific”*.

**Design Risk**: A keyword-driven approach can produce false positives. Technical specifications frequently contain numeric constants, bit allocations, and descriptive architectural rules (e.g., *"sets aside a 12-bit encoding space for up to 4,096 CSRs"*). Under a simple keyword prompt, an LLM might misclassify invariant specification rules as configurable parameters.

### Refined Extraction Prompt

The prompt was refined (`REFINED_EXTRACTOR_PROMPT`) to explicitly define what constitutes an architectural parameter versus a fixed specification rule:
- **Variable vs. Fixed**: Explicitly mandates that fixed ISA constants, bit-field allocations, and mandatory rules are NOT parameters.
- **Strict Grounding**: Forbids the model from using external RISC-V knowledge or inferring unstated parameters.
- **Explicit Field Specifications**: Enforces machine-readable `snake_case` names, accurate descriptions, variability types, and explicit textual constraints.
- **Empty List Instruction**: Instructs the model to return an empty parameter list (`[]`) when a snippet contains only invariant specification facts.

### Verification / Hallucination Control

To reduce hallucinations and unsupported inferences, a second LLM verification stage (`VERIFIER_PROMPT`) was introduced. The verifier audits each candidate against four criteria:
1. **Variability Check**: Confirms the candidate represents a true implementation choice.
2. **Grounding Check**: Verifies direct textual proof for the parameter and its constraints.
3. **Redundancy Check**: Merges or removes duplicate candidates.
4. **No Additions**: Prevents the verifier from introducing new parameters.

**Safeguards**:
- **Controlled Temperature**: Set to `0.0` to favor consistent extraction.
- **Schema Enforcement**: Pydantic schema validation (`ParameterList`).
- **YAML Validation**: Pre-save verification via `yaml.safe_load()`.

---

## 5. Prompts Used

The exact prompt templates from `prompts.py` are presented below:

### 5.1 Initial Extractor Prompt

```python
INITIAL_EXTRACTOR_PROMPT = """
You are an expert hardware engineer analyzing RISC-V specification snippets.

Extract all architectural parameters from the following snippet.
Look for keywords such as: 'may', 'might', 'should', 'optional', 'optionally', 'implementation-defined', 'implementation-specific'.

Return a list of parameters with name, description, type, and constraints.

Snippet:
{snippet}
"""
```

### 5.2 Refined Extractor Prompt

```python
REFINED_EXTRACTOR_PROMPT = """
You are a RISC-V hardware architecture specialist tasked with extracting implementation-variable parameters from specification text.

CRITICAL DISTINCTION:
- AN ARCHITECTURAL PARAMETER is a property, size, capacity, organization, presence, or behavior that MAY VARY between different conforming hardware implementations of the RISC-V specification.
- FIXED ISA CONSTANTS, standard encoding rules, bit field allocations, or mandatory specifications ARE NOT parameters. Do NOT extract them.

EXTRACTOR RULES:
1. Grounding: Every parameter MUST be explicitly supported by text in the snippet. Do NOT invent or infer external parameters.
2. Indicator Words: Words like 'implementation-specific', 'implementation-defined', 'optional', 'may', 'might', 'should' indicate potential variability, but you MUST confirm the text describes a variable choice.
3. Fixed Rules Excluded: Fixed values (e.g. 12-bit address space, top 2 bits encoding read/write) are non-variable ISA rules and MUST NOT be extracted as parameters.
4. Parameter Fields:
   - name: Concise, machine-readable snake_case identifier (e.g. cache_block_size, cache_capacity).
   - description: Clear explanation of what this parameter configures based on the snippet.
   - type: Category of variability indicated in text (e.g. 'implementation-specific', 'optional', 'implementation-defined').
   - constraints: List of any explicit requirements or constraints mentioned in the snippet (e.g. 'Must be power-of-two (NAPOT)', 'Shall be uniform throughout system in initial CMO extensions').
5. Empty Extraction: If the snippet contains NO implementation-variable parameters (only fixed ISA facts), return an empty parameter list.

RISC-V Specification Snippet:
{snippet}
"""
```

### 5.3 Verification Prompt

```python
VERIFIER_PROMPT = """
You are a rigorous formal verification engineer reviewing extracted RISC-V architectural parameters for accuracy and hallucination prevention.

Your task is to independently audit each candidate parameter extracted from the RISC-V specification snippet.

AUDIT CRITERIA:
1. Variability Check: Is this item actually variable between implementations? (If it is a fixed specification constant, rule, or field allocation, REMOVE IT).
2. Grounding Check: Is there direct textual proof in the snippet for this parameter and all its claimed constraints? (If anything was assumed or brought in from outside knowledge, REMOVE IT).
3. Redundancy Check: Are multiple candidates describing the exact same underlying parameter? (Merge or remove duplicates).
4. No Additions: Do NOT invent new parameters. Only validate or filter out the provided candidates.

Snippet:
{snippet}

Candidate Parameters to Audit:
{candidates_json}

Return ONLY the verified list of parameters that strictly pass all audit criteria. If no candidate passes, return an empty parameter list.
"""
```

---

## 6. Results

Below is the exact `results.yaml` output generated by executing `main.py` against the primary evaluation snippets:

```yaml
results:
  - source: Privileged Spec 19.3.1
    parameters:
      - name: cache_capacity
        description:
          The total amount of data that can be stored in the cache, which may
          vary between implementations.
        type: implementation-specific
        constraints: []
      - name: cache_organization
        description:
          The structure and arrangement of the cache, which is implementation-specific
          and can differ across systems.
        type: implementation-specific
        constraints: []
      - name: cache_block_size
        description:
          The size of each cache block, which is implementation-specific but
          must be uniform throughout the system in the initial CMO extensions.
        type: implementation-specific
        constraints:
          - Shall be uniform throughout system in initial CMO extensions
  - source: Privileged Spec 2.1
    parameters: []
```

---

## 7. Observations

- **Privileged Spec 19.3.1**: The pipeline successfully extracted three implementation-specific parameters: `cache_capacity`, `cache_organization`, and `cache_block_size`. It also captured the explicit constraint on `cache_block_size` (*“Shall be uniform throughout system in initial CMO extensions”*).
- **Privileged Spec 2.1**: The pipeline returned an empty list (`parameters: []`). Although the text contains numeric values and architectural details (e.g., *12-bit encoding space*, *4,096 CSRs*, *top two bits*), these represent fixed ISA rules rather than implementation-variable choices. Returning an empty list demonstrates that the pipeline distinguishes fixed architectural facts from configurable parameters on the supplied challenge snippets.

---

## 8. Reproducibility

To execute the pipeline and reproduce `results.yaml`:

1. **Clone Repository**:
   ```bash
   git clone https://github.com/dhruvil-codes/riscv-parameter-extractor.git
   cd riscv-parameter-extractor
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Copy `.env.example` to `.env` and set your API key:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o-mini
   ```

4. **Run Pipeline**:
   ```bash
   python main.py
   ```

5. **Inspect Output**:
   Check the generated `results.yaml`.

---

## 9. Source Code & Repository Structure

**GitHub Repository**: [https://github.com/dhruvil-codes/riscv-parameter-extractor](https://github.com/dhruvil-codes/riscv-parameter-extractor)

**Repository Contents**:
- `main.py`: CLI entrypoint executing the two-stage extraction and verification pipeline.
- `prompts.py`: Prompt definitions (`INITIAL_EXTRACTOR_PROMPT`, `REFINED_EXTRACTOR_PROMPT`, `VERIFIER_PROMPT`).
- `snippets.py`: Benchmark RISC-V specification snippets.
- `results.yaml`: Validated output YAML generated by the pipeline.
- `requirements.txt`: Project dependencies (`openai`, `pydantic`, `pyyaml`, `python-dotenv`).
- `.env.example`: Template for environment variables.
- `.gitignore`: Ensures secrets and virtual environments are not committed.
- `README.md`: Project documentation and execution instructions.
