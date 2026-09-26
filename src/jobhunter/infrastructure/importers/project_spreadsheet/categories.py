"""Map workbook group labels to CapabilityCategory."""

from __future__ import annotations

from jobhunter.domain.profile_enums import CapabilityCategory

GROUP_TO_CATEGORY: dict[str, CapabilityCategory] = {
    "Domain": CapabilityCategory.DOMAIN,
    "Type of System": CapabilityCategory.SYSTEM_TYPE,
    "System Development": CapabilityCategory.SYSTEM_DEVELOPMENT,
    "Data and Analysis": CapabilityCategory.DATA_ANALYSIS,
    "Quality Assurance": CapabilityCategory.QUALITY_ASSURANCE,
    "Management and Strategy": CapabilityCategory.MANAGEMENT_STRATEGY,
    "Capacity Development": CapabilityCategory.CAPACITY_DEVELOPMENT,
}
