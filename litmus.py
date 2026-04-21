"""
theLitmus — Main Pipeline
==================================
Ties all three layers together:
  Layer A (extraction) → Layer B (rules) → Layer C (suppression)

Usage:
    from litmus import analyze_rationale
    result = analyze_rationale(rationale_text)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import json
import time

from case_schema import CaseSchema
from schema_extractor import SchemaExtractor
from failure_pattern_engine import detect_failure_patterns, FailureFlag
from suppression_engine import run_suppression, get_retained_flags, get_suppressed_flags
from llm_provider import get_provider, LLMProvider, ClaudeProvider
import config


@dataclass
class LitmusResult:
    """Complete result from theLitmus analysis pipeline."""
    rationale: str
    schema: CaseSchema
    all_flags: list[FailureFlag]
    retained_flags: list[FailureFlag]
    suppressed_flags: list[FailureFlag]
    detection_mode: str
    provider_used: str
    extraction_time_ms: float
    detection_time_ms: float
    suppression_time_ms: float
    total_time_ms: float

    @property
    def flagged(self) -> bool:
        return len(self.retained_flags) > 0

    @property
    def flag_count(self) -> int:
        return len(self.retained_flags)

    @property
    def highest_severity(self) -> Optional[str]:
        if not self.retained_flags:
            return None
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        highest = max(
            self.retained_flags,
            key=lambda f: severity_order.get(f.severity.value, 0),
        )
        return highest.severity.value

    def to_dict(self) -> dict:
        return {
            "flagged": self.flagged,
            "flag_count": self.flag_count,
            "highest_severity": self.highest_severity,
            "detection_mode": self.detection_mode,
            "provider_used": self.provider_used,
            "timing": {
                "extraction_ms": round(self.extraction_time_ms, 1),
                "detection_ms": round(self.detection_time_ms, 1),
                "suppression_ms": round(self.suppression_time_ms, 1),
                "total_ms": round(self.total_time_ms, 1),
            },
            "retained_flags": [f.to_dict() for f in self.retained_flags],
            "suppressed_flags": [f.to_dict() for f in self.suppressed_flags],
            "schema": self.schema.to_dict(),
        }

    def summary(self) -> str:
        """Human-readable summary for CLI/UI output."""
        if not self.flagged:
            return (
                f"No material findings. "
                f"({len(self.suppressed_flags)} flag(s) considered and suppressed.) "
                f"[{self.total_time_ms:.0f}ms]"
            )

        lines = []
        lines.append(
            f"FLAGGED: {self.flag_count} finding(s) | "
            f"Highest severity: {self.highest_severity} | "
            f"[{self.total_time_ms:.0f}ms]"
        )
        for flag in self.retained_flags:
            lines.append(f"")
            lines.append(f"  [{flag.pattern_id}] {flag.pattern_name} ({flag.severity.value})")
            lines.append(f"  {flag.explanation_template}")
        if self.suppressed_flags:
            lines.append(f"")
            lines.append(
                f"  ({len(self.suppressed_flags)} additional flag(s) suppressed)"
            )
        return "\n".join(lines)


def _get_provider_from_config() -> LLMProvider:
    """Build a provider from config settings."""
    kwargs = {}
    if config.LLM_PROVIDER == "ollama":
        kwargs["base_url"] = config.OLLAMA_BASE_URL

    api_key = None
    if config.LLM_PROVIDER == "claude":
        api_key = config.ANTHROPIC_API_KEY
    elif config.LLM_PROVIDER == "openai":
        api_key = config.OPENAI_API_KEY

    model = config.LLM_MODEL if config.LLM_MODEL else None

    return get_provider(
        provider_name=config.LLM_PROVIDER,
        api_key=api_key,
        model=model,
        **kwargs,
    )


def analyze_rationale(
    rationale: str,
    metadata: dict | None = None,
    provider: LLMProvider | None = None,
) -> LitmusResult:
    """
    Full theLitmus analysis pipeline.

    Layer A: Extract rationale → CaseSchema (uses Haiku for speed)
    Layer B: Detect failure patterns (deterministic)
    Layer C: Suppress false positives + contextualise (uses Sonnet for tone)

    Args:
        rationale: Raw analyst rationale text
        metadata: Optional case metadata dict
        provider: Optional LLM provider (uses config default if not provided)

    Returns:
        LitmusResult with all findings, suppressions, and timing
    """
    if provider is None:
        provider = _get_provider_from_config()

    # Build a fast provider for extraction (Haiku) if using Claude
    extraction_provider = provider
    if isinstance(provider, ClaudeProvider):
        try:
            extraction_provider = ClaudeProvider(
                api_key=provider.api_key,
                model="claude-haiku-4-5-20251001",
                max_tokens=provider.max_tokens,
            )
        except Exception:
            extraction_provider = provider  # Fallback to default

    total_start = time.time()

    # ── Layer A: Extraction (Haiku — fast) ──
    t0 = time.time()
    extractor = SchemaExtractor(extraction_provider)
    schema = extractor.extract(rationale, metadata)
    extraction_time = (time.time() - t0) * 1000

    # ── Layer B: Deterministic Detection ──
    t1 = time.time()
    flags = detect_failure_patterns(schema)
    detection_time = (time.time() - t1) * 1000

    # ── Layer C: Suppression (Sonnet — better tone) ──
    suppression_time = 0.0
    if config.SUPPRESSION_ENABLED and flags:
        t2 = time.time()
        flags = run_suppression(flags, schema, rationale, provider)
        suppression_time = (time.time() - t2) * 1000

    total_time = (time.time() - total_start) * 1000

    return LitmusResult(
        rationale=rationale,
        schema=schema,
        all_flags=flags,
        retained_flags=get_retained_flags(flags),
        suppressed_flags=get_suppressed_flags(flags),
        detection_mode=config.DETECTION_MODE,
        provider_used=config.LLM_PROVIDER,
        extraction_time_ms=extraction_time,
        detection_time_ms=detection_time,
        suppression_time_ms=suppression_time,
        total_time_ms=total_time,
    )


# ─── Audit Logging ───────────────────────────────────────────────────

def log_result(result: LitmusResult) -> None:
    """Append result to audit log (JSONL)."""
    import datetime

    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "flagged": result.flagged,
        "flag_count": result.flag_count,
        "highest_severity": result.highest_severity,
        "detection_mode": result.detection_mode,
        "provider": result.provider_used,
        "timing_ms": round(result.total_time_ms, 1),
        "retained_flags": [f.to_dict() for f in result.retained_flags],
        "suppressed_flags": [
            {"pattern_id": f.pattern_id, "reason": f.suppression_reason}
            for f in result.suppressed_flags
        ],
    }

    with open(config.AUDIT_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
