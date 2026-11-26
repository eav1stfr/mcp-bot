from collections.abc import Sequence
from typing import get_args

from sqlmodel import select

from app.common.dependencies import DBSessionDep
from app.common.exceptions import NotFound
from app.common.models import Model
from app.config.base import CONFIG


class ModelRepository[T: Model]:
    """Base repository class for database models.

    Provides common CRUD operations that can be inherited by specific
    repositories.
    Specific repositories can add domain-specific query methods.

    Example:
    ```
        class MoviesRepository(ModelRepository[Movie]):
            default_model = Movie

            def get_by_title(self, title: str) -> Movie | None:
                # Custom method
                ...
    ```
    """

    default_model: type[T] = NotImplemented
    page_size: int = CONFIG.DEFAULT_PAGE_SIZE

    def __init__(self, session: DBSessionDep):
        self.session = session

        # Check type parameter
        bases = get_args(self.__orig_bases__[0])  # type: ignore[attr-defined]
        cname = self.__class__.__name__
        if not bases:
            raise NotImplementedError(
                f"Can't instantiate class {cname} "
                "without specifying the type parameter!"
            )
        if not issubclass(bases[0], Model):
            raise TypeError(
                f"Can't instantiate class {cname} "
                f"with type parameter {bases[0]}! "
                "Should be a subclass of `Model`."
            )
        if self.default_model == NotImplemented:
            raise NotImplementedError(
                f"Can't instantiate class {cname} "
                "without an initialization for the abstract attribute "
                "'default_model'!"
            )

    def get(self, native_id: int | str) -> T | None:
        """Get entity by ID"""
        return self.session.get(self.default_model, native_id)

    def get_or_404(
        self, native_id: int | str, message: str | None = None
    ) -> T:
        """Get entity by ID or raise NotFound exception"""
        if instance := self.get(native_id):
            return instance
        if message:
            raise NotFound(message)
        raise NotFound(
            f"{self.default_model.__name__} with id {native_id} not found."
        )

    def create(self, model: T) -> T:
        """Create a new entity"""
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return model

    def update(self, model: T) -> T:
        """Update an existing entity"""
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return model

    def update_without_commit(self, model: T) -> T:
        """Update an existing entity without commit"""
        self.session.add(model)
        self.session.flush()
        self.session.refresh(model)
        return model

    def delete(self, native_id: int | str) -> bool:
        """Delete entity by ID. Returns True if deleted, False if not found"""
        if instance := self.get(native_id):
            self.session.delete(instance)
            self.session.commit()
            return True
        return False

    def get_all(self) -> Sequence[T]:
        """Get all entities"""
        statement = select(self.default_model)
        return self.session.exec(statement).all()

    def get_page(
        self, page: int = 0, page_size: int | None = None
    ) -> Sequence[T]:
        """A page of entities; page 0 without a page size returns them all"""
        statement = select(self.default_model)

        if page_size:
            statement = statement.offset(page * page_size).limit(page_size)
        elif page:
            statement = statement.offset(page * self.page_size).limit(
                self.page_size
            )

        return self.session.exec(statement).all()

    def commit(self) -> None:
        self.session.commit()
