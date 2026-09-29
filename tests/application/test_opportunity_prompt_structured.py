"""Assessment prompt includes source-neutral structured opportunity fields."""

from __future__ import annotations

from jobhunter.application.profile_assessment.digests import (
    compute_opportunity_content_digest,
)
from jobhunter.application.profile_assessment.opportunity_prompt import (
    build_opportunity_prompt_text,
)
from jobhunter.application.profile_assessment.source_sufficiency import (
    infer_source_data_sufficiency,
)
from jobhunter.domain.assessment_enums import OpportunityEvidenceField, SourceDataSufficiency
from jobhunter.domain.enums import OpportunityType
from jobhunter.domain.opportunity import Opportunity
from jobhunter.domain.opportunity_structured_facts import OpportunityStructuredFacts


def test_prompt_includes_structured_metadata() -> None:
    opp = Opportunity(
        title="GIS specialist",
        organisation="Client",
        description="A" * 500,
        opportunity_type=OpportunityType.CONSULTANCY,
        publication_date=__import__("datetime").date(2026, 9, 20),
        deadline=__import__("datetime").date(2026, 10, 15),
    )
    facts = OpportunityStructuredFacts(
        sectors=("Land Administration",),
        languages=("English", "French"),
        minimum_experience_years=8,
        organisation_type="Consulting firm",
        contract_type_label="Contract, 6 months",
    )
    prompt = build_opportunity_prompt_text(opp, facts)
    assert prompt[OpportunityEvidenceField.SECTORS.value] == "Land Administration"
    assert "English" in prompt[OpportunityEvidenceField.LANGUAGES.value]
    assert prompt[OpportunityEvidenceField.MINIMUM_EXPERIENCE.value] == "8"
    assert prompt[OpportunityEvidenceField.ORGANISATION_TYPE.value] == "Consulting firm"
    assert prompt[OpportunityEvidenceField.PUBLICATION_DATE.value] == "2026-09-20"
    assert prompt[OpportunityEvidenceField.DEADLINE.value] == "2026-10-15"
    assert prompt[OpportunityEvidenceField.CONTRACT_TYPE.value] == "Contract, 6 months"


def test_digest_includes_structured_facts() -> None:
    opp = Opportunity(title="T", description="body")
    facts = OpportunityStructuredFacts(sectors=("GIS",))
    d1 = compute_opportunity_content_digest(opp)
    d2 = compute_opportunity_content_digest(opp, facts)
    assert d1 != d2


def test_rich_description_is_adequate_sufficiency() -> None:
    opp = Opportunity(
        title="Senior role",
        description="Detailed requirements.\n" + ("x" * 450),
    )
    suff = infer_source_data_sufficiency(opp, primary_source_id="developmentaid-jobs")
    assert suff is SourceDataSufficiency.ADEQUATE
