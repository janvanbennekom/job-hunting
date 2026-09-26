"""Conversational search strategy management (Phase 11)."""

from __future__ import annotations

import streamlit as st

from jobhunter.ai.strategy_factory import StrategyProvider, resolve_strategy_change_model
from jobhunter.application.strategy_conversation import (
    StrategyChangeConfirmationService,
    StrategyConversationService,
    StrategyQueryService,
)
from jobhunter.application.strategy_conversation.dtos import ProposalOutcome
from jobhunter.infrastructure.config import get_settings
from jobhunter.ui.streamlit.bootstrap import get_session_factory
from jobhunter.ui.streamlit.sidebar import render_sidebar

render_sidebar()

st.title("Search strategy")
st.caption(
    "Propose changes in natural language, review the structured diff, then confirm "
    "to activate a new immutable revision."
)

session_factory = get_session_factory()
with session_factory() as session:
    active = StrategyQueryService(session).get_active_view()
    history = StrategyQueryService(session).list_revision_history()

if active is None:
    st.warning("No search strategy found. Seed strategy before using this page.")
    st.stop()

st.subheader("Active strategy")
if active.current_revision_id:
    st.write(
        f"Revision **#{active.revision_number}** — {active.change_summary or '—'}"
    )
    st.caption(f"`{active.current_revision_id}` · hash `{active.content_hash}`")
    with st.expander("Themes"):
        st.json(active.themes)
    with st.expander("Criteria"):
        st.json(active.criteria)
    with st.expander("Exclusions"):
        st.json(active.exclusions)
else:
    st.info("Strategy exists but has no active revision.")

st.subheader("Revision history")
if history:
    st.dataframe(
        [
            {
                "rev": row.revision_number,
                "status": row.status,
                "current": row.is_current,
                "source": row.change_source,
                "summary": row.change_summary[:80],
            }
            for row in history
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.write("No revisions recorded.")

st.subheader("Request a change")
instruction = st.text_area(
    "Natural-language instruction",
    placeholder="Example: Focus more on hands-on implementation and LIS work.",
    height=120,
)
provider = st.selectbox(
    "Interpretation provider",
    [StrategyProvider.OPENAI.value, StrategyProvider.FAKE.value],
    index=1,
    help="OpenAI requires JOBHUNTER_OPENAI_* env vars. Fake is for development/tests.",
)
if provider == StrategyProvider.FAKE.value:
    st.error("Development/fake interpretation provider selected.")

generate = st.button("Generate proposal", type="primary")

if generate:
    if not instruction.strip():
        st.warning("Enter an instruction first.")
    else:
        settings = get_settings()
        try:
            model = resolve_strategy_change_model(settings, provider)
        except RuntimeError as exc:
            st.error(str(exc))
        else:
            with session_factory() as session:
                proposal = StrategyConversationService(session).propose(
                    instruction, model
                )
            st.session_state["strategy_proposal"] = proposal

proposal = st.session_state.get("strategy_proposal")
if proposal is not None:
    st.subheader("Proposal")
    st.write(f"**Outcome:** {proposal.outcome.value}")
    st.write(proposal.summary)
    if proposal.assumptions:
        st.write("Assumptions:", proposal.assumptions)
    if proposal.clarification_questions:
        st.info("Clarification: " + "; ".join(proposal.clarification_questions))
    if proposal.provider_error:
        st.error(proposal.provider_error)
    if proposal.validation_errors:
        st.error("\n".join(proposal.validation_errors))

    if proposal.diff_lines:
        st.write("**Diff**")
        for line in proposal.diff_lines:
            st.write(
                f"- {line.area} `{line.item_key}` · {line.field_name}: "
                f"`{line.current_value}` → `{line.proposed_value}`"
            )

    if proposal.proposed_bundle and proposal.outcome == ProposalOutcome.PROPOSED:
        with st.expander("Proposed content (canonical)"):
            st.json(
                {
                    "content_hash": proposal.content_hash,
                    "revision_id": proposal.proposed_revision_id,
                }
            )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirm and activate"):
            with session_factory() as session:
                result = StrategyChangeConfirmationService(session).confirm(proposal)
                session.commit()
            st.success(result.message)
            st.session_state.pop("strategy_proposal", None)
            st.rerun()
    with col2:
        if st.button("Cancel proposal"):
            with session_factory() as session:
                StrategyChangeConfirmationService(session).cancel(proposal)
            st.session_state.pop("strategy_proposal", None)
            st.info("Proposal discarded.")
            st.rerun()
