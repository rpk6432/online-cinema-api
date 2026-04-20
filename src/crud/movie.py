from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from crud.base import CRUDBase
from models.movie import (
    Director,
    Genre,
    Movie,
    Star,
)


class CRUDMovie(CRUDBase[Movie]):
    async def get_detail(self, db: AsyncSession, movie_id: int) -> Movie | None:
        result = await db.execute(
            select(Movie)
            .options(
                selectinload(Movie.certification),
                selectinload(Movie.genres),
                selectinload(Movie.stars),
                selectinload(Movie.directors),
            )
            .where(Movie.id == movie_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        search: str | None = None,
        year: int | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        imdb_min: float | None = None,
        imdb_max: float | None = None,
        genre_id: int | None = None,
        certification_id: int | None = None,
        sort_by: str = "id",
        sort_order: str = "asc",
    ) -> list[Movie]:
        query = select(Movie).options(
            selectinload(Movie.certification),
            selectinload(Movie.genres),
        )

        if search:
            query = query.where(Movie.name.ilike(f"%{search}%"))
        if year is not None:
            query = query.where(Movie.year == year)
        if year_min is not None:
            query = query.where(Movie.year >= year_min)
        if year_max is not None:
            query = query.where(Movie.year <= year_max)
        if imdb_min is not None:
            query = query.where(Movie.imdb >= imdb_min)
        if imdb_max is not None:
            query = query.where(Movie.imdb <= imdb_max)
        if certification_id is not None:
            query = query.where(Movie.certification_id == certification_id)
        if genre_id is not None:
            query = query.where(Movie.genres.any(Genre.id == genre_id))

        sort_column = getattr(Movie, sort_by, Movie.id)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count_filtered(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        year: int | None = None,
        year_min: int | None = None,
        year_max: int | None = None,
        imdb_min: float | None = None,
        imdb_max: float | None = None,
        genre_id: int | None = None,
        certification_id: int | None = None,
    ) -> int:
        from sqlalchemy import func

        query = select(func.count()).select_from(Movie)

        if search:
            query = query.where(Movie.name.ilike(f"%{search}%"))
        if year is not None:
            query = query.where(Movie.year == year)
        if year_min is not None:
            query = query.where(Movie.year >= year_min)
        if year_max is not None:
            query = query.where(Movie.year <= year_max)
        if imdb_min is not None:
            query = query.where(Movie.imdb >= imdb_min)
        if imdb_max is not None:
            query = query.where(Movie.imdb <= imdb_max)
        if certification_id is not None:
            query = query.where(Movie.certification_id == certification_id)
        if genre_id is not None:
            query = query.where(Movie.genres.any(Genre.id == genre_id))

        result = await db.execute(query)
        return result.scalar_one()

    async def create_movie(self, db: AsyncSession, **kwargs: Any) -> Movie:
        genre_ids: list[int] = kwargs.pop("genre_ids", [])
        star_ids: list[int] = kwargs.pop("star_ids", [])
        director_ids: list[int] = kwargs.pop("director_ids", [])

        movie = Movie(**kwargs)

        if genre_ids:
            genre_result = await db.execute(
                select(Genre).where(Genre.id.in_(genre_ids))
            )
            movie.genres = list(genre_result.scalars().all())

        if star_ids:
            star_result = await db.execute(
                select(Star).where(Star.id.in_(star_ids))
            )
            movie.stars = list(star_result.scalars().all())

        if director_ids:
            director_result = await db.execute(
                select(Director).where(Director.id.in_(director_ids))
            )
            movie.directors = list(director_result.scalars().all())

        db.add(movie)
        await db.commit()
        await db.refresh(
            movie,
            attribute_names=[
                "certification",
                "genres",
                "stars",
                "directors",
            ],
        )
        return movie

    async def update_movie(
        self, db: AsyncSession, movie: Movie, **kwargs: Any
    ) -> Movie:
        genre_ids: list[int] | None = kwargs.pop("genre_ids", None)
        star_ids: list[int] | None = kwargs.pop("star_ids", None)
        director_ids: list[int] | None = kwargs.pop("director_ids", None)

        for key, value in kwargs.items():
            setattr(movie, key, value)

        if genre_ids is not None:
            genre_result = await db.execute(
                select(Genre).where(Genre.id.in_(genre_ids))
            )
            movie.genres = list(genre_result.scalars().all())

        if star_ids is not None:
            star_result = await db.execute(
                select(Star).where(Star.id.in_(star_ids))
            )
            movie.stars = list(star_result.scalars().all())

        if director_ids is not None:
            director_result = await db.execute(
                select(Director).where(Director.id.in_(director_ids))
            )
            movie.directors = list(director_result.scalars().all())

        await db.commit()
        await db.refresh(
            movie,
            attribute_names=[
                "certification",
                "genres",
                "stars",
                "directors",
            ],
        )
        return movie


movie_crud = CRUDMovie(Movie)
