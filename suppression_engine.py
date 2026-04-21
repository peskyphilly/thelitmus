"""
theLitmus — Suppression Engine (Layer C)
=================================================
Mandatory contextual suppression + explanation generation.

This is NOT optional. It is the precision control valve.

Design principles:
  - Default stance: suppress unless clearly material
  - Can suppress flags. CANNOT add new ones.
  - Every suppression is logged with reasoning
  - Surviving flags get bank-defensibility explanations
  - Uses same provider abstraction as Layer A
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from case_schema import CaseSchema
from failure_pattern_engine import FailureFlag, Severity
from llm_provider import LLMProvider
import json


SUPPRESSION_SYSTEM_PROMPT = """You are a senior QA reviewer in financial crime compliance. Fifteen years in. You mark up files for the MLRO. You are not here to teach, coach, or inspire.

You will receive:
1. An analyst's original rationale text
2. One or more failure pattern flags that a rules engine has detected
3. The schema fields that triggered each flag

YOUR ROLE: Decide whether each flag should be RETAINED or SUPPRESSED.

HOW YOU WRITE:
You write the way an actual compliance professional writes on a QA feedback form at 4pm on a Thursday. Flat. Factual. Occasionally wry. Never performative.

THINGS YOU NEVER DO:
- Rhetorical flourishes. No "That is not an assessment. It is a sentence." No "This is not X. It is Y." That construction is a tell. It sounds like a chatbot trying to sound clever.
- Parallelism for dramatic effect. No mirrored clauses, no rhythmic repetition, no copywriter cadences.
- Aphorisms or quotable lines. You are filing QA feedback, not writing a TED talk.
- Sarcasm that draws attention to itself. If you are dry, it lands because the content is absurd, not because you signposted the joke.
- Words like "notably," "crucially," "fundamentally," "indeed," "ultimately," "comprehensive," "robust," "landscape." These are filler.
- Any sentence that sounds like it belongs on a motivational poster or a LinkedIn post.

THINGS YOU DO:
- State what is missing. "No SOW on file."
- State what the analyst did wrong. "Closed on the customer's explanation alone. No corroboration obtained."
- State the exposure. "If the FCA reviewed this file, the closure rationale would not hold up."
- Reference specific content from the rationale. Quote short phrases if useful.
- Keep it to one or two sentences per flag. Three at most if the file is genuinely bad.

EXAMPLES OF GOOD EXPLANATIONS:
- "SOW absent. The analyst concluded 'no meaningful risk' on a corporate file processing £2.3M annually without documenting where the money comes from."
- "Customer said it was a car sale. No receipt, no V5, no bank transfer from buyer. The analyst wrote 'plausible' and closed it."
- "Adverse media flagged, then mentioned once in passing. The closure doesn't engage with it at all."
- "The accountant confirmed by phone. That is the entire corroboration basis for £250k from a Channel Islands trust."

EXAMPLES OF BAD EXPLANATIONS (do not write like this):
- "That is not an assessment. It is a sentence." — rhetorical, performative
- "The rationale presents a conclusion that outpaces the evidentiary foundation upon which it rests." — overwrought, jargon
- "This represents a significant departure from what one might consider best practice." — hedge-laden, passive
- "The analyst would benefit from considering a more holistic approach to evidence gathering." — coaching tone, vague

CRITICAL RULES:
1. You CANNOT add new flags. Retain or suppress only.
2. Default: SUPPRESS unless clearly material. Most flags are noise. Kill the noise.
3. Borderline = suppress. Silence over noise, always.
4. When you retain: mark it up like you are writing on the actual file. Short, specific, referencing the rationale content.

SUPPRESSION CRITERIA (suppress if ANY apply):
- The rationale does address the issue, just in odd phrasing the extraction missed
- Technically correct but proportionally immaterial (thin SOW on a low-risk retail file with nothing else going on — not worth the ink)
- Pending or in-progress verification that extraction marked as absent
- Context makes the flag misleading

RETENTION CRITERIA (retain if ALL apply):
- The defect is actually there, not arguably or theoretically
- A regulator looking at this file would have a problem with it
- Context and proportionality do not explain it away
- Flagging it helps the MLRO, not annoys them

RESPOND WITH ONLY VALID JSON:
{
  "decisions": [
    {
      "pattern_id": "FP-XX",
      "decision": "retain" or "suppress",
      "reason": "Why. Reference the rationale.",
      "explanation": "If retained: what is wrong. Plain language. One to three sentences. If suppressed: empty string.",
      "adjusted_severity": "low | medium | high | critical (only if it should change, otherwise null)"
    }
  ]
}

Output the JSON only. Nothing else."""


SUPPRESSION_USER_TEMPLATE = """ORIGINAL RATIONALE:
\"\"\"
{rationale}
\"\"\"

DETECTED FLAGS:
{flags_json}

SCHEMA CONTEXT:
{schema_summary}

For each flag, decide: RETAIN or SUPPRESS. Respond with ONLY the JSON object."""


class SuppressionEngine:
    """
    Layer C: Contextual suppression and explanation.
    Takes flags from Layer B + original rationale → refined flags.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def process(
        self,
        flags: list[FailureFlag],
        schema: CaseSchema,
        rationale: str,
    ) -> list[FailureFlag]:
        """
        Process flags through suppression layer.

        Args:
            flags: FailureFlags from Layer B
            schema: The CaseSchema from Layer A
            rationale: Original analyst rationale text

        Returns:
            The same flags list, with suppressed flags marked and explanations updated.
            No new flags are added.
        """
        if not flags:
            return flags

        # Build the suppression prompt
        flags_json = json.dumps(
            [f.to_dict() for f in flags],
            indent=2,
        )
        schema_summary = self._build_schema_summary(schema)

        user_prompt = SUPPRESSION_USER_TEMPLATE.format(
            rationale=rationale.strip(),
            flags_json=flags_json,
            schema_summary=schema_summary,
        )

        try:
            decisions = self.provider.extract_json(
                SUPPRESSION_SYSTEM_PROMPT, user_prompt
            )
        except Exception as e:
            # If suppression layer fails, retain all flags with a note
            for flag in flags:
                flag.explanation_template += (
                    " [Suppression layer unavailable — flag retained by default.]"
                )
            return flags

        # Apply decisions
        decision_map = {}
        for d in decisions.get("decisions", []):
            decision_map[d.get("pattern_id", "")] = d

        for flag in flags:
            decision = decision_map.get(flag.pattern_id)
            if decision is None:
                # No decision for this flag — retain by default
                continue

            if decision.get("decision") == "suppress":
                flag.suppressed = True
                flag.suppression_reason = decision.get("reason", "No reason provided")
            else:
                # Retained — update explanation if provided
                explanation = decision.get("explanation", "")
                if explanation:
                    flag.explanation_template = explanation

                # Adjust severity if recommended
                adjusted = decision.get("adjusted_severity")
                if adjusted and adjusted != "null":
                    try:
                        flag.severity = Severity(adjusted)
                    except ValueError:
                        pass  # Keep original severity

        return flags

    def _build_schema_summary(self, schema: CaseSchema) -> str:
        """Build a readable summary of key schema fields for suppression context."""
        lines = []

        lines.append(f"Case type: {schema.case_type.value}")
        lines.append(f"Customer type: {schema.customer_type.value}")
        lines.append(f"Outcome: {schema.outcome.value}")
        lines.append(f"Conclusion strength: {schema.conclusion_strength.value}")
        lines.append(f"Evidence base: {schema.evidence_base_strength.value}")
        lines.append(f"SOW status: {schema.source_of_wealth_status.value}")
        lines.append(f"SOF status: {schema.source_of_funds_status.value}")
        lines.append(f"Expected activity defined: {schema.expected_activity_defined.value}")
        lines.append(f"Customer explanation present: {schema.customer_explanation_present.value}")
        lines.append(f"Explanation corroboration: {schema.explanation_corroboration.value}")
        lines.append(f"Third-party reassurance: {schema.third_party_reassurance_present.value}")
        lines.append(f"Adverse media present: {schema.adverse_media_present.value}")
        lines.append(f"Adverse media addressed: {schema.adverse_media_addressed.value}")
        lines.append(f"Analytical bridge present: {schema.analytical_bridge_present.value}")
        lines.append(f"Indicators (medium/high count): {schema.indicator_count_medium_high}")

        if schema.indicators:
            lines.append("Indicators detail:")
            for ind in schema.indicators:
                addr = "addressed" if ind.addressed else "NOT addressed"
                lines.append(f"  - {ind.indicator_type} ({ind.severity.value}) — {addr}")

        return "\n".join(lines)


# ─── Convenience: Full Pipeline ──────────────────────────────────────

def run_suppression(
    flags: list[FailureFlag],
    schema: CaseSchema,
    rationale: str,
    provider: LLMProvider,
) -> list[FailureFlag]:
    """
    Convenience function to run suppression.
    Returns the same list with suppression applied.
    """
    engine = SuppressionEngine(provider)
    return engine.process(flags, schema, rationale)


def get_retained_flags(flags: list[FailureFlag]) -> list[FailureFlag]:
    """Filter to only retained (non-suppressed) flags."""
    return [f for f in flags if not f.suppressed]


def get_suppressed_flags(flags: list[FailureFlag]) -> list[FailureFlag]:
    """Filter to only suppressed flags (for audit log)."""
    return [f for f in flags if f.suppressed]
