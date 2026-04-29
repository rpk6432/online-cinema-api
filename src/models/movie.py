import uuid as _uuid
from decimal import Decimal

from sqlalchemy import (
    Column,
    ForeignKey,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

# M2M association tables

movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

movie_stars = Table(
    "movie_stars",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("star_id", ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True),
)

movie_directors = Table(
    "movie_directors",
    Base.metadata,
    Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# Catalog models


class Certification(Base):
    __tablename__ = "certifications"

    name: Mapped[str] = mapped_column(String(100), unique=True)

    movies: Mapped[list[Movie]] = relationship(back_populates="certification")


class Genre(Base):
    __tablename__ = "genres"

    name: Mapped[str] = mapped_column(String(100), unique=True)

    movies: Mapped[list[Movie]] = relationship(
        secondary=movie_genres, back_populates="genres"
    )


class Star(Base):
    __tablename__ = "stars"

    name: Mapped[str] = mapped_column(String(255), unique=True)

    movies: Mapped[list[Movie]] = relationship(
        secondary=movie_stars, back_populates="stars"
    )


class Director(Base):
    __tablename__ = "directors"

    name: Mapped[str] = mapped_column(String(255), unique=True)

    movies: Mapped[list[Movie]] = relationship(
        secondary=movie_directors, back_populates="directors"
    )


# Movie model


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (UniqueConstraint("name", "year", "time"),)

    uuid: Mapped[_uuid.UUID] = mapped_column(
        unique=True, default=_uuid.uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    year: Mapped[int]
    time: Mapped[int]
    imdb: Mapped[float]
    votes: Mapped[int]
    meta_score: Mapped[float | None]
    gross: Mapped[float | None]
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    certification_id: Mapped[int | None] = mapped_column(
        ForeignKey("certifications.id"), default=None
    )

    certification: Mapped[Certification | None] = relationship(back_populates="movies")
    genres: Mapped[list[Genre]] = relationship(
        secondary=movie_genres, back_populates="movies"
    )
    stars: Mapped[list[Star]] = relationship(
        secondary=movie_stars, back_populates="movies"
    )
    directors: Mapped[list[Director]] = relationship(
        secondary=movie_directors, back_populates="movies"
    )
