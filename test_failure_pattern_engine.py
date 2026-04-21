"""
theLitmus — Failure Pattern Engine Tests
=================================================
Deterministic tests: given a CaseSchema, assert exact flags and severity.
No LLM needed. These test Layer B in isolation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from case_schema import (
    CaseSchema, SchemaField, RiskIndicator,
    CaseType, CustomerType, Outcome, EvidenceStatus,
    CorroborationType, ConclusionStrength, EvidenceBaseStrength,
    IndicatorSeverity,
)
from failure_pattern_engine import (
    detect_fp02_unsupported_conclusion,
    detect_fp04_narrative_acceptance,
    detect_failure_patterns,
    Severity,
)


def _sf(value, text="test"):
    """Shorthand for SchemaField creation in tests."""
    return SchemaField(value=value, supporting_text=text)


def _indicator(itype, severity, addressed=False):
    """Shorthand for RiskIndicator creation in tests."""
    return RiskIndicator(
        indicator_type=itype,
        severity=IndicatorSeverity(severity),
        addressed=addressed,
        supporting_text="test indicator",
    )


def _base_schema(**overrides) -> CaseSchema:
    """
    Build a base CaseSchema with sensible defaults.
    Override specific fields via kwargs.
    """
    defaults = dict(
        case_type=_sf(CaseType.ALERT_REVIEW),
        customer_type=_sf(CustomerType.RETAIL),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
        indicators=[],
        indicator_count_medium_high=0,
        adverse_media_present=_sf(False),
        adverse_media_addressed=_sf(False),
        source_of_wealth_status=_sf(EvidenceStatus.ABSENT),
        source_of_funds_status=_sf(EvidenceStatus.ABSENT),
        expected_activity_defined=_sf(False),
        customer_explanation_present=_sf(False),
        explanation_corroboration=_sf(CorroborationType.NONE),
        third_party_reassurance_present=_sf(False),
        conclusion_strength=_sf(ConclusionStrength.ABSENT),
        evidence_base_strength=_sf(EvidenceBaseStrength.ABSENT),
        analytical_bridge_present=_sf(False),
        cumulative_inference_present=_sf(False),
        escalation_considered=_sf(False),
        non_escalation_reasoning_explicit=_sf(False),
    )
    defaults.update(overrides)

    # Recalculate medium/high count from indicators
    indicators = defaults.get("indicators", [])
    defaults["indicator_count_medium_high"] = sum(
        1 for i in indicators
        if i.severity in (IndicatorSeverity.MEDIUM, IndicatorSeverity.HIGH)
    )

    return CaseSchema(**defaults)


# ══════════════════════════════════════════════════════════════════════
# FP-02: UNSUPPORTED CONCLUSION TESTS
# ══════════════════════════════════════════════════════════════════════

def test_fp02_triggers_on_strong_conclusion_thin_evidence():
    """Classic FP-02: strong conclusion, thin evidence, no bridge, closure."""
    schema = _base_schema(
        conclusion_strength=_sf(ConclusionStrength.STRONG_CLEAR),
        evidence_base_strength=_sf(EvidenceBaseStrength.THIN),
        analytical_bridge_present=_sf(False),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
    )
    flag = detect_fp02_unsupported_conclusion(schema)
    assert flag is not None, "FP-02 should trigger"
    assert flag.pattern_id == "FP-02"
    print("PASS: test_fp02_triggers_on_strong_conclusion_thin_evidence")


def test_fp02_triggers_on_moderate_conclusion_absent_evidence():
    """FP-02 triggers on moderate conclusion with absent evidence."""
    schema = _base_schema(
        conclusion_strength=_sf(ConclusionStrength.MODERATE_QUALIFIED),
        evidence_base_strength=_sf(EvidenceBaseStrength.ABSENT),
        analytical_bridge_present=_sf(False),
        outcome=_sf(Outcome.APPROVED),
    )
    flag = detect_fp02_unsupported_conclusion(schema)
    assert flag is not None, "FP-02 should trigger"
    print("PASS: test_fp02_triggers_on_moderate_conclusion_absent_evidence")


def test_fp02_does_not_trigger_with_analytical_bridge():
    """FP-02 should NOT trigger if analytical bridge is present."""
    schema = _base_schema(
        conclusion_strength=_sf(ConclusionStrength.STRONG_CLEAR),
        evidence_base_strength=_sf(EvidenceBaseStrength.THIN),
        analytical_bridge_present=_sf(True),  # Bridge present
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
    )
    flag = detect_fp02_unsupported_conclusion(schema)
    assert flag is None, "FP-02 should NOT trigger when bridge is present"
    print("PASS: test_fp02_does_not_trigger_with_analytical_bridge")


def test_fp02_does_not_trigger_with_strong_evidence():
    """FP-02 should NOT trigger if evidence is comprehensive."""
    schema = _base_schema(
        conclusion_strength=_sf(ConclusionStrength.STRONG_CLEAR),
        evidence_base_strength=_sf(EvidenceBaseStrength.COMPREHENSIVE),
        analytical_bridge_present=_sf(False),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
    )
    flag = detect_fp02_unsupported_conclusion(schema)
    assert flag is None, "FP-02 should NOT trigger with strong evidence"
    print("PASS: test_fp02_does_not_trigger_with_strong_evidence")


def test_fp02_does_not_trigger_on_escalation():
    """FP-02 should NOT trigger if outcome is escalation."""
    schema = _base_schema(
        conclusion_strength=_sf(ConclusionStrength.STRONG_CLEAR),
        evidence_base_strength=_sf(EvidenceBaseStrength.THIN),
        analytical_bridge_present=_sf(False),
        outcome=_sf(Outcome.ESCALATED),
    )
    flag = detect_fp02_unsupported_conclusion(schema)
    assert flag is None, "FP-02 should NOT trigger on escalation"
    print("PASS: test_fp02_does_not_trigger_on_escalation")


def test_fp02_does_not_trigger_on_weak_conclusion():
    """FP-02 should NOT trigger on weak/absent conclusion."""
    schema = _base_schema(
        conclusion_strength=_sf(ConclusionStrength.WEAK_COMFORT),
        evidence_base_strength=_sf(EvidenceBaseStrength.THIN),
        analytical_bridge_present=_sf(False),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
    )
    flag = detect_fp02_unsupported_conclusion(schema)
    assert flag is None, "FP-02 should NOT trigger on weak conclusion"
    print("PASS: test_fp02_does_not_trigger_on_weak_conclusion")


def test_fp02_severity_escalates_with_adverse_media():
    """Severity should escalate when adverse media is present but unaddressed."""
    schema = _base_schema(
        conclusion_strength=_sf(ConclusionStrength.STRONG_CLEAR),
        evidence_base_strength=_sf(EvidenceBaseStrength.ABSENT),
        analytical_bridge_present=_sf(False),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
        adverse_media_present=_sf(True),
        adverse_media_addressed=_sf(False),
        customer_type=_sf(CustomerType.CORPORATE),
    )
    flag = detect_fp02_unsupported_conclusion(schema)
    assert flag is not None
    assert flag.severity in (Severity.HIGH, Severity.CRITICAL), \
        f"Severity should be HIGH or CRITICAL, got {flag.severity}"
    print("PASS: test_fp02_severity_escalates_with_adverse_media")


def test_fp02_severity_escalates_with_high_risk_customer():
    """Severity should escalate for PEP/high-risk customers."""
    schema = _base_schema(
        conclusion_strength=_sf(ConclusionStrength.STRONG_CLEAR),
        evidence_base_strength=_sf(EvidenceBaseStrength.THIN),
        analytical_bridge_present=_sf(False),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
        customer_type=_sf(CustomerType.PEP),
    )
    flag = detect_fp02_unsupported_conclusion(schema)
    assert flag is not None
    assert flag.severity in (Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL), \
        f"Severity should be at least MEDIUM for PEP, got {flag.severity}"
    print("PASS: test_fp02_severity_escalates_with_high_risk_customer")


# ══════════════════════════════════════════════════════════════════════
# FP-04: NARRATIVE ACCEPTANCE TESTS
# ══════════════════════════════════════════════════════════════════════

def test_fp04_triggers_on_unverified_narrative_closure():
    """Classic FP-04: explanation present, no corroboration, case closed."""
    schema = _base_schema(
        customer_explanation_present=_sf(True),
        explanation_corroboration=_sf(CorroborationType.NONE),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
    )
    flag = detect_fp04_narrative_acceptance(schema)
    assert flag is not None, "FP-04 should trigger"
    assert flag.pattern_id == "FP-04"
    print("PASS: test_fp04_triggers_on_unverified_narrative_closure")


def test_fp04_triggers_on_self_corroborating_explanation():
    """FP-04 triggers when explanation is self-corroborating only."""
    schema = _base_schema(
        customer_explanation_present=_sf(True),
        explanation_corroboration=_sf(CorroborationType.SELF_CORROBORATING),
        outcome=_sf(Outcome.APPROVED),
    )
    flag = detect_fp04_narrative_acceptance(schema)
    assert flag is not None, "FP-04 should trigger on self-corroborating"
    print("PASS: test_fp04_triggers_on_self_corroborating_explanation")


def test_fp04_does_not_trigger_with_independent_corroboration():
    """FP-04 should NOT trigger with independent documentary corroboration."""
    schema = _base_schema(
        customer_explanation_present=_sf(True),
        explanation_corroboration=_sf(CorroborationType.INDEPENDENT_DOCUMENTARY),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
    )
    flag = detect_fp04_narrative_acceptance(schema)
    assert flag is None, "FP-04 should NOT trigger with independent corroboration"
    print("PASS: test_fp04_does_not_trigger_with_independent_corroboration")


def test_fp04_does_not_trigger_with_internal_verbal():
    """FP-04 should NOT trigger with internal verbal corroboration."""
    schema = _base_schema(
        customer_explanation_present=_sf(True),
        explanation_corroboration=_sf(CorroborationType.INTERNAL_VERBAL),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
    )
    flag = detect_fp04_narrative_acceptance(schema)
    assert flag is None, "FP-04 should NOT trigger with internal verbal"
    print("PASS: test_fp04_does_not_trigger_with_internal_verbal")


def test_fp04_does_not_trigger_without_explanation():
    """FP-04 should NOT trigger if no customer explanation present."""
    schema = _base_schema(
        customer_explanation_present=_sf(False),
        explanation_corroboration=_sf(CorroborationType.NONE),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
    )
    flag = detect_fp04_narrative_acceptance(schema)
    assert flag is None, "FP-04 should NOT trigger without explanation"
    print("PASS: test_fp04_does_not_trigger_without_explanation")


def test_fp04_does_not_trigger_on_escalation():
    """FP-04 should NOT trigger if outcome is escalation."""
    schema = _base_schema(
        customer_explanation_present=_sf(True),
        explanation_corroboration=_sf(CorroborationType.NONE),
        outcome=_sf(Outcome.ESCALATED),
    )
    flag = detect_fp04_narrative_acceptance(schema)
    assert flag is None, "FP-04 should NOT trigger on escalation"
    print("PASS: test_fp04_does_not_trigger_on_escalation")


def test_fp04_severity_escalates_with_adverse_media():
    """Severity escalates when adverse media is present and narrative overrides."""
    schema = _base_schema(
        customer_explanation_present=_sf(True),
        explanation_corroboration=_sf(CorroborationType.NONE),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
        adverse_media_present=_sf(True),
        customer_type=_sf(CustomerType.CORPORATE),
    )
    flag = detect_fp04_narrative_acceptance(schema)
    assert flag is not None
    assert flag.severity in (Severity.HIGH, Severity.CRITICAL), \
        f"Severity should be HIGH or CRITICAL, got {flag.severity}"
    print("PASS: test_fp04_severity_escalates_with_adverse_media")


def test_fp04_severity_escalates_with_third_party():
    """Severity escalates with third-party reassurance and no independent check."""
    schema = _base_schema(
        customer_explanation_present=_sf(True),
        explanation_corroboration=_sf(CorroborationType.NONE),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
        third_party_reassurance_present=_sf(True),
    )
    flag = detect_fp04_narrative_acceptance(schema)
    assert flag is not None
    assert flag.severity in (Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL), \
        f"Severity should be at least MEDIUM, got {flag.severity}"
    print("PASS: test_fp04_severity_escalates_with_third_party")


# ══════════════════════════════════════════════════════════════════════
# CROSS-PATTERN TESTS
# ══════════════════════════════════════════════════════════════════════

def test_co_occurrence_escalates_severity():
    """When FP-02 and FP-04 co-occur, highest severity should escalate."""
    schema = _base_schema(
        # FP-02 triggers
        conclusion_strength=_sf(ConclusionStrength.STRONG_CLEAR),
        evidence_base_strength=_sf(EvidenceBaseStrength.THIN),
        analytical_bridge_present=_sf(False),
        # FP-04 triggers
        customer_explanation_present=_sf(True),
        explanation_corroboration=_sf(CorroborationType.NONE),
        # Shared
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
    )
    flags = detect_failure_patterns(schema)
    assert len(flags) == 2, f"Should detect 2 patterns, got {len(flags)}"

    # Check that at least one was escalated
    has_escalation_note = any(
        "co_occurrence_escalation" in f.trigger_fields for f in flags
    )
    assert has_escalation_note, "Co-occurrence should escalate severity"
    print("PASS: test_co_occurrence_escalates_severity")


def test_clean_rationale_no_flags():
    """A well-structured rationale should produce no flags."""
    schema = _base_schema(
        conclusion_strength=_sf(ConclusionStrength.MODERATE_QUALIFIED),
        evidence_base_strength=_sf(EvidenceBaseStrength.COMPREHENSIVE),
        analytical_bridge_present=_sf(True),
        customer_explanation_present=_sf(True),
        explanation_corroboration=_sf(CorroborationType.INDEPENDENT_DOCUMENTARY),
        outcome=_sf(Outcome.CLOSED_NO_ACTION),
        source_of_wealth_status=_sf(EvidenceStatus.VERIFIED_DOCUMENTARY),
        source_of_funds_status=_sf(EvidenceStatus.VERIFIED_DOCUMENTARY),
        expected_activity_defined=_sf(True),
    )
    flags = detect_failure_patterns(schema)
    assert len(flags) == 0, f"Clean rationale should produce no flags, got {len(flags)}"
    print("PASS: test_clean_rationale_no_flags")


def test_escalated_outcome_no_flags():
    """Escalated cases should not trigger either pattern."""
    schema = _base_schema(
        conclusion_strength=_sf(ConclusionStrength.STRONG_CLEAR),
        evidence_base_strength=_sf(EvidenceBaseStrength.THIN),
        analytical_bridge_present=_sf(False),
        customer_explanation_present=_sf(True),
        explanation_corroboration=_sf(CorroborationType.NONE),
        outcome=_sf(Outcome.ESCALATED),
    )
    flags = detect_failure_patterns(schema)
    assert len(flags) == 0, f"Escalated cases should not flag, got {len(flags)}"
    print("PASS: test_escalated_outcome_no_flags")


# ══════════════════════════════════════════════════════════════════════
# RUN ALL TESTS
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    tests = [
        # FP-02 positive
        test_fp02_triggers_on_strong_conclusion_thin_evidence,
        test_fp02_triggers_on_moderate_conclusion_absent_evidence,
        test_fp02_severity_escalates_with_adverse_media,
        test_fp02_severity_escalates_with_high_risk_customer,
        # FP-02 negative
        test_fp02_does_not_trigger_with_analytical_bridge,
        test_fp02_does_not_trigger_with_strong_evidence,
        test_fp02_does_not_trigger_on_escalation,
        test_fp02_does_not_trigger_on_weak_conclusion,
        # FP-04 positive
        test_fp04_triggers_on_unverified_narrative_closure,
        test_fp04_triggers_on_self_corroborating_explanation,
        test_fp04_severity_escalates_with_adverse_media,
        test_fp04_severity_escalates_with_third_party,
        # FP-04 negative
        test_fp04_does_not_trigger_with_independent_corroboration,
        test_fp04_does_not_trigger_with_internal_verbal,
        test_fp04_does_not_trigger_without_explanation,
        test_fp04_does_not_trigger_on_escalation,
        # Cross-pattern
        test_co_occurrence_escalates_severity,
        test_clean_rationale_no_flags,
        test_escalated_outcome_no_flags,
    ]

    passed = 0
    failed = 0
    errors = []

    print("=" * 60)
    print("THELITMUS — FAILURE PATTERN ENGINE TESTS")
    print("=" * 60)
    print()

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"FAIL: {test_fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"ERROR: {test_fn.__name__}: {e}")

    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    if errors:
        print("\nFailed tests:")
        for name, err in errors:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print("\nAll tests passed.")
        sys.exit(0)
