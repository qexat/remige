"""
Tools to build configuration validators.
"""

from __future__ import annotations

import typing

from . import predicates

if typing.TYPE_CHECKING:
    import collections.abc


class ValidationField(typing.NamedTuple):
    """
    Represents a TOML field to validate.
    """

    name: str
    validator: typing.Callable[[typing.Any], bool]
    optional: bool


class Validator[T]:
    """
    Handles validation of the `T` node given a dumb value,
    usually extracted from parsing the TOML config file.
    """

    def __init__(
        self,
        fields: collections.abc.Iterable[ValidationField],
        *,
        for_type: type[T],
    ) -> None:
        self._fields = fields
        self._for_type = for_type

    @staticmethod
    def _check_field(
        field: typing.Any | None,
        validator: typing.Callable[[typing.Any], bool],
        *,
        optional: bool = False,
    ) -> bool:
        if field is None:
            return optional

        return validator(field)

    def validate(self, value: typing.Any) -> typing.TypeGuard[T]:
        """
        Return whether `value` is a valid `T` node.
        """

        if not predicates.is_any_dict(value):
            return False

        for field in self._fields:
            if not self._check_field(
                value.get(field.name),
                field.validator,
                optional=field.optional,
            ):
                return False

        return True


class Builder:
    """
    Builder for a node validator.

    Each method returns the builder so it can be chained.
    """

    def __init__(self) -> None:
        self._fields: list[ValidationField] = []

    def _add_field(
        self,
        name: str,
        validator: typing.Callable[[typing.Any], bool],
        *,
        optional: bool,
    ) -> None:
        self._fields.append(
            ValidationField(
                name,
                validator,
                optional=optional,
            )
        )

    def add_field(
        self,
        name: str,
        validator: typing.Callable[[typing.Any], bool],
        *,
        optional: bool = False,
    ) -> typing.Self:
        """
        Add a validation field given its `name`, a `validator`
        function that verifies that the field itself is valid,
        and whether it is `optional` or not.
        """

        self._add_field(name, validator, optional=optional)

        return self

    def build[T](self, *, for_type: type[T]) -> Validator[T]:
        """
        Construct the node validator for the type `T` and return
        it.

        This cannot be enforced, but `T` should be a subclass of
        `typing.TypedDict`.
        """

        return Validator(self._fields, for_type=for_type)
