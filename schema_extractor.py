"""
theLitmus — Schema Extractor (Layer A)
===============================================
Constrained LLM extraction: rationale text → CaseSchema JSON.

Design constraints:
  - The LLM translates. It never judges.
  - Every field carries a supporting quote or "not present"
  - No quality assessment, no failure detection
  - Output is validated against schema before passing to Layer B
"""

from __future__ import annotations
from case_schema import CaseSchema, build_schema
from llm_provider import LLMProvider, ExtractionError
import json


# ─── The Extraction Prompt ───────────────────────────────────────────
# This is the hardest single design artifact in the entire system.
# It must constrain the LLM to TRANSLATE, not JUDGE.

SYSTEM_PROMPT = """You are a structured data extraction engine for financial crime compliance case rationales.

YOUR ROLE: Extract factual information from analyst rationale text into a fixed JSON schema.
YOU DO NOT: Assess quality, detect failures, evaluate reasoning, or make judgments about the rationale.
YOU ONLY: Report what is present, what is absent, and what was stated.

CRITICAL RULES:
1. Every field must include a "supporting_text" property containing either:
   - A direct quote from the rationale (kept under 30 words) that justifies the field value
   - The exact string "not present" if the information does not appear in the rationale
2. Do NOT infer information that is not explicitly stated. If something is ambiguous, mark it as absent.
3. Do NOT assess whether the analyst's reasoning is good or bad. You are a transcriber, not a critic.
4. If the rationale mentions something in passing without substantive engagement, that is "present but not addressed."
5. Respond with ONLY valid JSON. No preamble, no markdown fences, no commentary.

OUTPUT SCHEMA:
{
  "case_type": {
    "value": "onboarding | refresh | alert_review | sar_decision | periodic_review | unknown",
    "supporting_text": "quote or 'not present'"
  },
  "customer_type": {
    "value": "retail | corporate | pep | high_risk | correspondent | unknown",
    "supporting_text": "quote or 'not present'"
  },
  "outcome": {
    "value": "closed_no_action | closed_downgraded | escalated | sar_filed | approved | pending | deferred | rejected | unknown",
    "supporting_text": "quote or 'not present'"
  },
  "indicators": [
    {
      "indicator_type": "string describing the indicator (e.g. adverse_media, unusual_transaction_pattern, inconsistent_profile, law_enforcement_touchpoint, jurisdictional_concern, prior_alert, unresolved_cdd, threshold_proximity, rapid_movement, third_party_concern, pep_association, sanctions_proximity)",
      "severity": "low | medium | high",
      "addressed": true/false,
      "supporting_text": "quote from rationale describing this indicator"
    }
  ],
  "adverse_media_present": {
    "value": true/false,
    "supporting_text": "quote or 'not present'"
  },
  "adverse_media_addressed": {
    "value": true/false,
    "supporting_text": "quote showing how it was addressed, or 'not present' / 'mentioned but not substantively addressed'"
  },
  "source_of_wealth_status": {
    "value": "verified_documentary | verified_verbal | stated_unverified | absent | generic",
    "supporting_text": "quote or 'not present'"
  },
  "source_of_funds_status": {
    "value": "verified_documentary | verified_verbal | stated_unverified | absent | generic",
    "supporting_text": "quote or 'not present'"
  },
  "expected_activity_defined": {
    "value": true/false,
    "supporting_text": "quote or 'not present'"
  },
  "customer_explanation_present": {
    "value": true/false,
    "supporting_text": "quote of the explanation or 'not present'"
  },
  "explanation_corroboration": {
    "value": "independent_documentary | internal_verbal | self_corroborating | none",
    "supporting_text": "quote showing corroboration method, or 'not present' if no corroboration was documented"
  },
  "third_party_reassurance_present": {
    "value": true/false,
    "supporting_text": "quote or 'not present'"
  },
  "conclusion_strength": {
    "value": "strong_clear | moderate_qualified | weak_comfort | absent",
    "supporting_text": "quote of the conclusion"
  },
  "evidence_base_strength": {
    "value": "comprehensive | partial | thin | absent",
    "supporting_text": "quote summarising the evidence cited, or 'not present' if minimal evidence referenced"
  },
  "analytical_bridge_present": {
    "value": true/false,
    "supporting_text": "quote showing reasoning that connects evidence to conclusion, or 'not present'"
  },
  "cumulative_inference_present": {
    "value": true/false,
    "supporting_text": "quote showing multiple factors being connected in reasoning, or 'not present'"
  },
  "escalation_considered": {
    "value": true/false,
    "supporting_text": "quote or 'not present'"
  },
  "non_escalation_reasoning_explicit": {
    "value": true/false,
    "supporting_text": "quote explaining why escalation was not pursued, or 'not present'"
  }
}

FIELD GUIDANCE:

- case_type: Determine from context clues (e.g. "onboarding review," "periodic refresh," "alert investigation").
- customer_type: Look for explicit mentions of customer category, PEP status, or risk classification.
- outcome: What did the analyst decide? Look for closure language, escalation, SAR filing, approval.
- indicators: List every risk signal mentioned in the rationale. Be thorough. Include signals the analyst mentioned even if they dismissed them.
- adverse_media_present/addressed: Did the rationale mention negative news? Did it engage with it substantively or just note it?
- source_of_wealth_status: Was SOW discussed? Was it backed by documents, stated verbally, or absent?
  - "verified_documentary": SOW supported by documents (bank statements, tax returns, property records, etc.)
  - "verified_verbal": SOW discussed based on verbal confirmation or interview
  - "stated_unverified": SOW mentioned but no verification documented
  - "absent": SOW not mentioned at all
  - "generic": SOW described in vague/boilerplate terms ("employment income" with no specifics)
- source_of_funds_status: Same logic as SOW but for source of funds for specific transactions.
- expected_activity_defined: Did the rationale state what activity is expected on this account?
- customer_explanation_present: Did a customer provide an explanation for specific activity or concerns?
- explanation_corroboration: If customer gave an explanation, how was it verified?
  - "independent_documentary": Checked against independent documents (Land Registry, Companies House, bank statements, court records, solicitor correspondence). The documents must come from a source OTHER than the customer or their instructed professionals.
  - "internal_verbal": Verified against the BANK'S OWN internal records or by an internal relationship manager who has independent knowledge. This does NOT include external third parties like the customer's accountant, lawyer, or family members — those are not internal to the bank.
  - "self_corroborating": The explanation references only information the customer themselves provided, OR is confirmed only by the customer's own instructed professionals (their accountant, their lawyer, their family member). An accountant or lawyer acting for the customer is NOT an independent source — they are repeating or confirming their client's own narrative.
  - "none": No verification documented
- third_party_reassurance_present: Did a relationship manager, accountant, lawyer, or other third party vouch for the customer?
- conclusion_strength: How definitive is the analyst's conclusion?
  - "strong_clear": Definitive statement with no hedging. This includes formal language ("no suspicion identified," "risk is low," "no further action required") AND informal/casual language that reaches the same definitive outcome ("happy to discount," "fine to close," "no issues," "all good," "nothing to worry about," "discounted"). If the analyst has decided the case is closed or discounted with no caveats, that is strong_clear regardless of how casually it is phrased.
  - "moderate_qualified": Conclusion with caveats ("on balance, no significant concerns")
  - "weak_comfort": Vague comfort language ("nothing particularly unusual," "appears consistent")
  - "absent": No clear conclusion stated
- evidence_base_strength: How much evidence did the analyst actually cite?
  - "comprehensive": Multiple evidence types referenced and engaged with
  - "partial": Some evidence cited but gaps visible
  - "thin": Minimal evidence, mostly assertions without documentary backing
  - "absent": No evidence cited. If the rationale is only one or two sentences and contains no references to documents, checks, reviews, or specific facts beyond stating a system output or marker, the evidence base is absent.
- analytical_bridge_present: Is there explicit reasoning that connects EVIDENCE to the conclusion? This means the analyst cited specific facts, documents, policies, or verifiable references and explained WHY those facts lead to the conclusion. 

  CRITICAL DISTINCTION: A bare assertion is NOT an analytical bridge. If the analyst states a classification or conclusion as fact without citing where that classification comes from, that is an unsupported claim, not reasoning. Examples:
  
  NOT a bridge: "A local councillor does not qualify as a PEP" — this is a policy claim with no citation. Which policy? Which PEP definition? Which regulatory guidance?
  NOT a bridge: "This does not qualify as a red flag" — says it is not a red flag but does not explain why.
  NOT a bridge: "The activity is consistent with the customer profile" — asserts consistency without showing what was compared.
  NOT a bridge: "Given the plausible explanation, no suspicion" — just says the explanation was accepted.
  NOT a bridge: "Screening was clear therefore no concerns" — cites a system output as the entire reasoning.
  
  IS a bridge: "A local councillor does not meet our PEP definition under Onboarding Policy section 4.2, which applies only to nationally appointed officials per the 2017 MLR guidance."
  IS a bridge: "The transaction amount and timing are consistent with the documented property sale completion on 15 March, and the originating bank matches the buyer's solicitor."
  IS a bridge: "Expected activity was defined at onboarding as salary credits of £3-5k monthly. The account shows salary credits of £4.2k monthly with no deviation."
  
  The test is simple: did the analyst cite something specific and external (a policy, a document, a record, a verifiable fact) to support their reasoning? Or did they just state their conclusion as if it were self-evidently true? If the latter, analytical_bridge_present = false.
- cumulative_inference_present: Did the analyst connect multiple factors together in their reasoning? Or did they treat each factor independently?
- escalation_considered: Did the rationale mention escalation at all?
- non_escalation_reasoning_explicit: If not escalated, did the analyst explain WHY escalation was not warranted?

Remember: you are extracting what IS in the text. You are not evaluating whether what is there is sufficient."""


USER_PROMPT_TEMPLATE = """Extract the structured schema from the following analyst rationale.

{metadata_section}

RATIONALE TEXT:
\"\"\"
{rationale}
\"\"\"

Respond with ONLY the JSON object. No preamble, no markdown fences, no commentary."""


def _build_metadata_section(metadata: dict | None) -> str:
    """Build optional metadata context for the extraction prompt."""
    if not metadata:
        return "No additional case metadata provided."

    lines = ["CASE METADATA (use to inform context fields):"]
    for key, value in metadata.items():
        lines.append(f"  - {key}: {value}")
    return "\n".join(lines)


# ─── The Extractor ────────────────────────────────────────────────────

class SchemaExtractor:
    """
    Layer A: Constrained LLM extraction.
    Takes raw rationale text → CaseSchema.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def extract(
        self,
        rationale: str,
        metadata: dict | None = None,
    ) -> CaseSchema:
        """
        Extract a CaseSchema from analyst rationale text.

        Args:
            rationale: The raw analyst rationale text
            metadata: Optional dict with case context (e.g. customer_type, case_type)

        Returns:
            A validated CaseSchema object

        Raises:
            ExtractionError: If LLM output is invalid JSON or fails validation
        """
        if not rationale or not rationale.strip():
            raise ExtractionError("Empty rationale provided")

        metadata_section = _build_metadata_section(metadata)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            metadata_section=metadata_section,
            rationale=rationale.strip(),
        )

        # Call LLM
        raw_json = self.provider.extract_json(SYSTEM_PROMPT, user_prompt)

        # Validate and build schema
        schema = build_schema(raw_json)

        # Post-validation: recalculate derived fields
        self._validate_traceability(raw_json)

        return schema

    def extract_raw(
        self,
        rationale: str,
        metadata: dict | None = None,
    ) -> dict:
        """
        Extract raw JSON without building CaseSchema.
        Useful for debugging extraction quality.
        """
        if not rationale or not rationale.strip():
            raise ExtractionError("Empty rationale provided")

        metadata_section = _build_metadata_section(metadata)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            metadata_section=metadata_section,
            rationale=rationale.strip(),
        )

        return self.provider.extract_json(SYSTEM_PROMPT, user_prompt)

    def _validate_traceability(self, raw_json: dict) -> None:
        """
        Check that extracted fields carry supporting text.
        Logs warnings for fields without traceability but does not reject.
        """
        traceable_fields = [
            "case_type", "customer_type", "outcome",
            "adverse_media_present", "adverse_media_addressed",
            "source_of_wealth_status", "source_of_funds_status",
            "expected_activity_defined", "customer_explanation_present",
            "explanation_corroboration", "third_party_reassurance_present",
            "conclusion_strength", "evidence_base_strength",
            "analytical_bridge_present", "cumulative_inference_present",
            "escalation_considered", "non_escalation_reasoning_explicit",
        ]

        missing_traceability = []
        for field_name in traceable_fields:
            field_data = raw_json.get(field_name)
            if isinstance(field_data, dict):
                st = field_data.get("supporting_text", "")
                if not st or st.strip() == "":
                    missing_traceability.append(field_name)
            else:
                missing_traceability.append(field_name)

        if missing_traceability:
            # Log but don't reject — extraction still usable
            import sys
            print(
                f"[TRACEABILITY WARNING] Fields without supporting text: "
                f"{', '.join(missing_traceability)}",
                file=sys.stderr,
            )
