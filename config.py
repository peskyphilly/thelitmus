"""
theLitmus — Configuration
==================================
Central config. Switch providers, toggle modes, set keys.
"""

import os

# ─── LLM Provider ────────────────────────────────────────────────────
# Options: "claude", "openai", "ollama"
LLM_PROVIDER = os.environ.get("LITMUS_LLM_PROVIDER", "claude")

# Model override (defaults handled by provider classes)
LLM_MODEL = os.environ.get("LITMUS_LLM_MODEL", "")

# API Keys (set via environment or Streamlit secrets)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Ollama
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# ─── Detection Mode ──────────────────────────────────────────────────
# "schema": Full schema-first pipeline (Layer A → B → C)
# "regex":  Phase 1.5 regex fallback (no LLM required)
# "hybrid": Schema-first with regex as backup on extraction failure
DETECTION_MODE = os.environ.get("LITMUS_DETECTION_MODE", "schema")

# ─── Suppression ─────────────────────────────────────────────────────
# Whether suppression layer (Layer C) is active
# Should always be True in production. False only for debugging.
SUPPRESSION_ENABLED = os.environ.get("LITMUS_SUPPRESSION", "true").lower() == "true"

# ─── Audit Logging ───────────────────────────────────────────────────
AUDIT_LOG_PATH = os.environ.get("LITMUS_AUDIT_LOG", "litmus_audit.jsonl")

# ─── Active Patterns ─────────────────────────────────────────────────
# Which failure patterns are active. Add pattern IDs as they are built.
ACTIVE_PATTERNS = ["FP-02", "FP-04"]
