from datetime import date

from sqlalchemy import ForeignKey, Index, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Retraction(Base):
    __tablename__ = "retractions"

    record_id: Mapped[int] = mapped_column(primary_key=True)

    # Required
    title: Mapped[str] = mapped_column(Text)
    journal: Mapped[str] = mapped_column(index=True)
    retraction_nature: Mapped[str] = mapped_column(index=True)
    paywalled: Mapped[str]  # Yes/No/Unknown

    # Nullable
    publisher: Mapped[str | None] = mapped_column(index=True)
    article_type: Mapped[str | None]
    institution: Mapped[str | None] = mapped_column(Text)
    urls: Mapped[str | None] = mapped_column(Text)
    authors_raw: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    # Dates - nullable
    retraction_date: Mapped[date | None] = mapped_column(index=True)
    original_paper_date: Mapped[date | None]

    # Identifiers - nullable
    retraction_doi: Mapped[str | None] = mapped_column(index=True)
    retraction_pubmed_id: Mapped[int | None] = mapped_column(index=True)
    original_paper_doi: Mapped[str | None] = mapped_column(index=True)
    original_paper_pubmed_id: Mapped[int | None] = mapped_column(index=True)

    __table_args__ = (
        Index("ix_retractions_original_doi_normalized", func.lower(func.trim(original_paper_doi))),
        Index("ix_retractions_retraction_doi_normalized", func.lower(func.trim(retraction_doi))),
    )

    # Relationships
    countries: Mapped[list["RetractionCountry"]] = relationship(
        back_populates="retraction", cascade="all, delete-orphan"
    )
    reasons: Mapped[list["RetractionReason"]] = relationship(
        back_populates="retraction", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["RetractionSubject"]] = relationship(
        back_populates="retraction", cascade="all, delete-orphan"
    )


class RetractionCountry(Base):
    __tablename__ = "retraction_countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    country: Mapped[str] = mapped_column(index=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("retractions.record_id"), index=True)

    retraction: Mapped["Retraction"] = relationship(
        back_populates = "countries"
    )

class RetractionReason(Base):
    __tablename__ = "retraction_reasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    reason: Mapped[str] = mapped_column(index=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("retractions.record_id"), index=True)

    retraction: Mapped["Retraction"] = relationship(
        back_populates="reasons"
    )


class RetractionSubject(Base):
    __tablename__ = "retraction_subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(index=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("retractions.record_id"), index=True)

    retraction: Mapped["Retraction"] = relationship(
        back_populates="subjects"
    )


class DatasetImport(Base):
    __tablename__ = "dataset_import"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_filename: Mapped[str]
    source_sha256: Mapped[str]
    imported_at: Mapped[str]
    record_count: Mapped[int]
    api_version: Mapped[str]
