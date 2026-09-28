"""Search strategy management: structured view/edit and conversational changes."""

from __future__ import annotations

import streamlit as st

from jobhunter.ai.strategy_factory import StrategyProvider, resolve_strategy_change_model
from jobhunter.application.strategy_conversation import (
    StrategyChangeConfirmationService,
    StrategyConversationService,
    StrategyQueryService,
)
from jobhunter.application.strategy_conversation.dtos import ProposalOutcome
from jobhunter.application.strategy_display.labels import label_change_source
from jobhunter.application.strategy_display.presentation import build_strategy_presentation
from jobhunter.application.strategy_structured_edit.service import StructuredStrategyEditService
from jobhunter.domain.strategy_enums import PreferenceStrength
from jobhunter.infrastructure.config import get_settings
from jobhunter.ui.streamlit.bootstrap import get_session_factory
from jobhunter.ui.streamlit.sidebar import render_sidebar


def _render_proposal(proposal, session_factory, state_key: str) -> None:
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

    if proposal.outcome == ProposalOutcome.NO_OP:
        st.info("This edit matches the active revision; no new revision will be created.")

    col1, col2 = st.columns(2)
    with col1:
        confirmable = (
            proposal.proposed_bundle
            and proposal.outcome == ProposalOutcome.PROPOSED
        )
        if confirmable and st.button("Confirm and activate", key=f"confirm-{state_key}"):
            with session_factory() as session:
                result = StrategyChangeConfirmationService(session).confirm(proposal)
                session.commit()
            st.success(result.message)
            st.session_state.pop(state_key, None)
            st.rerun()
    with col2:
        if st.button("Cancel proposal", key=f"cancel-{state_key}"):
            with session_factory() as session:
                StrategyChangeConfirmationService(session).cancel(proposal)
            st.session_state.pop(state_key, None)
            st.info("Proposal discarded.")
            st.rerun()


render_sidebar()

st.title("Search strategy")
st.caption(
    "Semantic search preferences are versioned as immutable revisions. "
    "Use **Structured edit** for explicit field changes or **Request a change** "
    "for natural-language proposals."
)

session_factory = get_session_factory()
with session_factory() as session:
    active = StrategyQueryService(session).get_active_view()
    history = StrategyQueryService(session).list_revision_history()

if active is None:
    st.warning("No search strategy found. Seed strategy before using this page.")
    st.stop()

current_hist = next((row for row in history if row.is_current), None)
st.subheader("Active revision")
if active.current_revision_id:
    st.write(
        f"Revision **#{active.revision_number}** — {active.change_summary or '—'}"
    )
    if current_hist:
        st.caption(
            f"Activated {current_hist.created_at} · "
            f"{label_change_source(current_hist.change_source)}"
        )
else:
    st.info("Strategy exists but has no active revision.")

presentation = build_strategy_presentation(active)

tab_overview, tab_structured, tab_conversation = st.tabs(
    ["Overview", "Structured edit", "Request a change"]
)

with tab_overview:
    st.markdown("#### Search themes")
    if presentation.theme_rows:
        st.dataframe(
            [
                {
                    "Theme": row.label or row.theme_key,
                    "Strength": row.strength,
                    "Active": row.active,
                    "Notes": row.notes,
                }
                for row in presentation.theme_rows
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No themes configured.")

    st.markdown("#### Preference criteria")
    if presentation.preference_rows:
        st.dataframe(
            [
                {
                    "Criterion": row.criterion,
                    "Strength": row.strength,
                    "Active": row.active,
                    "Value": row.value_summary,
                }
                for row in presentation.preference_rows
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No preference criteria.")

    st.markdown("#### Hard constraints")
    if presentation.constraint_rows:
        st.dataframe(
            [
                {
                    "Constraint": row.criterion,
                    "Strength": row.strength,
                    "Active": row.active,
                    "Value": row.value_summary,
                }
                for row in presentation.constraint_rows
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No hard constraints.")

    st.markdown("#### Exclusions")
    if presentation.exclusion_rows:
        st.dataframe(
            [
                {
                    "Exclusion": row.exclusion,
                    "Active": row.active,
                    "Condition": row.condition,
                }
                for row in presentation.exclusion_rows
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No exclusions.")

    st.markdown("#### Revision history")
    if history:
        st.dataframe(
            [
                {
                    "Rev": row.revision_number,
                    "Current": "Yes" if row.is_current else "",
                    "Activated": row.created_at,
                    "Source": label_change_source(row.change_source),
                    "Summary": row.change_summary,
                }
                for row in history
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No revisions recorded.")

with tab_structured:
    st.write(
        "Adjust themes and exclusions deterministically. A new revision is created "
        "only after you review the diff and confirm."
    )
    strength_values = [s.value for s in PreferenceStrength]
    theme_edits: dict[str, dict[str, object]] = {}
    for item in active.themes:
        key = str(item.get("theme_key", ""))
        if not key:
            continue
        label = str(item.get("label") or key)
        current_strength = str(item.get("strength", strength_values[0]))
        current_active = bool(item.get("is_active", True))
        st.markdown(f"**{label}** (`{key}`)")
        cols = st.columns(2)
        with cols[0]:
            strength = st.selectbox(
                "Strength",
                strength_values,
                index=strength_values.index(current_strength)
                if current_strength in strength_values
                else 0,
                key=f"theme-strength-{key}",
            )
        with cols[1]:
            is_active = st.checkbox(
                "Active",
                value=current_active,
                key=f"theme-active-{key}",
            )
        theme_edits[key] = {"strength": strength, "is_active": is_active}

    st.markdown("#### Exclusions")
    exclusion_edits: dict[str, bool] = {}
    for item in active.exclusions:
        code = str(item.get("exclusion_code", ""))
        if not code:
            continue
        exclusion_edits[code] = st.checkbox(
            f"Active — {code}",
            value=bool(item.get("is_active", True)),
            key=f"excl-{code}",
        )

    change_summary = st.text_input(
        "Change summary (for revision history)",
        value="Structured strategy edit",
    )

    if st.button("Preview structured changes", type="primary"):
        mutations: list[dict[str, object]] = []
        for key, edit in theme_edits.items():
            original = next(
                (t for t in active.themes if str(t.get("theme_key")) == key),
                None,
            )
            if original is None:
                continue
            if str(original.get("strength")) != edit["strength"]:
                mutations.append(
                    {
                        "op": "SET_THEME_STRENGTH",
                        "theme_key": key,
                        "strength": edit["strength"],
                    }
                )
            if bool(original.get("is_active", True)) != edit["is_active"]:
                mutations.append(
                    {
                        "op": "SET_THEME_ACTIVE",
                        "theme_key": key,
                        "is_active": edit["is_active"],
                    }
                )
        for code, is_active in exclusion_edits.items():
            original = next(
                (
                    e
                    for e in active.exclusions
                    if str(e.get("exclusion_code")) == code
                ),
                None,
            )
            if original is None:
                continue
            if bool(original.get("is_active", True)) != is_active:
                mutations.append(
                    {
                        "op": "SET_EXCLUSION_ACTIVE",
                        "exclusion_code": code,
                        "is_active": is_active,
                    }
                )
        if not mutations:
            st.info("No changes detected compared with the active revision.")
        else:
            with session_factory() as session:
                proposal = StructuredStrategyEditService(session).propose_mutations(
                    mutations,
                    change_summary=change_summary.strip() or "Structured strategy edit",
                )
            st.session_state["structured_strategy_proposal"] = proposal

    structured_proposal = st.session_state.get("structured_strategy_proposal")
    if structured_proposal is not None:
        _render_proposal(structured_proposal, session_factory, "structured_strategy_proposal")

with tab_conversation:
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

    if st.button("Generate proposal", type="primary", key="conv-generate"):
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

    conversation_proposal = st.session_state.get("strategy_proposal")
    if conversation_proposal is not None:
        _render_proposal(conversation_proposal, session_factory, "strategy_proposal")
