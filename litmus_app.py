"""
Crucible Phase 2 — Streamlit UI
=================================
Sleek, minimalist interface. White + light blue.
Designed for compliance heads, not developers.
"""

import streamlit as st
import json
import time
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from case_schema import CaseSchema, build_schema
from failure_pattern_engine import detect_failure_patterns, FailureFlag, Severity
from suppression_engine import SuppressionEngine, get_retained_flags, get_suppressed_flags

# ─── Page Config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="theLitmus",
    page_icon="◇",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Custom CSS ───────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300;1,9..40,400&family=JetBrains+Mono:wght@300;400;500&display=swap');

    /* ── Reset & Base ── */
    .stApp {
        background: #FAFBFD;
        font-family: 'DM Sans', sans-serif;
    }

    .main .block-container {
        max-width: 920px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }

    /* ── Hide Streamlit defaults ── */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    section[data-testid="stSidebar"] {display: none;}
    .stAppToolbar {display: none !important;}

    /* ── Typography ── */
    h1, h2, h3 {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        color: #1a1a2e !important;
        letter-spacing: -0.02em;
    }

    h1 {
        font-size: 1.75rem !important;
        margin-bottom: 0.25rem !important;
    }

    p, li, span, div {
        font-family: 'DM Sans', sans-serif !important;
    }

    /* ── Logo / Brand ── */
    .crucible-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 2rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid #E8EDF3;
    }

    .crucible-logo {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, #4A9BD9 0%, #7BB8E8 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 18px;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }

    .crucible-wordmark {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.35rem;
        font-weight: 600;
        color: #1a1a2e;
        letter-spacing: 0.08em;
    }

    .crucible-tagline {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.75rem;
        color: #8899AA;
        letter-spacing: 0.04em;
        margin-left: auto;
    }

    /* ── Input Area ── */
    .stTextArea textarea {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.9rem !important;
        line-height: 1.6 !important;
        color: #2C3E50 !important;
        background: #FFFFFF !important;
        border: 1px solid #D6E4F0 !important;
        border-radius: 10px !important;
        padding: 1rem !important;
        transition: border-color 0.2s ease;
    }

    .stTextArea textarea:focus {
        border-color: #4A9BD9 !important;
        box-shadow: 0 0 0 2px rgba(74, 155, 217, 0.1) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        background: linear-gradient(135deg, #4A9BD9 0%, #5FAEE3 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 2rem !important;
        letter-spacing: 0.02em;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(74, 155, 217, 0.2) !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #3D8BC5 0%, #4A9BD9 100%) !important;
        box-shadow: 0 4px 14px rgba(74, 155, 217, 0.3) !important;
        transform: translateY(-1px);
    }

    .stButton > button:active {
        transform: translateY(0px);
    }

    /* ── Result Cards ── */
    .result-card {
        background: #FFFFFF;
        border: 1px solid #E8EDF3;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: box-shadow 0.2s ease;
    }

    .result-card:hover {
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
    }

    .result-clear {
        border-left: 4px solid #4ECDC4;
    }

    .result-flagged {
        border-left: 4px solid #E94560;
    }

    /* ── Status Badges ── */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', monospace;
    }

    .badge-clear {
        background: #E8F8F5;
        color: #2D6A4F;
    }

    .badge-low {
        background: #FFF3E0;
        color: #E76F51;
    }

    .badge-medium {
        background: #FFF0E6;
        color: #D35400;
    }

    .badge-high {
        background: #FDEAEA;
        color: #C1121F;
    }

    .badge-critical {
        background: #1a1a2e;
        color: #FFFFFF;
    }

    .badge-suppressed {
        background: #F0F2F5;
        color: #8899AA;
    }

    /* ── Schema View ── */
    .schema-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.75rem;
        margin: 1rem 0;
    }

    .schema-field {
        background: #F7FAFC;
        border: 1px solid #E8EDF3;
        border-radius: 8px;
        padding: 0.75rem 1rem;
    }

    .schema-field-label {
        font-size: 0.7rem;
        font-weight: 500;
        color: #8899AA;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 2px;
        font-family: 'JetBrains Mono', monospace;
    }

    .schema-field-value {
        font-size: 0.88rem;
        color: #2C3E50;
        font-weight: 400;
    }

    .schema-field-quote {
        font-size: 0.75rem;
        color: #8899AA;
        font-style: italic;
        margin-top: 4px;
        line-height: 1.4;
    }

    /* ── Flag Detail ── */
    .flag-card {
        background: #FFFFFF;
        border: 1px solid #FDEAEA;
        border-left: 4px solid #E94560;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin: 0.75rem 0;
    }

    .flag-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 0.75rem;
    }

    .flag-id {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        font-weight: 500;
        color: #E94560;
    }

    .flag-name {
        font-size: 0.95rem;
        font-weight: 500;
        color: #1a1a2e;
    }

    .flag-explanation {
        font-size: 0.88rem;
        color: #4A5568;
        line-height: 1.6;
        margin: 0.5rem 0;
    }

    .flag-defensibility {
        font-size: 0.82rem;
        color: #718096;
        line-height: 1.5;
        padding: 0.75rem;
        background: #FAFBFD;
        border-radius: 6px;
        margin-top: 0.75rem;
        border-left: 2px solid #D6E4F0;
    }

    /* ── Suppressed flag ── */
    .suppressed-card {
        background: #FAFBFD;
        border: 1px solid #E8EDF3;
        border-left: 4px solid #D6E4F0;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0;
        opacity: 0.75;
    }

    .suppressed-reason {
        font-size: 0.82rem;
        color: #8899AA;
        font-style: italic;
    }

    /* ── Timing bar ── */
    .timing-bar {
        display: flex;
        gap: 1.5rem;
        padding: 0.75rem 0;
        margin-top: 1rem;
        border-top: 1px solid #E8EDF3;
    }

    .timing-item {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        color: #8899AA;
    }

    .timing-value {
        color: #4A9BD9;
        font-weight: 500;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 1px solid #E8EDF3;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 400;
        font-size: 0.88rem;
        color: #8899AA;
        padding: 0.75rem 1.25rem;
        border-bottom: 2px solid transparent;
    }

    .stTabs [aria-selected="true"] {
        color: #4A9BD9 !important;
        border-bottom: 2px solid #4A9BD9 !important;
        font-weight: 500;
    }

    /* ── Selectbox ── */
    .stSelectbox > div > div {
        border-radius: 8px !important;
        border-color: #D6E4F0 !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    /* ── Checkbox styling ── */
    .stCheckbox label {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.85rem !important;
        color: #4A9BD9 !important;
    }

    /* ── Selectbox fix ── */
    .stSelectbox [data-baseweb="select"] {
        background: #FFFFFF !important;
    }

    .stSelectbox [data-baseweb="select"] > div {
        background: #FFFFFF !important;
        color: #2C3E50 !important;
    }

    /* ── Divider ── */
    .section-divider {
        border: none;
        border-top: 1px solid #E8EDF3;
        margin: 2rem 0 1.5rem 0;
    }

    /* ── Mode indicator ── */
    .mode-pill {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.65rem;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 500;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    .mode-schema {
        background: #E3F0FA;
        color: #4A9BD9;
    }

    .mode-regex {
        background: #FFF3E0;
        color: #E76F51;
    }
</style>
""", unsafe_allow_html=True)

# ─── Brand Header ─────────────────────────────────────────────────────

st.markdown("""
<div class="crucible-brand">
    <div class="crucible-logo">L</div>
    <div class="crucible-wordmark">theLitmus</div>
    <div class="crucible-tagline">Reasoning Integrity Auditor</div>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar: Settings ────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Settings")

    provider = st.selectbox(
        "LLM Provider",
        ["claude", "openai", "ollama"],
        index=0,
        help="Select the LLM provider for extraction and suppression."
    )

    # Try to load API key from Streamlit secrets first
    _secret_key = ""
    try:
        _secret_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    except Exception:
        pass

    if _secret_key:
        api_key = _secret_key
        st.markdown(
            '<div style="font-size: 0.75rem; color: #4ECDC4; margin-bottom: 1rem;">'
            '✓ API key loaded from secrets</div>',
            unsafe_allow_html=True,
        )
    else:
        api_key = st.text_input(
            "API Key",
            type="password",
            help="Required for Claude or OpenAI. Not needed for Ollama."
        )

    model_override = st.text_input(
        "Model Override (optional)",
        placeholder="e.g. claude-sonnet-4-20250514",
        help="Leave blank for provider defaults."
    )

    suppression_enabled = st.toggle(
        "Suppression Layer (Layer C)",
        value=True,
        help="When enabled, a second LLM call filters out immaterial flags."
    )

    st.markdown("---")
    st.markdown(
        '<div style="font-size: 0.75rem; color: #8899AA;">'
        'Schema-first architecture. The LLM translates. '
        'The rules engine judges. Layer C suppresses noise.'
        '</div>',
        unsafe_allow_html=True,
    )

# ─── Main Tabs ────────────────────────────────────────────────────────

tab_analyze, tab_corpus, tab_architecture = st.tabs([
    "Analyze", "Test Corpus", "Architecture"
])

# ══════════════════════════════════════════════════════════════════════
# TAB: ANALYZE
# ══════════════════════════════════════════════════════════════════════

with tab_analyze:
    st.markdown(
        '<p style="font-size: 0.88rem; color: #718096; margin-bottom: 1.5rem;">'
        'Paste an analyst rationale below. theLitmus will extract its reasoning structure, '
        'run deterministic failure-pattern rules, and surface only material findings.'
        '</p>',
        unsafe_allow_html=True,
    )

    rationale = st.text_area(
        "Analyst Rationale",
        height=220,
        placeholder="Paste the analyst's case rationale here...",
        label_visibility="collapsed",
    )

    analyze_clicked = st.button("Analyze", use_container_width=True)

    show_meta = st.checkbox("Add case metadata (optional)", value=False)
    meta_case_type = ""
    meta_customer_type = ""
    if show_meta:
        meta_case_type = st.selectbox(
            "Case Type",
            ["", "onboarding", "refresh", "alert_review", "sar_decision", "periodic_review"],
        )
        meta_customer_type = st.selectbox(
            "Customer Type",
            ["", "retail", "corporate", "pep", "high_risk", "correspondent"],
        )

    if analyze_clicked and rationale.strip():
        metadata = {}
        if meta_case_type:
            metadata["case_type"] = meta_case_type
        if meta_customer_type:
            metadata["customer_type"] = meta_customer_type

        # ── Check provider setup ──
        if provider in ("claude", "openai") and not api_key:
            st.error(f"API key required for {provider}. Set it in the sidebar.")
            st.stop()

        # ── Run pipeline ──
        progress_placeholder = st.empty()
        progress_placeholder.markdown(
            '<div style="display: flex; align-items: center; gap: 12px; padding: 1.5rem; '
            'background: #F0F7FC; border: 1px solid #D6E4F0; border-radius: 10px; margin: 1rem 0;">'
            '<div style="width: 20px; height: 20px; border: 3px solid #D6E4F0; '
            'border-top: 3px solid #4A9BD9; border-radius: 50%; '
            'animation: spin 0.8s linear infinite;"></div>'
            '<div style="font-size: 0.88rem; color: #4A5568; font-family: DM Sans, sans-serif;">'
            'Extracting reasoning structure...</div>'
            '</div>'
            '<style>@keyframes spin { 0% { transform: rotate(0deg); } '
            '100% { transform: rotate(360deg); } }</style>',
            unsafe_allow_html=True,
        )
        try:
            # Set config
            os.environ["ANTHROPIC_API_KEY"] = api_key if provider == "claude" else ""
            os.environ["OPENAI_API_KEY"] = api_key if provider == "openai" else ""

            import config as cfg
            cfg.LLM_PROVIDER = provider
            cfg.LLM_MODEL = model_override if model_override else ""
            cfg.SUPPRESSION_ENABLED = suppression_enabled

            from litmus import analyze_rationale
            from llm_provider import get_provider

            llm = get_provider(
                provider_name=provider,
                api_key=api_key if api_key else None,
                model=model_override if model_override else None,
            )

            result = analyze_rationale(rationale, metadata, provider=llm)

        except Exception as e:
            progress_placeholder.empty()
            st.error(f"Analysis failed: {str(e)}")
            st.stop()

        progress_placeholder.empty()

        # ── Results ──
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # Status header
        if result.flagged:
            severity_badge = result.highest_severity
            badge_class = f"badge-{severity_badge}"
            st.markdown(
                f'<div class="result-card result-flagged">'
                f'<div style="display: flex; align-items: center; gap: 12px;">'
                f'<span style="font-size: 1.1rem; font-weight: 500; color: #1a1a2e;">'
                f'{result.flag_count} Finding{"s" if result.flag_count != 1 else ""}</span>'
                f'<span class="badge {badge_class}">{severity_badge}</span>'
                f'<span class="mode-pill mode-schema">schema</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            suppressed_count = len(result.suppressed_flags)
            suppressed_note = (
                f" &middot; {suppressed_count} considered, suppressed"
                if suppressed_count > 0 else ""
            )
            st.markdown(
                f'<div class="result-card result-clear">'
                f'<div style="display: flex; align-items: center; gap: 12px;">'
                f'<span style="font-size: 1.1rem; font-weight: 500; color: #2D6A4F;">'
                f'No Material Findings</span>'
                f'<span class="badge badge-clear">clear</span>'
                f'<span class="mode-pill mode-schema">schema</span>'
                f'</div>'
                f'<div style="font-size: 0.82rem; color: #718096; margin-top: 6px;">'
                f'The rationale was analyzed against FP-02 and FP-04 pattern rules{suppressed_note}.'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Retained Flags ──
        for flag in result.retained_flags:
            badge_class = f"badge-{flag.severity.value}"
            st.markdown(
                f'<div class="flag-card">'
                f'<div class="flag-header">'
                f'<span class="flag-id">{flag.pattern_id}</span>'
                f'<span class="flag-name">{flag.pattern_name}</span>'
                f'<span class="badge {badge_class}">{flag.severity.value}</span>'
                f'</div>'
                f'<div class="flag-explanation">{flag.explanation_template}</div>'
                f'<div class="flag-defensibility">{flag.defensibility_note}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Suppressed Flags ──
        if result.suppressed_flags:
            show_suppressed = st.checkbox(f"Show suppressed ({len(result.suppressed_flags)})", value=False)
            if show_suppressed:
                for flag in result.suppressed_flags:
                    st.markdown(
                        f'<div class="suppressed-card">'
                        f'<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">'
                        f'<span class="flag-id" style="color: #8899AA;">{flag.pattern_id}</span>'
                        f'<span style="font-size: 0.88rem; color: #8899AA;">{flag.pattern_name}</span>'
                        f'<span class="badge badge-suppressed">suppressed</span>'
                        f'</div>'
                        f'<div class="suppressed-reason">{flag.suppression_reason}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # ── Schema View ──
        show_schema = st.checkbox("Show schema extraction", value=False)
        if show_schema:
            schema = result.schema
            schema_fields = [
                ("Case Type", schema.case_type),
                ("Customer Type", schema.customer_type),
                ("Outcome", schema.outcome),
                ("Conclusion Strength", schema.conclusion_strength),
                ("Evidence Base", schema.evidence_base_strength),
                ("Analytical Bridge", schema.analytical_bridge_present),
                ("SOW Status", schema.source_of_wealth_status),
                ("SOF Status", schema.source_of_funds_status),
                ("Expected Activity", schema.expected_activity_defined),
                ("Customer Explanation", schema.customer_explanation_present),
                ("Corroboration", schema.explanation_corroboration),
                ("Third-Party Reassurance", schema.third_party_reassurance_present),
                ("Adverse Media", schema.adverse_media_present),
                ("Adverse Media Addressed", schema.adverse_media_addressed),
                ("Cumulative Inference", schema.cumulative_inference_present),
                ("Escalation Considered", schema.escalation_considered),
                ("Non-Escalation Reasoning", schema.non_escalation_reasoning_explicit),
            ]

            html_fields = ""
            for label, sf in schema_fields:
                val = sf.value
                if hasattr(val, 'value'):
                    val = val.value
                quote = sf.supporting_text
                if len(str(quote)) > 120:
                    quote = str(quote)[:120] + "..."
                quote_html = (
                    f'<div class="schema-field-quote">"{quote}"</div>'
                    if quote and quote != "test" and quote != "not present"
                    else (
                        f'<div class="schema-field-quote" style="color: #D4A574;">not present</div>'
                        if quote == "not present"
                        else ""
                    )
                )
                html_fields += (
                    f'<div class="schema-field">'
                    f'<div class="schema-field-label">{label}</div>'
                    f'<div class="schema-field-value">{val}</div>'
                    f'{quote_html}'
                    f'</div>'
                )

            st.markdown(
                f'<div class="schema-grid">{html_fields}</div>',
                unsafe_allow_html=True,
            )

            # Indicators
            if schema.indicators:
                st.markdown(
                    '<div style="font-size: 0.78rem; font-weight: 500; color: #8899AA; '
                    'text-transform: uppercase; letter-spacing: 0.06em; margin-top: 1rem; '
                    'margin-bottom: 0.5rem; font-family: JetBrains Mono, monospace;">'
                    'Risk Indicators</div>',
                    unsafe_allow_html=True,
                )
                for ind in schema.indicators:
                    addr_badge = (
                        '<span class="badge badge-clear">addressed</span>'
                        if ind.addressed
                        else '<span class="badge badge-low">unaddressed</span>'
                    )
                    sev_color = {"low": "#4ECDC4", "medium": "#E76F51", "high": "#C1121F"}
                    color = sev_color.get(ind.severity.value, "#8899AA")
                    st.markdown(
                        f'<div style="padding: 0.5rem 0.75rem; margin: 0.25rem 0; '
                        f'background: #F7FAFC; border-radius: 6px; border-left: 3px solid {color}; '
                        f'display: flex; align-items: center; gap: 8px;">'
                        f'<span style="font-size: 0.85rem; color: #2C3E50;">{ind.indicator_type}</span>'
                        f'<span class="badge" style="background: {color}15; color: {color};">'
                        f'{ind.severity.value}</span>'
                        f'{addr_badge}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # ── Trigger Fields (raw) ──
        if result.retained_flags:
            show_triggers = st.checkbox("Show trigger fields (audit detail)", value=False)
            if show_triggers:
                for flag in result.retained_flags:
                    st.markdown(f"**{flag.pattern_id}** — {flag.pattern_name}")
                    st.json(flag.trigger_fields)

        # ── Debug: Raw Schema ──
        show_debug = st.checkbox("Show debug: raw schema output", value=False)
        if show_debug:
            st.markdown(f"**Flags from Layer B:** {len(result.all_flags)}")
            st.markdown(f"**Retained:** {len(result.retained_flags)}")
            st.markdown(f"**Suppressed:** {len(result.suppressed_flags)}")
            st.json(result.schema.to_dict())

        # ── Timing ──
        st.markdown(
            f'<div class="timing-bar">'
            f'<div class="timing-item">extraction <span class="timing-value">'
            f'{result.extraction_time_ms:.0f}ms</span></div>'
            f'<div class="timing-item">detection <span class="timing-value">'
            f'{result.detection_time_ms:.0f}ms</span></div>'
            f'<div class="timing-item">suppression <span class="timing-value">'
            f'{result.suppression_time_ms:.0f}ms</span></div>'
            f'<div class="timing-item">total <span class="timing-value">'
            f'{result.total_time_ms:.0f}ms</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    elif analyze_clicked:
        st.warning("Paste a rationale first.")


# ══════════════════════════════════════════════════════════════════════
# TAB: TEST CORPUS
# ══════════════════════════════════════════════════════════════════════

with tab_corpus:
    st.markdown(
        '<p style="font-size: 0.88rem; color: #718096; margin-bottom: 1.5rem;">'
        'Pre-built test rationales for validating detection accuracy. '
        'Select a rationale and run it through the pipeline.'
        '</p>',
        unsafe_allow_html=True,
    )

    corpus_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_corpus")

    corpus_files = {}
    for root, dirs, files in os.walk(corpus_dir):
        for f in files:
            if f.endswith(".json"):
                rel = os.path.relpath(os.path.join(root, f), corpus_dir)
                corpus_files[rel] = os.path.join(root, f)

    if corpus_files:
        selected_file = st.selectbox("Corpus File", list(corpus_files.keys()))

        if selected_file:
            with open(corpus_files[selected_file], "r") as f:
                corpus = json.load(f)

            labels = [f"{r['id']}: {r['label']}" for r in corpus]
            selected_label = st.selectbox("Rationale", labels)

            if selected_label:
                idx = labels.index(selected_label)
                entry = corpus[idx]

                st.markdown(
                    f'<div class="result-card">'
                    f'<div style="font-size: 0.78rem; color: #8899AA; margin-bottom: 0.5rem; '
                    f'font-family: JetBrains Mono, monospace;">{entry["id"]}</div>'
                    f'<div style="font-size: 0.88rem; color: #2C3E50; line-height: 1.6;">'
                    f'{entry["rationale"]}</div>'
                    f'<div style="margin-top: 0.75rem; font-size: 0.78rem; color: #8899AA;">'
                    f'Expected triggers: {", ".join(entry.get("should_trigger", [])) or "none"}'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if entry.get("notes"):
                    st.markdown(
                        f'<div style="font-size: 0.82rem; color: #718096; font-style: italic; '
                        f'padding: 0.5rem 0;">{entry["notes"]}</div>',
                        unsafe_allow_html=True,
                    )
    else:
        st.info("No test corpus files found. Add JSON files to the test_corpus/ directory.")


# ══════════════════════════════════════════════════════════════════════
# TAB: ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════

with tab_architecture:
    st.markdown(
        '<p style="font-size: 0.88rem; color: #718096; margin-bottom: 1.5rem;">'
        'How theLitmus works. Three layers, one principle: '
        'the LLM never decides whether a failure occurred.'
        '</p>',
        unsafe_allow_html=True,
    )

    st.markdown("""
<div style="display: flex; flex-direction: column; gap: 1rem; margin: 1.5rem 0;">

<div style="background: #FFFFFF; border: 1px solid #D6E4F0; border-left: 4px solid #4A9BD9;
    border-radius: 10px; padding: 1.25rem 1.5rem;">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
            font-weight: 500; color: #4A9BD9; text-transform: uppercase; letter-spacing: 0.06em;">
            Layer A</span>
        <span style="font-size: 0.95rem; font-weight: 500; color: #1a1a2e;">
            Constrained Extraction</span>
    </div>
    <div style="font-size: 0.85rem; color: #4A5568; line-height: 1.6;">
        A provider-agnostic LLM reads the rationale and populates a typed schema (19 fields).
        Every field carries a supporting quote or an explicit "not present" marker.
        The LLM translates. It does not judge.
    </div>
</div>

<div style="text-align: center; color: #D6E4F0; font-size: 1.2rem;">↓</div>

<div style="background: #FFFFFF; border: 1px solid #D6E4F0; border-left: 4px solid #2D6A4F;
    border-radius: 10px; padding: 1.25rem 1.5rem;">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
            font-weight: 500; color: #2D6A4F; text-transform: uppercase; letter-spacing: 0.06em;">
            Layer B</span>
        <span style="font-size: 0.95rem; font-weight: 500; color: #1a1a2e;">
            Deterministic Adjudication</span>
    </div>
    <div style="font-size: 0.85rem; color: #4A5568; line-height: 1.6;">
        Pure Python logic. No LLM. Takes the schema and runs failure-pattern rules.
        Currently active: FP-02 (Unsupported Conclusion) and FP-04 (Narrative Acceptance).
        Same input always produces the same output. Every flag traces to specific schema fields.
    </div>
</div>

<div style="text-align: center; color: #D6E4F0; font-size: 1.2rem;">↓</div>

<div style="background: #FFFFFF; border: 1px solid #D6E4F0; border-left: 4px solid #E94560;
    border-radius: 10px; padding: 1.25rem 1.5rem;">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 0.5rem;">
        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
            font-weight: 500; color: #E94560; text-transform: uppercase; letter-spacing: 0.06em;">
            Layer C</span>
        <span style="font-size: 0.95rem; font-weight: 500; color: #1a1a2e;">
            Contextual Suppression</span>
    </div>
    <div style="font-size: 0.85rem; color: #4A5568; line-height: 1.6;">
        A second LLM call reviews flagged findings against the original rationale.
        Default stance: suppress unless clearly material.
        Can suppress flags. Cannot add new ones.
        When this system speaks, it is almost undeniably correct.
    </div>
</div>

</div>
""", unsafe_allow_html=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size: 0.78rem; font-weight: 500; color: #8899AA; '
        'text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.75rem; '
        'font-family: JetBrains Mono, monospace;">Active Patterns</div>',
        unsafe_allow_html=True,
    )

    patterns_html = """
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
    <div style="background: #F7FAFC; border: 1px solid #E8EDF3; border-radius: 8px; padding: 1rem;">
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #E94560;
            font-weight: 500; margin-bottom: 4px;">FP-02</div>
        <div style="font-size: 0.88rem; font-weight: 500; color: #1a1a2e; margin-bottom: 4px;">
            Unsupported Conclusion</div>
        <div style="font-size: 0.78rem; color: #718096; line-height: 1.5;">
            The decision outruns the evidence. Strong conclusion reached while key evidential
            components are absent, thin, or generic.</div>
    </div>
    <div style="background: #F7FAFC; border: 1px solid #E8EDF3; border-radius: 8px; padding: 1rem;">
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #E94560;
            font-weight: 500; margin-bottom: 4px;">FP-04</div>
        <div style="font-size: 0.88rem; font-weight: 500; color: #1a1a2e; margin-bottom: 4px;">
            Narrative Acceptance</div>
        <div style="font-size: 0.78rem; color: #718096; line-height: 1.5;">
            A customer or third-party explanation was treated as risk-resolving without
            documented corroboration. Plausibility is not verification.</div>
    </div>
</div>
"""
    st.markdown(patterns_html, unsafe_allow_html=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    st.markdown(
        '<div style="font-size: 0.82rem; color: #718096; line-height: 1.6; max-width: 600px;">'
        'theLitmus is built on enforcement-action evidence: &#163;265M+ in FCA fines across '
        'Nationwide, Barclays, Mako, Coinbase, Monzo, and Dinosaur Merchant Bank. '
        'The patterns are not theoretical. They are extracted from what regulators actually punished.'
        '</div>',
        unsafe_allow_html=True,
    )
