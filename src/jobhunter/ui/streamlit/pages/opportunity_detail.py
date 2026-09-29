"""Single opportunity review detail."""

from __future__ import annotations

import streamlit as st

from jobhunter.application.display_labels import (
    label_pursuit_status,
    label_review_disposition,
)
from jobhunter.application.pursuit import (
    PursuitOperationalUpdate,
    PursuitTrackingService,
)
from jobhunter.application.review import HumanReviewService, OpportunityDetailService
from jobhunter.domain.pursuit_enums import PursuitStatus
from jobhunter.domain.review_enums import ReviewDisposition
from jobhunter.ui.streamlit.bootstrap import allow_fake_results, get_session_factory
from jobhunter.ui.streamlit.detail_sections import (
    render_assessment_section,
    render_eligibility_section,
    render_facts_section,
    render_human_review_section,
    render_ranking_section,
)
from jobhunter.ui.streamlit.navigation import resolve_opportunity_id_from_url
from jobhunter.ui.streamlit.sidebar import render_sidebar

render_sidebar()

st.title("Opportunity detail")

session_factory = get_session_factory()
opportunity_id = (
    resolve_opportunity_id_from_url()
    or st.session_state.get("selected_opportunity_id")
    or ""
)

if not opportunity_id:
    st.info(
        "Open an opportunity from **Opportunities** or **Applications**, or use a "
        "bookmark link with `?opportunity_id=…`."
    )
    st.stop()

with session_factory() as session:
    detail = OpportunityDetailService(session).get_detail(
        opportunity_id, allow_fake=allow_fake_results()
    )

if detail is None:
    st.error("Opportunity not found. Check the link or pick another opportunity.")
    st.stop()

render_facts_section(detail.facts)
render_eligibility_section(detail.eligibility)
render_assessment_section(detail.assessment)
render_ranking_section(detail.ranking)
render_human_review_section(detail.human_review)

st.markdown("## Application / pursuit")
st.caption(
    "Workflow after you decide to pursue — separate from review triage "
    "(SHORTLIST / INVESTIGATE / DISMISS)."
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
    st.write(
        f"**Status:** {label_pursuit_status(pursuit.current_status.value)}"
    )
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
            new_status = st.selectbox(
                "Record status transition",
                options,
                format_func=label_pursuit_status,
            )
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
        with st.expander("Pursuit status history", expanded=False):
            for entry in pursuit.history:
                st.write(
                    f"{entry.recorded_at}: "
                    f"**{label_pursuit_status(entry.status.value)}** — "
                    f"{entry.notes or ''}"
                )

with st.form("review_form"):
    st.markdown("## Record review disposition")
    disposition = st.selectbox(
        "Disposition",
        [d.value for d in ReviewDisposition],
        format_func=label_review_disposition,
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
