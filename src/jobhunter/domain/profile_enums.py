"""Enumerations for professional evidence."""

from __future__ import annotations

from enum import StrEnum


class CapabilityCategory(StrEnum):
    DOMAIN = "DOMAIN"
    SYSTEM_TYPE = "SYSTEM_TYPE"
    SYSTEM_DEVELOPMENT = "SYSTEM_DEVELOPMENT"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    QUALITY_ASSURANCE = "QUALITY_ASSURANCE"
    MANAGEMENT_STRATEGY = "MANAGEMENT_STRATEGY"
    CAPACITY_DEVELOPMENT = "CAPACITY_DEVELOPMENT"


class ProfileDocumentType(StrEnum):
    CV = "CV"
    PROFESSIONAL_SERVICES = "PROFESSIONAL_SERVICES"
    PROJECT_DATA = "PROJECT_DATA"
    OTHER = "OTHER"
