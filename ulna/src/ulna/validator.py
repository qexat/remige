"""
Tools to build configuration validators.
"""

from __future__ import annotations

import dataclasses
import typing

import option
import result

from . import datatypes
from . import predicates

if typing.TYPE_CHECKING:
    import collections.abc

# TODO: build a proper typechecker


@dataclasses.dataclass(slots=True, frozen=True)
class FieldTypeError(datatypes.AbstractError):
    """
    Error when a field is provided with a value of an incorrect
    type.
    """

    field_name: str
    section_name: str | None
    expected_type: str

    @typing.override
    def render_message(self) -> str:
        section = _make_section_message_portion(self.section_name)

        return (
            f"field {self.field_name!r}{section} has an incorrect type\n"
            f"  expected value of type {self.expected_type!r}"
        )


@dataclasses.dataclass(slots=True, frozen=True)
class SectionKindError(datatypes.AbstractError):
    """
    Error when a field that isn't a table is provided in place
    of a section.
    """

    section_name: str

    @typing.override
    def render_message(self) -> str:
        return (
            f"section {self.section_name!r} was incorrectly provided "
            f"as a field"
        )


@dataclasses.dataclass(slots=True, frozen=True)
class MissingFieldError(datatypes.AbstractError):
    """
    Error when a non-optional field is not provided.
    """

    field_name: str
    section_name: str | None

    @typing.override
    def render_message(self) -> str:
        section = _make_section_message_portion(self.section_name)

        return f"field {self.field_name!r}{section} is missing"


@dataclasses.dataclass(slots=True, frozen=True)
class MissingSectionError(datatypes.AbstractError):
    """
    Error when a non-optional section is not provided.
    """

    section_name: str

    @typing.override
    def render_message(self) -> str:
        return f"section {self.section_name!r} is missing"


@dataclasses.dataclass(slots=True, frozen=True)
class NonexistentFieldError(datatypes.AbstractError):
    """
    Error when a field is provided but is not recognized by
    ulna's configuration scheme.
    """

    field_name: str
    section_name: str | None

    @typing.override
    def render_message(self) -> str:
        section = _make_section_message_portion(self.section_name)

        return f"field {self.field_name!r}{section} is not recognized"


type ValidationError = (
    FieldTypeError
    | SectionKindError
    | MissingFieldError
    | MissingSectionError
    | NonexistentFieldError
)


def _make_section_message_portion(section_name: str | None) -> str:
    return (
        "" if section_name is None else f" (in section {section_name!r})"
    )


class ValidationSection(typing.NamedTuple):
    """
    Represents a TOML section to validate.
    """

    name: str
    validator: Validator[typing.Any]
    optional: bool


class ValidationField(typing.NamedTuple):
    """
    Represents a TOML field to validate.
    """

    name: str
    validator: datatypes.Predicate[typing.Any]
    optional: bool


class Validator[T]:
    """
    Handles validation of the `T` node given a dumb value,
    usually extracted from parsing the TOML config file.
    """

    def __init__(
        self,
        *,
        name: str | None = None,
        fields: collections.abc.Iterable[ValidationField],
        sections: collections.abc.Iterable[ValidationSection],
        for_type: type[T],
    ) -> None:
        self.section_name: typing.Final = name

        self._fields = list(fields)
        self._sections = list(sections)
        self._for_type = for_type

    @property
    def name(self) -> str:
        """
        Name of the validated node.
        """

        return "config" if self.section_name is None else self.section_name

    def _get_entry_names(self) -> set[str]:
        return {field.name for field in self._fields} | {
            section.name for section in self._sections
        }

    def _check_field(
        self,
        name: str,
        value: typing.Any | None,
        validator: datatypes.Predicate[typing.Any],
        *,
        optional: bool,
    ) -> result.Result[option.Option[typing.Any], ValidationError]:
        if value is None:
            if not optional:
                return result.Err(
                    MissingFieldError(name, self.section_name)
                )
            return result.Ok(option.Nothing())

        if not validator(value):
            return result.Err(
                FieldTypeError(
                    name,
                    self.section_name,
                    validator.name,
                )
            )

        return result.Ok(option.Some(value))

    @staticmethod
    def _check_section[SectionT](
        section: typing.Any | None,
        validator: Validator[SectionT],
        *,
        optional: bool,
    ) -> result.Result[option.Option[SectionT], list[ValidationError]]:
        if section is None:
            if not optional:
                return result.Err([MissingSectionError(validator.name)])

            return result.Ok(option.Nothing())

        return validator.validate(section).map(option.Some)

    def _get_unrecognized_entries(
        self,
        data: dict[str, typing.Any],
    ) -> set[str]:
        recognized_entries = self._get_entry_names()

        return {key for key in data if key not in recognized_entries}

    def validate(
        self,
        data: typing.Any,
    ) -> result.Result[T, list[ValidationError]]:
        """
        Return whether `value` is a valid `T` node.
        """

        if not predicates.is_any_dict(data):
            return result.Err([SectionKindError(self.name)])

        errors: list[ValidationError] = []

        unrecognized_entries = self._get_unrecognized_entries(data)

        for entry in unrecognized_entries:
            errors.append(NonexistentFieldError(entry, self.section_name))  # noqa: PERF401

        for field in self._fields:
            field_value = data.get(field.name)

            match self._check_field(
                field.name,
                field_value,
                field.validator,
                optional=field.optional,
            ):
                case result.Err(error):
                    errors.append(error)
                case result.Ok():
                    pass

        for section in self._sections:
            match self._check_section(
                data.get(section.name),
                section.validator,
                optional=section.optional,
            ):
                case result.Err(section_errors):
                    errors.extend(section_errors)
                case result.Ok():
                    pass

        if errors:
            return result.Err(errors)

        return result.Ok(typing.cast("T", data))


class Builder:
    """
    Builder for a node validator.

    Each method returns the builder so it can be chained.
    """

    def __init__(self, name: str | None = None) -> None:
        self.name: typing.Final = name
        self._fields: list[ValidationField] = []
        self._sections: list[ValidationSection] = []

    def add_field(
        self,
        name: str,
        validator: datatypes.Predicate[typing.Any],
        *,
        optional: bool = False,
    ) -> typing.Self:
        """
        Add a validation field given its `name`, a `validator`
        function that verifies that the field itself is valid,
        and whether it is `optional` or not.
        """

        self._fields.append(
            ValidationField(
                name,
                validator,
                optional=optional,
            )
        )

        return self

    def add_section(
        self,
        validator: Validator[typing.Any],
        *,
        optional: bool = False,
    ) -> typing.Self:
        """
        Add a validation section given a `validator` class for
        the section and whether it is `optional` or not.
        """

        self._sections.append(
            ValidationSection(
                validator.name,
                validator,
                optional=optional,
            )
        )

        return self

    def build[T](self, *, for_type: type[T]) -> Validator[T]:
        """
        Construct the node validator for the type `T` and return
        it.

        This cannot be enforced, but `T` should be a subclass of
        `typing.TypedDict`.
        """

        return Validator(
            name=self.name,
            fields=self._fields,
            sections=self._sections,
            for_type=for_type,
        )


def check_type[T](
    value: typing.Any,
    predicate: typing.Callable[[typing.Any], typing.TypeGuard[T]],
) -> option.Option[T]:
    """
    Determine whether `value` satisfies the type `predicate`.
    """

    if predicate(value):
        return option.Some(value)

    return option.Nothing()
