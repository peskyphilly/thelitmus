"""
theLitmus — CaseSchema
==============================
Typed ontology for analyst rationale extraction.
19 fields. Every field populated by Layer A (LLM extraction).
Layer B (deterministic rules) adjudicates only on these fields.

Design principles:
  - Lean: enough to power FP-02 + FP-04, extensible for FP-01/FP-05 later
  - Traceable: every field carries a supporting quote or explicit "not present"
  - Typed: enums, bools, structured lists — no free text in the schema itself
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─── Enums ───────────────────────────────────────────────────────────

class CaseType(str, Enum):
    ONBOARDING = "onboarding"
    REFRESH = "refresh"
    ALERT_REVIEW = "alert_review"
    SAR_DECISION = "sar_decision"
    PERIODIC_REVIEW = "periodic_review"
    UNKNOWN = "unknown"


class CustomerType(str, Enum):
    RETAIL = "retail"
    CORPORATE = "corporate"
    PEP = "pep"
    HIGH_RISK = "high_risk"
    CORRESPONDENT = "correspondent"
    UNKNOWN = "unknown"


class Outcome(str, Enum):
    CLOSED_NO_ACTION = "closed_no_action"
    CLOSED_DOWNGRADED = "closed_downgraded"
    ESCALATED = "escalated"
    SAR_FILED = "sar_filed"
    APPROVED = "approved"
    PENDING = "pending"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class EvidenceStatus(str, Enum):
    """Used for SOW, SOF, and similar evidential fields."""
    VERIFIED_DOCUMENTARY = "verified_documentary"
    VERIFIED_VERBAL = "verified_verbal"
    STATED_UNVERIFIED = "stated_unverified"
    ABSENT = "absent"
    GENERIC = "generic"


class CorroborationType(str, Enum):
    INDEPENDENT_DOCUMENTARY = "independent_documentary"
    INTERNAL_VERBAL = "internal_verbal"
    SELF_CORROBORATING = "self_corroborating"
    NONE = "none"


class ConclusionStrength(str, Enum):
    STRONG_CLEAR = "strong_clear"
    MODERATE_QUALIFIED = "moderate_qualified"
    WEAK_COMFORT = "weak_comfort"
    ABSENT = "absent"


class EvidenceBaseStrength(str, Enum):
    COMPREHENSIVE = "comprehensive"
    PARTIAL = "partial"
    THIN = "thin"
    ABSENT = "absent"


class IndicatorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ─── Supporting Dataclasses ──────────────────────────────────────────

@dataclass
class RiskIndicator:
    """A single risk indicator extracted from the rationale."""
    indicator_type: str          # e.g. "adverse_media", "unusual_transaction_pattern"
    severity: IndicatorSeverity
    addressed: bool              # Was this indicator substantively engaged in the rationale?
    supporting_text: str         # Quote from rationale, or "not present"

    def to_dict(self) -> dict:
        return {
            "indicator_type": self.indicator_type,
            "severity": self.severity.value,
            "addressed": self.addressed,
            "supporting_text": self.supporting_text,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RiskIndicator":
        try:
            severity = IndicatorSeverity(d["severity"])
        except (ValueError, KeyError):
            severity = IndicatorSeverity.LOW
        return cls(
            indicator_type=d.get("indicator_type", "unknown"),
            severity=severity,
            addressed=d.get("addressed", False),
            supporting_text=d.get("supporting_text", "not present"),
        )


@dataclass
class SchemaField:
    """Wrapper for any extracted field value + its supporting text."""
    value: object
    supporting_text: str  # Quote from rationale, or "not present"

    def to_dict(self) -> dict:
        v = self.value
        if isinstance(v, Enum):
            v = v.value
        return {"value": v, "supporting_text": self.supporting_text}


# ─── The CaseSchema ─────────────────────────────────────────────────

@dataclass
class CaseSchema:
    """
    Lean typed schema for analyst rationale extraction.
    19 fields. Every field carries evidence traceability.

    Fields 1-3:   Case context
    Fields 4-7:   Risk indicators
    Fields 8-10:  Evidence inventory
    Fields 11-13: Explanations & narratives
    Fields 14-16: Conclusion quality
    Fields 17-19: Synthesis & escalation (extensibility for FP-01/FP-05)
    """

    # ── Case Context ──
    case_type: SchemaField                    # 1. CaseType enum
    customer_type: SchemaField                # 2. CustomerType enum
    outcome: SchemaField                      # 3. Outcome enum

    # ── Risk Indicators ──
    indicators: list[RiskIndicator]           # 4. List of extracted indicators
    indicator_count_medium_high: int          # 5. Derived count
    adverse_media_present: SchemaField        # 6. bool
    adverse_media_addressed: SchemaField      # 7. bool

    # ── Evidence Inventory ──
    source_of_wealth_status: SchemaField      # 8. EvidenceStatus enum
    source_of_funds_status: SchemaField       # 9. EvidenceStatus enum
    expected_activity_defined: SchemaField    # 10. bool

    # ── Explanations & Narratives ──
    customer_explanation_present: SchemaField  # 11. bool
    explanation_corroboration: SchemaField     # 12. CorroborationType enum
    third_party_reassurance_present: SchemaField  # 13. bool

    # ── Conclusion Quality ──
    conclusion_strength: SchemaField          # 14. ConclusionStrength enum
    evidence_base_strength: SchemaField       # 15. EvidenceBaseStrength enum
    analytical_bridge_present: SchemaField    # 16. bool

    # ── Synthesis & Escalation (extensibility) ──
    cumulative_inference_present: SchemaField  # 17. bool (for FP-01)
    escalation_considered: SchemaField         # 18. bool (for FP-05)
    non_escalation_reasoning_explicit: SchemaField  # 19. bool (for FP-05)

    @property
    def outcome_value(self) -> Outcome:
        v = self.outcome.value
        if isinstance(v, Outcome):
            return v
        return Outcome(v)

    @property
    def conclusion_strength_value(self) -> ConclusionStrength:
        v = self.conclusion_strength.value
        if isinstance(v, ConclusionStrength):
            return v
        return ConclusionStrength(v)

    @property
    def evidence_base_strength_value(self) -> EvidenceBaseStrength:
        v = self.evidence_base_strength.value
        if isinstance(v, EvidenceBaseStrength):
            return v
        return EvidenceBaseStrength(v)

    @property
    def corroboration_value(self) -> CorroborationType:
        v = self.explanation_corroboration.value
        if isinstance(v, CorroborationType):
            return v
        return CorroborationType(v)

    @property
    def customer_type_value(self) -> CustomerType:
        v = self.customer_type.value
        if isinstance(v, CustomerType):
            return v
        return CustomerType(v)

    @property
    def sow_status(self) -> EvidenceStatus:
        v = self.source_of_wealth_status.value
        if isinstance(v, EvidenceStatus):
            return v
        return EvidenceStatus(v)

    @property
    def sof_status(self) -> EvidenceStatus:
        v = self.source_of_funds_status.value
        if isinstance(v, EvidenceStatus):
            return v
        return EvidenceStatus(v)

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output / audit logging."""
        return {
            "case_type": self.case_type.to_dict(),
            "customer_type": self.customer_type.to_dict(),
            "outcome": self.outcome.to_dict(),
            "indicators": [i.to_dict() for i in self.indicators],
            "indicator_count_medium_high": self.indicator_count_medium_high,
            "adverse_media_present": self.adverse_media_present.to_dict(),
            "adverse_media_addressed": self.adverse_media_addressed.to_dict(),
            "source_of_wealth_status": self.source_of_wealth_status.to_dict(),
            "source_of_funds_status": self.source_of_funds_status.to_dict(),
            "expected_activity_defined": self.expected_activity_defined.to_dict(),
            "customer_explanation_present": self.customer_explanation_present.to_dict(),
            "explanation_corroboration": self.explanation_corroboration.to_dict(),
            "third_party_reassurance_present": self.third_party_reassurance_present.to_dict(),
            "conclusion_strength": self.conclusion_strength.to_dict(),
            "evidence_base_strength": self.evidence_base_strength.to_dict(),
            "analytical_bridge_present": self.analytical_bridge_present.to_dict(),
            "cumulative_inference_present": self.cumulative_inference_present.to_dict(),
            "escalation_considered": self.escalation_considered.to_dict(),
            "non_escalation_reasoning_explicit": self.non_escalation_reasoning_explicit.to_dict(),
        }


# ─── Factory / Builder ───────────────────────────────────────────────

def build_schema(raw: dict) -> CaseSchema:
    """
    Build a CaseSchema from the raw JSON output of the LLM extraction.
    Validates types and provides defaults for missing fields.
    """

    def _sf(raw_field: dict | None, default_value=None, default_text="not present") -> SchemaField:
        """Parse a SchemaField from raw dict."""
        if raw_field is None:
            return SchemaField(value=default_value, supporting_text=default_text)
        if isinstance(raw_field, dict):
            return SchemaField(
                value=raw_field.get("value", default_value),
                supporting_text=raw_field.get("supporting_text", default_text),
            )
        # If it's a plain value (shouldn't happen with good extraction, but safety)
        return SchemaField(value=raw_field, supporting_text="extracted without traceability")

    def _enum_sf(raw_field: dict | None, enum_cls, default) -> SchemaField:
        """Parse a SchemaField with enum validation."""
        sf = _sf(raw_field, default_value=default.value)
        try:
            sf.value = enum_cls(sf.value)
        except (ValueError, KeyError):
            sf.value = default
        return sf

    def _bool_sf(raw_field: dict | None, default: bool = False) -> SchemaField:
        """Parse a SchemaField with bool validation."""
        sf = _sf(raw_field, default_value=default)
        if isinstance(sf.value, str):
            sf.value = sf.value.lower() in ("true", "yes", "1")
        sf.value = bool(sf.value)
        return sf

    # Parse indicators
    raw_indicators = raw.get("indicators", [])
    indicators = []
    for ri in raw_indicators:
        if isinstance(ri, dict):
            indicators.append(RiskIndicator.from_dict(ri))

    # Count medium/high
    medium_high_count = sum(
        1 for i in indicators
        if i.severity in (IndicatorSeverity.MEDIUM, IndicatorSeverity.HIGH)
    )

    return CaseSchema(
        # Context
        case_type=_enum_sf(raw.get("case_type"), CaseType, CaseType.UNKNOWN),
        customer_type=_enum_sf(raw.get("customer_type"), CustomerType, CustomerType.UNKNOWN),
        outcome=_enum_sf(raw.get("outcome"), Outcome, Outcome.UNKNOWN),

        # Indicators
        indicators=indicators,
        indicator_count_medium_high=medium_high_count,
        adverse_media_present=_bool_sf(raw.get("adverse_media_present")),
        adverse_media_addressed=_bool_sf(raw.get("adverse_media_addressed")),

        # Evidence
        source_of_wealth_status=_enum_sf(
            raw.get("source_of_wealth_status"), EvidenceStatus, EvidenceStatus.ABSENT
        ),
        source_of_funds_status=_enum_sf(
            raw.get("source_of_funds_status"), EvidenceStatus, EvidenceStatus.ABSENT
        ),
        expected_activity_defined=_bool_sf(raw.get("expected_activity_defined")),

        # Explanations
        customer_explanation_present=_bool_sf(raw.get("customer_explanation_present")),
        explanation_corroboration=_enum_sf(
            raw.get("explanation_corroboration"), CorroborationType, CorroborationType.NONE
        ),
        third_party_reassurance_present=_bool_sf(raw.get("third_party_reassurance_present")),

        # Conclusion
        conclusion_strength=_enum_sf(
            raw.get("conclusion_strength"), ConclusionStrength, ConclusionStrength.ABSENT
        ),
        evidence_base_strength=_enum_sf(
            raw.get("evidence_base_strength"), EvidenceBaseStrength, EvidenceBaseStrength.ABSENT
        ),
        analytical_bridge_present=_bool_sf(raw.get("analytical_bridge_present")),

        # Synthesis & Escalation
        cumulative_inference_present=_bool_sf(raw.get("cumulative_inference_present")),
        escalation_considered=_bool_sf(raw.get("escalation_considered")),
        non_escalation_reasoning_explicit=_bool_sf(raw.get("non_escalation_reasoning_explicit")),
    )
