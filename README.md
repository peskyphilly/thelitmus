# theLitmus

**Reasoning Integrity Auditor for Financial Crime Compliance**

theLitmus extracts the reasoning structure of AML/KYC case rationales into a typed schema, then runs deterministic failure-pattern rules against that schema. The LLM never decides whether a failure occurred.

## Architecture

```
Layer A: Constrained Extraction (LLM → typed schema)
         ↓
Layer B: Deterministic Adjudication (schema → failure flags)
         ↓
Layer C: Contextual Suppression (flags → refined findings)
```

## Active Patterns

- **FP-02: Unsupported Conclusion** — The decision outruns the evidence
- **FP-04: Narrative Acceptance** — Customer explanation accepted without corroboration

## Quick Start

```bash
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY="your-key-here"
python3 -m streamlit run crucible_app.py
```

## Run Tests

```bash
python3 test_failure_pattern_engine.py
```

19 deterministic tests covering both patterns, severity escalation, cross-pattern interaction, and negative cases.

## File Structure

| File | Purpose |
|------|---------|
| `case_schema.py` | 19-field typed schema with evidence traceability |
| `llm_provider.py` | Provider abstraction (Claude / OpenAI / Ollama) |
| `schema_extractor.py` | Layer A: constrained LLM extraction |
| `failure_pattern_engine.py` | Layer B: deterministic rules (FP-02 + FP-04) |
| `suppression_engine.py` | Layer C: contextual suppression |
| `litmus.py` | Full pipeline orchestrator |
| `crucible_app.py` | Streamlit UI |
| `config.py` | Central configuration |
| `test_corpus/` | 16 synthetic rationales for validation |

## Switch LLM Provider

```bash
export LITMUS_LLM_PROVIDER=openai
export OPENAI_API_KEY="your-key"
```

Or in the Streamlit sidebar.

## Evidence Base

Built on £265M+ in FCA enforcement actions across Nationwide, Barclays, Mako, Coinbase, Monzo, and Dinosaur Merchant Bank.
