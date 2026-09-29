"""Streamlit rendering helpers for opportunity detail (Phase 16)."""

from __future__ import annotations

import streamlit as st

from jobhunter.application.display_labels import (
    label_eligibility_status,
    label_lifecycle_status,
    label_priority_band,
    label_pursuit_status,
    label_ranking_status,
    label_review_disposition,
)
from jobhunter.application.review.dtos import (
    AssessmentSectionView,
    EligibilitySectionView,
    HumanReviewSectionView,
    OpportunityFactsSectionView,
    OpportunityDetailView,
    RankingSectionView,
)


def render_facts_section(facts: OpportunityFactsSectionView) -> None:
    st.markdown("## Opportunity")
    st.header(facts.title)
    link_cols = st.columns(2)
    with link_cols[0]:
        if facts.primary_external_url:
            st.link_button("Open source listing", facts.primary_external_url)
    with link_cols[1]:
        if facts.application_url:
            st.link_button("Open application URL", facts.application_url)
    cols = st.columns(2)
    with cols[0]:
        st.write(f"**Organisation:** {facts.organisation or '—'}")
        if facts.organisation_type:
            st.write(f"**Organisation type:** {facts.organisation_type}")
        st.write(f"**Location:** {facts.location or '—'}")
        st.write(f"**Type:** {facts.opportunity_type}")
        if facts.contract_type_label:
            st.write(f"**Contract / job type:** {facts.contract_type_label}")
        st.write(
            f"**Lifecycle:** {label_lifecycle_status(facts.lifecycle_status.value)}"
        )
    with cols[1]:
        st.write(
            f"**Eligibility (stored):** "
            f"{label_eligibility_status(facts.eligibility_status.value)}"
        )
        st.write(f"**Deadline:** {facts.deadline or '—'}")
        st.write(f"**Publication:** {facts.publication_date or '—'}")
        if facts.expected_start_date:
            st.write(f"**Expected start:** {facts.expected_start_date}")
        if facts.minimum_experience_years is not None:
            st.write(
                f"**Minimum experience:** {facts.minimum_experience_years} year(s)"
            )
        if facts.languages:
            st.write(f"**Languages:** {', '.join(facts.languages)}")
        if facts.sectors:
            st.write(f"**Sectors:** {', '.join(facts.sectors)}")
        if facts.content_last_updated:
            st.write(f"**Last updated (source):** {facts.content_last_updated}")
        if facts.source_status:
            st.write(f"**Source status:** {facts.source_status}")
    if facts.description:
        st.text_area("Description", facts.description, height=200, disabled=True)
    if facts.source_links:
        st.markdown("**Sources**")
        for link in facts.source_links:
            st.write(
                f"- **{link.source_name}** — ref {link.source_reference or '—'} "
                f"(last seen {link.last_seen_at})"
            )
            if link.external_url:
                st.link_button(
                    f"Listing — {link.source_name}",
                    link.external_url,
                    key=f"link-{link.source_id}",
                )
            if link.application_url:
                st.link_button(
                    f"Application — {link.source_name}",
                    link.application_url,
                    key=f"app-link-{link.source_id}",
                )


def render_eligibility_section(elig: EligibilitySectionView | None) -> None:
    st.markdown("## Eligibility")
    st.caption("Deterministic rules for the active search strategy revision.")
    if elig is None:
        st.info("No eligibility decision recorded for the active strategy revision.")
        return
    st.write(
        f"**Decision:** {label_eligibility_status(elig.status.value)} "
        f"(evaluated {elig.evaluated_at})"
    )
    if not elig.rule_results:
        st.write("No rule breakdown stored.")
        return
    st.dataframe(
        [
            {
                "Rule": rule.rule_code,
                "Kind": rule.rule_kind,
                "Outcome": rule.outcome,
                "Review?": "Yes" if rule.suggests_review else "",
                "Summary": rule.summary or "",
            }
            for rule in elig.rule_results
        ],
        use_container_width=True,
        hide_index=True,
    )
    for rule in elig.rule_results:
        if rule.evidence:
            st.caption(f"{rule.rule_code}: {rule.evidence}")


def render_assessment_section(assess: AssessmentSectionView) -> None:
    st.markdown("## Profile assessment")
    st.caption("AI inference — not source fact.")
    operator = assess.operator
    if operator is None:
        st.warning(assess.explanation or "No assessment information.")
        return
    if operator.situation.name == "FAKE_VISIBLE" or assess.is_fake:
        st.error(operator.headline)
    elif not assess.present:
        st.warning(operator.headline)
    else:
        st.success(operator.headline)
    if operator.detail:
        st.write(operator.detail)
    if operator.sufficiency_notice:
        st.info(operator.sufficiency_notice)
    if assess.present:
        st.write(
            f"Assessed **{assess.assessed_at}** · "
            f"{assess.model_provider} / {assess.model_name}"
        )
        if assess.validation_warnings:
            st.warning("Warnings: " + "; ".join(assess.validation_warnings))
        if assess.provider_error and not assess.present:
            st.code(assess.provider_error)
    elif assess.provider_error:
        st.code(assess.provider_error)

    structured = operator.structured
    if structured:
        st.markdown("### Assessment summary")
        summary_cols = st.columns(2)
        summary_cols[0].metric("Overall relevance", structured.overall_relevance)
        summary_cols[1].metric(
            "Source data", structured.source_data_sufficiency
        )
        if structured.scope_summary:
            st.write(structured.scope_summary)
        if structured.domain_tags:
            st.write("Domain tags: " + ", ".join(structured.domain_tags))
        st.caption(
            f"Delivery mode: {structured.delivery_mode_inference} · "
            f"Seniority: {structured.seniority_inference}"
        )

        st.markdown("### Service alignment")
        if structured.service_alignments:
            st.dataframe(
                [
                    {
                        "Service": row.service_label,
                        "Alignment": row.alignment,
                        "Basis": row.basis,
                        "Explanation": row.rationale,
                    }
                    for row in structured.service_alignments
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("No service alignment rows in this assessment.")

        st.markdown("### Theme alignment")
        if structured.theme_alignments:
            st.dataframe(
                [
                    {
                        "Theme": row.theme_key,
                        "Alignment": row.alignment,
                        "Basis": row.basis,
                        "Explanation": row.rationale,
                    }
                    for row in structured.theme_alignments
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("No theme alignment rows in this assessment.")

        for title, items in (
            ("Strengths", structured.strengths),
            ("Gaps", structured.gaps),
            ("Uncertainties", structured.uncertainties),
        ):
            st.markdown(f"### {title}")
            if items:
                for line in items:
                    st.write(f"- {line}")
            else:
                st.write(f"No {title.lower()} recorded for this assessment.")

        st.markdown("### Evidence")
        if structured.evidence_rows:
            st.dataframe(
                [
                    {
                        "Type": row.evidence_type,
                        "Profile item": row.entity_label,
                        "Alignment": row.alignment,
                        "Basis": row.basis,
                        "Explanation": row.rationale,
                    }
                    for row in structured.evidence_rows
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.write("No structured evidence rows in this assessment.")

        if structured.rationale:
            st.markdown("### Rationale")
            st.write(structured.rationale)

    if operator.show_raw_json and assess.result:
        with st.expander("Full assessment JSON (diagnostic)", expanded=False):
            st.caption(
                "Raw structured model output as persisted. Use for debugging only."
            )
            st.json(assess.result)
    elif not assess.present:
        st.caption("No assessment payload to display.")


def render_ranking_section(rank: RankingSectionView) -> None:
    st.markdown("## Ranking")
    st.caption("Deterministic ranking for the active strategy revision.")
    if rank.status:
        st.write(f"**Status:** {label_ranking_status(rank.status.value)}")
    if rank.priority_band:
        st.write(f"**Band:** {label_priority_band(rank.priority_band.value)}")
    if rank.dynamic_rank:
        st.write(f"**Queue position:** #{rank.dynamic_rank}")
    if rank.explanation:
        st.info(rank.explanation)
    if rank.unranked_reason:
        st.write(f"Unranked reason: {rank.unranked_reason}")
    if rank.exclusion_reason:
        st.write(f"Exclusion reason: {rank.exclusion_reason}")
    if rank.factors:
        st.dataframe(
            [
                {
                    "Factor": factor.code,
                    "Effect": factor.effect,
                    "Explanation": factor.summary or "",
                }
                for factor in rank.factors
            ],
            use_container_width=True,
            hide_index=True,
        )
    elif rank.status:
        st.write("No ranking factor breakdown stored.")
    if rank.warnings:
        st.warning("Warnings: " + "; ".join(rank.warnings))
    if rank.ranking_method_version:
        st.caption(
            f"Method {rank.ranking_method_version} · config {rank.ranking_config_hash}"
        )


def render_human_review_section(hr: HumanReviewSectionView) -> None:
    st.markdown("## Human review")
    st.caption("Triage — should I consider this opportunity?")
    if hr.current_disposition:
        st.write(
            f"**Current:** {label_review_disposition(hr.current_disposition.value)} "
            f"at {hr.current_recorded_at}"
        )
        if hr.current_notes:
            st.write(hr.current_notes)
    else:
        st.write("Not reviewed yet.")
    if hr.history:
        with st.expander("Review history", expanded=False):
            for disp, when, note in hr.history:
                st.write(
                    f"{when}: **{label_review_disposition(disp.value)}** — "
                    f"{note or ''}"
                )
