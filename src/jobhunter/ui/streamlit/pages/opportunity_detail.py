"""Single opportunity review detail."""

from __future__ import annotations

import json

import streamlit as st

from jobhunter.application.pursuit import (
    PursuitOperationalUpdate,
    PursuitTrackingService,
)
from jobhunter.application.review import HumanReviewService, OpportunityDetailService
from jobhunter.domain.pursuit_enums import PursuitStatus
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.ui.streamlit.bootstrap import allow_fake_results, get_session_factory
from jobhunter.ui.streamlit.sidebar import render_sidebar

render_sidebar()

st.title("Opportunity detail")

session_factory = get_session_factory()
default_id = st.session_state.get("selected_opportunity_id", "")
opportunity_id = st.text_input("Opportunity id", value=default_id)

if not opportunity_id:
    st.info("Select an opportunity from the Opportunities page or enter an id.")
    st.stop()

with session_factory() as session:
    detail = OpportunityDetailService(session).get_detail(
        opportunity_id, allow_fake=allow_fake_results()
    )

if detail is None:
    st.error("Opportunity not found.")
    st.stop()

facts = detail.facts
st.header(facts.title)
st.caption(f"Opportunity id: {facts.opportunity_id}")

if facts.primary_external_url:
    st.link_button("Open source posting", facts.primary_external_url)

st.markdown("### Source / opportunity facts")
st.markdown("*Source fact*")
st.write(
    {
        "organisation": facts.organisation,
        "location": facts.location,
        "type": facts.opportunity_type,
        "lifecycle": facts.lifecycle_status.value,
        "eligibility (stored)": facts.eligibility_status.value,
        "deadline": str(facts.deadline or ""),
        "publication": str(facts.publication_date or ""),
        "source_status": facts.source_status,
    }
)
if facts.description:
    st.text_area("Description", facts.description, height=200, disabled=True)

if facts.source_links:
    st.write("Source links (most recent first)")
    for link in facts.source_links:
        url = link.external_url
        st.write(
            f"**{link.source_name}** — ref={link.source_reference or '—'} "
            f"last_seen={link.last_seen_at}"
        )
        if url:
            st.link_button(f"Open ({link.source_id})", url, key=f"link-{link.source_id}")

st.markdown("### Deterministic eligibility")
st.markdown("*Deterministic eligibility*")
if detail.eligibility is None:
    st.write("No eligibility decision for the active search strategy revision.")
else:
    elig = detail.eligibility
    st.write(f"Status: **{elig.status.value}** (decision `{elig.decision_id}`)")
    st.write(f"Search strategy revision: `{elig.search_strategy_revision_id}`")
    st.write(f"Evaluated at: {elig.evaluated_at}")
    for rule in elig.rule_results:
        st.write(
            f"- `{rule.rule_code}` ({rule.rule_kind}) → {rule.outcome}: "
            f"{rule.summary or ''}"
        )
        if rule.evidence:
            st.caption(rule.evidence)

st.markdown("### AI profile assessment")
st.markdown("*AI inference*")
assess = detail.assessment
if not assess.present:
    st.warning(assess.explanation or "No assessment available.")
    if assess.provider_error:
        st.code(assess.provider_error)
else:
    if assess.is_fake:
        st.error("Development/fake assessment — not a production OpenAI result.")
    st.write(
        f"Provider **{assess.model_provider}** / {assess.model_name} "
        f"({assess.status}) at {assess.assessed_at}"
    )
    if assess.result:
        st.write(
            f"Overall relevance: **{assess.result.get('overall_relevance')}**; "
            f"Source data: **{assess.result.get('source_data_sufficiency')}**"
        )
        prof = assess.result.get("professional_relevance") or {}
        st.write(prof.get("scope_summary", ""))
        with st.expander("Full assessment JSON"):
            st.json(assess.result)
        if detail.profile_labels:
            st.caption("Profile labels: " + json.dumps(detail.profile_labels))

st.markdown("### Deterministic ranking")
st.markdown("*Deterministic ranking*")
rank = detail.ranking
if rank.dynamic_rank:
    st.write(f"Dynamic position: **#{rank.dynamic_rank}**")
if rank.priority_band:
    st.write(f"Band: **{rank.priority_band.value}**")
if rank.status:
    st.write(f"Status: {rank.status.value}")
if rank.explanation:
    st.info(rank.explanation)
for factor in rank.factors:
    st.write(f"- {factor.code}: {factor.summary} ({factor.effect})")
if rank.warnings:
    st.warning("Warnings: " + ", ".join(rank.warnings))
if rank.ranking_method_version:
    st.caption(
        f"Method {rank.ranking_method_version} · config {rank.ranking_config_hash}"
    )

st.markdown("### Application / pursuit")
st.markdown(
    "*What you are doing after deciding to pursue — separate from review triage "
    "(SHORTLIST / INVESTIGATE / DISMISS).*"
)
pursuit = detail.pursuit
if pursuit is None:
    st.write("Not tracking as an application yet.")
    with st.form("start_pursuit_form"):
        start_notes = st.text_area("Notes (optional)")
        if st.form_submit_button("Start pursuing"):
            with session_factory() as session:
                PursuitTrackingService(session).start_pursuit(
                    opportunity_id,
                    notes=start_notes,
                )
                session.commit()
            st.success("Pursuit tracking started.")
            st.rerun()
else:
    st.write(f"**Status:** {pursuit.current_status.value}")
    if pursuit.is_terminal:
        st.caption("Terminal pursuit state.")
    st.write(f"Started: {pursuit.started_at}")
    if pursuit.submission_deadline:
        st.write(f"Submission deadline: {pursuit.submission_deadline}")
    if pursuit.submission_url:
        st.link_button("Submission URL", pursuit.submission_url)
    if pursuit.next_action:
        st.write(
            f"Next action: {pursuit.next_action} "
            f"({pursuit.next_action_date or 'no date'})"
        )
    if pursuit.reference_identifier:
        st.write(f"Reference: {pursuit.reference_identifier}")
    if pursuit.contact_name or pursuit.contact_email:
        st.write(
            f"Contact: {pursuit.contact_name or ''} "
            f"{pursuit.contact_organisation or ''} "
            f"{pursuit.contact_email or ''}"
        )

    if not pursuit.is_terminal:
        options = [s.value for s in PursuitStatus if s != pursuit.current_status]
        with st.form("pursuit_status_form"):
            new_status = st.selectbox("Record status transition", options)
            status_notes = st.text_area("Transition notes (optional)")
            if st.form_submit_button("Save status"):
                with session_factory() as session:
                    PursuitTrackingService(session).record_status_transition(
                        opportunity_id,
                        PursuitStatus(new_status),
                        notes=status_notes,
                    )
                    session.commit()
                st.success("Status recorded.")
                st.rerun()

    with st.form("pursuit_ops_form"):
        st.markdown("Update operational fields")
        deadline = st.date_input(
            "Submission deadline",
            value=pursuit.submission_deadline,
        )
        sub_url = st.text_input("Submission URL", value=pursuit.submission_url or "")
        next_act = st.text_input("Next action", value=pursuit.next_action or "")
        next_date = st.date_input(
            "Next action date",
            value=pursuit.next_action_date,
        )
        ref_id = st.text_input(
            "Reference / procurement id",
            value=pursuit.reference_identifier or "",
        )
        c_name = st.text_input("Contact name", value=pursuit.contact_name or "")
        c_org = st.text_input(
            "Contact organisation", value=pursuit.contact_organisation or ""
        )
        c_email = st.text_input("Contact email", value=pursuit.contact_email or "")
        if st.form_submit_button("Save operational fields"):
            with session_factory() as session:
                PursuitTrackingService(session).update_operational(
                    opportunity_id,
                    PursuitOperationalUpdate(
                        submission_deadline=deadline,
                        submission_url=sub_url,
                        next_action=next_act,
                        next_action_date=next_date,
                        contact_name=c_name,
                        contact_organisation=c_org,
                        contact_email=c_email,
                        reference_identifier=ref_id,
                    ),
                )
                session.commit()
            st.success("Operational fields updated.")
            st.rerun()

    if pursuit.history:
        with st.expander("Pursuit status history"):
            for entry in pursuit.history:
                st.write(
                    f"{entry.recorded_at}: **{entry.status.value}** — "
                    f"{entry.notes or ''}"
                )

st.markdown("### Human review")
st.markdown("*Review triage — should I consider this?*")
hr = detail.human_review
if hr.current_disposition:
    st.write(
        f"Current: **{hr.current_disposition.value}** at {hr.current_recorded_at}"
    )
    if hr.current_notes:
        st.write(hr.current_notes)
else:
    st.write("Not reviewed yet.")

with st.form("review_form"):
    disposition = st.selectbox(
        "Record disposition",
        [d.value for d in ReviewDisposition],
    )
    notes = st.text_area("Notes (optional)")
    submitted = st.form_submit_button("Save review")
    if submitted:
        with session_factory() as session:
            HumanReviewService(session).append_review(
                opportunity_id,
                ReviewDisposition(disposition),
                notes,
            )
            session.commit()
        st.success("Review recorded.")
        st.rerun()

if hr.history:
    with st.expander("Review history"):
        for disp, when, note in hr.history:
            st.write(f"{when}: **{disp.value}** — {note or ''}")
