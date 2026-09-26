"""SQLAlchemy models for professional evidence (Phase 3B)."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from jobhunter.infrastructure.persistence.base import Base


class ProfileDocumentRow(Base):
    __tablename__ = "profile_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(2048))
    version_label: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text())


class ProfessionalProfileRow(Base):
    __tablename__ = "professional_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    positioning_summary: Mapped[str | None] = mapped_column(Text())
    primary_cv_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("profile_documents.id", ondelete="SET NULL"),
        nullable=True,
    )


class ProfessionalServiceRow(Base):
    __tablename__ = "professional_services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("profile_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )


class AssignmentRow(Base):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_record_id: Mapped[str | None] = mapped_column(String(64))
    sequence: Mapped[int | None] = mapped_column(Integer())
    project_name: Mapped[str] = mapped_column(String(1024), nullable=False)
    role: Mapped[str | None] = mapped_column(String(512))
    beneficiary: Mapped[str | None] = mapped_column(String(512))
    donor: Mapped[str | None] = mapped_column(String(512))
    country: Mapped[str | None] = mapped_column(String(255))
    period_text: Mapped[str | None] = mapped_column(String(255))
    working_days: Mapped[int | None] = mapped_column(Integer())
    last_active_year: Mapped[int | None] = mapped_column(Integer())
    description: Mapped[str | None] = mapped_column(Text())
    responsibilities: Mapped[str | None] = mapped_column(Text())
    tools_technologies_text: Mapped[str | None] = mapped_column(Text())
    web_link: Mapped[str | None] = mapped_column(String(2048))
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("profile_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )

    capability_links: Mapped[list[AssignmentCapabilityRow]] = relationship(
        back_populates="assignment"
    )


class CapabilityRow(Base):
    __tablename__ = "capabilities"
    __table_args__ = (
        UniqueConstraint("code", name="uq_capabilities_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("profile_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )

    assignment_links: Mapped[list[AssignmentCapabilityRow]] = relationship(
        back_populates="capability"
    )


class AssignmentCapabilityRow(Base):
    __tablename__ = "assignment_capabilities"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "capability_id",
            name="uq_assignment_capabilities_assignment_capability",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    assignment_id: Mapped[str] = mapped_column(
        ForeignKey("assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capability_id: Mapped[str] = mapped_column(
        ForeignKey("capabilities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("profile_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )

    assignment: Mapped[AssignmentRow] = relationship(back_populates="capability_links")
    capability: Mapped[CapabilityRow] = relationship(back_populates="assignment_links")


class SkillRow(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text())
    cv_emphasized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("profile_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )


class CountryExperienceRow(Base):
    __tablename__ = "country_experiences"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id",
            "country",
            name="uq_country_experiences_source_document_country",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    country: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text())
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("profile_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )


class LanguageCapabilityRow(Base):
    __tablename__ = "language_capabilities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    language: Mapped[str] = mapped_column(String(128), nullable=False)
    proficiency_text: Mapped[str | None] = mapped_column(String(512))
    cefr_level: Mapped[str | None] = mapped_column(String(16))
    notes: Mapped[str | None] = mapped_column(Text())
    source_document_id: Mapped[str | None] = mapped_column(
        ForeignKey("profile_documents.id", ondelete="RESTRICT"),
        nullable=True,
    )
