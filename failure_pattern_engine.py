"""
theLitmus — Failure Pattern Engine (Layer B)
====================================================
Deterministic adjudication on CaseSchema.
No LLM. No probability. Same input = same output.

Phase 2 patterns:
  - FP-02: Unsupported Conclusion / Incomplete-Evidence Closure
  - FP-04: Narrative Acceptance Without Verification

Every flag is traceable to specific schema fields.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from case_schema import (
    CaseSchema, ConclusionStrength, EvidenceBaseStrength,
    CorroborationType, Outcome, CustomerType, EvidenceStatus,
    IndicatorSeverity,
)


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FailureFlag:
    """A detected failure pattern with full traceability."""
    pattern_id: str                     # e.g. "FP-02"
    pattern_name: str                   # Human-readable name
    severity: Severity
    trigger_fields: dict                # Which schema fields triggered this
    explanation_template: str           # Pre-written explanation (no LLM needed)
    defensibility_note: str             # Why this matters to a bank
    suppressed: bool = False            # Set by Layer C
    suppression_reason: str = ""        # Set by Layer C

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "severity": self.severity.value,
            "trigger_fields": self.trigger_fields,
            "explanation_template": self.explanation_template,
            "defensibility_note": self.defensibility_note,
            "suppressed": self.suppressed,
            "suppression_reason": self.suppression_reason,
        }


# ─── FP-02: Unsupported Conclusion ──────────────────────────────────

def detect_fp02_unsupported_conclusion(schema: CaseSchema) -> Optional[FailureFlag]:
    """
    FP-02: Unsupported Conclusion / Incomplete-Evidence Closure

    Rule:
        IF conclusion_strength in (strong, moderate)
        AND evidence_base_strength in (thin, absent)
        AND analytical_bridge_present = false
        AND outcome in (closed_no_action, approved, closed_downgraded)

    The decision outruns the evidence. The analyst reached a comfort
    conclusion that is not earned by the evidence base.
    """

    conclusion = schema.conclusion_strength_value
    evidence = schema.evidence_base_strength_value
    bridge = schema.analytical_bridge_present.value
    outcome = schema.outcome_value

    # ── Gate conditions ──
    # Conclusion must be at least moderate
    if conclusion not in (ConclusionStrength.STRONG_CLEAR, ConclusionStrength.MODERATE_QUALIFIED):
        return None

    # Evidence must be thin or absent
    if evidence not in (EvidenceBaseStrength.THIN, EvidenceBaseStrength.ABSENT):
        return None

    # No analytical bridge
    if bridge is True:
        return None

    # Outcome must be a closure/approval (not escalation or pending)
    closure_outcomes = (
        Outcome.CLOSED_NO_ACTION, Outcome.APPROVED,
        Outcome.CLOSED_DOWNGRADED,
    )
    if outcome not in closure_outcomes:
        return None

    # ── Severity gradation ──
    severity = _fp02_severity(schema)

    # ── Build trigger fields ──
    trigger_fields = {
        "conclusion_strength": schema.conclusion_strength.to_dict(),
        "evidence_base_strength": schema.evidence_base_strength.to_dict(),
        "analytical_bridge_present": schema.analytical_bridge_present.to_dict(),
        "outcome": schema.outcome.to_dict(),
    }

    # Add specific evidence gaps to triggers
    evidence_gaps = _identify_evidence_gaps(schema)
    if evidence_gaps:
        trigger_fields["evidence_gaps"] = evidence_gaps

    return FailureFlag(
        pattern_id="FP-02",
        pattern_name="Unsupported Conclusion",
        severity=severity,
        trigger_fields=trigger_fields,
        explanation_template=_fp02_explanation(schema, evidence_gaps),
        defensibility_note=(
            "The rationale reaches a comfort conclusion beyond what the documented "
            "evidence can sustain. This creates defensibility exposure: a regulator "
            "reviewing this file would ask what evidence supports the stated conclusion "
            "and find the answer insufficient."
        ),
    )


def _fp02_severity(schema: CaseSchema) -> Severity:
    """Calculate severity for FP-02 based on escalating factors."""

    severity_score = 0

    # Base: conclusion-evidence mismatch is at least MEDIUM
    severity_score = 2

    # Escalator: evidence is absent (not just thin)
    if schema.evidence_base_strength_value == EvidenceBaseStrength.ABSENT:
        severity_score += 1

    # Escalator: SOW absent on a closure
    if schema.sow_status in (EvidenceStatus.ABSENT, EvidenceStatus.GENERIC):
        severity_score += 1

    # Escalator: SOF absent on a closure
    if schema.sof_status in (EvidenceStatus.ABSENT, EvidenceStatus.GENERIC):
        severity_score += 1

    # Escalator: high-risk customer type with weak evidence
    if schema.customer_type_value in (
        CustomerType.CORPORATE, CustomerType.PEP,
        CustomerType.HIGH_RISK, CustomerType.CORRESPONDENT,
    ):
        severity_score += 1

    # Escalator: expected activity not defined
    if not schema.expected_activity_defined.value:
        severity_score += 1

    # Escalator: adverse media present but closure reached
    if schema.adverse_media_present.value and not schema.adverse_media_addressed.value:
        severity_score += 2

    # Escalator: multiple unaddressed indicators
    unaddressed = [i for i in schema.indicators if not i.addressed]
    if len(unaddressed) >= 2:
        severity_score += 1

    # Map to severity levels
    if severity_score >= 6:
        return Severity.CRITICAL
    elif severity_score >= 4:
        return Severity.HIGH
    elif severity_score >= 3:
        return Severity.MEDIUM
    else:
        return Severity.LOW


def _identify_evidence_gaps(schema: CaseSchema) -> list[str]:
    """Identify specific evidence gaps for FP-02 explanation."""
    gaps = []

    if schema.sow_status in (EvidenceStatus.ABSENT, EvidenceStatus.GENERIC):
        gaps.append("source of wealth not verified or generic")

    if schema.sof_status in (EvidenceStatus.ABSENT, EvidenceStatus.GENERIC):
        gaps.append("source of funds not verified or generic")

    if not schema.expected_activity_defined.value:
        gaps.append("expected activity not defined")

    if schema.adverse_media_present.value and not schema.adverse_media_addressed.value:
        gaps.append("adverse media present but not substantively addressed")

    unaddressed = [i for i in schema.indicators if not i.addressed]
    for ind in unaddressed:
        gaps.append(f"indicator '{ind.indicator_type}' ({ind.severity.value}) not addressed")

    return gaps


def _fp02_explanation(schema: CaseSchema, evidence_gaps: list[str]) -> str:
    """Generate pre-written explanation for FP-02."""

    conclusion_text = schema.conclusion_strength.supporting_text
    outcome_text = schema.outcome.supporting_text

    base = (
        f"The rationale concludes with a {schema.conclusion_strength_value.value} "
        f"assessment and a {schema.outcome_value.value} outcome, but the underlying "
        f"evidence base is {schema.evidence_base_strength_value.value}."
    )

    if not schema.analytical_bridge_present.value:
        base += (
            " No analytical reasoning connects the cited evidence to the stated conclusion."
        )

    if evidence_gaps:
        gaps_text = "; ".join(evidence_gaps)
        base += f" Specific gaps: {gaps_text}."

    return base


# ─── FP-04: Narrative Acceptance Without Verification ────────────────

def detect_fp04_narrative_acceptance(schema: CaseSchema) -> Optional[FailureFlag]:
    """
    FP-04: Narrative Acceptance Without Verification

    Rule:
        IF customer_explanation_present = true
        AND explanation_corroboration in (self_corroborating, none)
        AND outcome in (closed_no_action, approved, closed_downgraded)

    The analyst accepted a customer or third-party explanation
    without documented corroboration.
    """

    explanation_present = schema.customer_explanation_present.value
    corroboration = schema.corroboration_value
    outcome = schema.outcome_value

    # ── Gate conditions ──
    # Must have a customer explanation
    if not explanation_present:
        return None

    # Corroboration must be weak or absent
    if corroboration not in (CorroborationType.SELF_CORROBORATING, CorroborationType.NONE):
        return None

    # Outcome must be a closure/approval
    closure_outcomes = (
        Outcome.CLOSED_NO_ACTION, Outcome.APPROVED,
        Outcome.CLOSED_DOWNGRADED,
    )
    if outcome not in closure_outcomes:
        return None

    # ── Severity gradation ──
    severity = _fp04_severity(schema)

    # ── Build trigger fields ──
    trigger_fields = {
        "customer_explanation_present": schema.customer_explanation_present.to_dict(),
        "explanation_corroboration": schema.explanation_corroboration.to_dict(),
        "outcome": schema.outcome.to_dict(),
    }

    if schema.third_party_reassurance_present.value:
        trigger_fields["third_party_reassurance_present"] = (
            schema.third_party_reassurance_present.to_dict()
        )

    # Check for unresolved indicators alongside narrative
    unresolved = _unresolved_despite_narrative(schema)
    if unresolved:
        trigger_fields["unresolved_indicators_despite_narrative"] = unresolved

    return FailureFlag(
        pattern_id="FP-04",
        pattern_name="Narrative Acceptance Without Verification",
        severity=severity,
        trigger_fields=trigger_fields,
        explanation_template=_fp04_explanation(schema, unresolved),
        defensibility_note=(
            "A customer or third-party explanation was treated as risk-resolving "
            "without documented corroboration. Plausibility is not verification. "
            "A regulator would ask what independent steps were taken to confirm "
            "the explanation and find the answer absent."
        ),
    )


def _fp04_severity(schema: CaseSchema) -> Severity:
    """Calculate severity for FP-04 based on escalating factors."""

    severity_score = 2  # Base: unverified narrative closure is at least MEDIUM

    # Escalator: no corroboration at all (worse than self-corroborating)
    if schema.corroboration_value == CorroborationType.NONE:
        severity_score += 1

    # Escalator: third-party reassurance without independent check
    if schema.third_party_reassurance_present.value:
        severity_score += 1

    # Escalator: adverse media present but narrative overrides
    if schema.adverse_media_present.value:
        severity_score += 2

    # Escalator: high-risk customer type
    if schema.customer_type_value in (
        CustomerType.CORPORATE, CustomerType.PEP,
        CustomerType.HIGH_RISK, CustomerType.CORRESPONDENT,
    ):
        severity_score += 1

    # Escalator: explanation addresses only partial picture
    unresolved = _unresolved_despite_narrative(schema)
    if len(unresolved) >= 2:
        severity_score += 1

    # Escalator: strong conclusion on unverified narrative
    if schema.conclusion_strength_value == ConclusionStrength.STRONG_CLEAR:
        severity_score += 1

    if severity_score >= 6:
        return Severity.CRITICAL
    elif severity_score >= 4:
        return Severity.HIGH
    elif severity_score >= 3:
        return Severity.MEDIUM
    else:
        return Severity.LOW


def _unresolved_despite_narrative(schema: CaseSchema) -> list[str]:
    """Find indicators that remain unaddressed despite narrative being accepted."""
    return [
        f"{i.indicator_type} ({i.severity.value})"
        for i in schema.indicators
        if not i.addressed and i.severity in (IndicatorSeverity.MEDIUM, IndicatorSeverity.HIGH)
    ]


def _fp04_explanation(schema: CaseSchema, unresolved: list[str]) -> str:
    """Generate pre-written explanation for FP-04."""

    explanation_text = schema.customer_explanation_present.supporting_text
    corr = schema.corroboration_value.value

    base = (
        f"A customer explanation was documented and the case was "
        f"{schema.outcome_value.value}. However, the corroboration level "
        f"is '{corr}' — "
    )

    if corr == "none":
        base += "no verification of the explanation was documented."
    else:
        base += "the explanation is supported only by information the customer themselves provided."

    if schema.third_party_reassurance_present.value:
        base += (
            " A third-party reassurance was also present but without evidence of "
            "independent verification."
        )

    if unresolved:
        indicators_text = "; ".join(unresolved)
        base += (
            f" Additionally, the following indicators remain unresolved despite "
            f"the narrative being accepted: {indicators_text}."
        )

    return base


# ─── Cross-Pattern Interaction ────────────────────────────────────────

def _escalate_co_occurrence(flags: list[FailureFlag]) -> list[FailureFlag]:
    """
    If FP-02 and FP-04 co-occur, escalate the higher severity by one level.
    An unsupported conclusion PLUS unverified narrative acceptance is worse
    than either alone.
    """
    pattern_ids = {f.pattern_id for f in flags if not f.suppressed}

    if "FP-02" in pattern_ids and "FP-04" in pattern_ids:
        # Find the higher-severity flag and escalate
        severity_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        for flag in flags:
            if flag.pattern_id in ("FP-02", "FP-04") and not flag.suppressed:
                current_idx = severity_order.index(flag.severity)
                if current_idx < len(severity_order) - 1:
                    flag.severity = severity_order[current_idx + 1]
                    flag.trigger_fields["co_occurrence_escalation"] = (
                        "Severity escalated due to co-occurrence of FP-02 and FP-04"
                    )
                break  # Only escalate the first (highest) one

    return flags


# ─── Main Detection Entry Point ──────────────────────────────────────

def detect_failure_patterns(schema: CaseSchema) -> list[FailureFlag]:
    """
    Run all active failure pattern detectors against a CaseSchema.
    Returns list of FailureFlags (may be empty if no patterns detected).

    This is Layer B. Pure deterministic logic. No LLM.
    """

    flags: list[FailureFlag] = []

    # FP-02: Unsupported Conclusion
    fp02 = detect_fp02_unsupported_conclusion(schema)
    if fp02:
        flags.append(fp02)

    # FP-04: Narrative Acceptance
    fp04 = detect_fp04_narrative_acceptance(schema)
    if fp04:
        flags.append(fp04)

    # Cross-pattern severity escalation
    if len(flags) > 1:
        flags = _escalate_co_occurrence(flags)

    return flags
