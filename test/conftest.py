import ast
from typing import Any, Callable

import pytest

from pytoschema.annotations import AstAnnotationElement


TEST_TYPING_NAMESPACE = {
    "Any": {"typing.Any"},
    "Dict": {"typing.Dict"},
    "List": {"typing.List"},
    "Literal": {"typing.Literal"},
    "Optional": {"typing.Optional"},
    "TypedDict": {"typing.TypedDict"},
    "Union": {"typing.Union"},
}


def build_ast_annotation_element(text: str) -> AstAnnotationElement:
    return ast.parse(text).body[0].value


def assert_expected_value_or_exception(callback: Callable, expected: Any):
    if isinstance(expected, Exception):
        with pytest.raises(expected.__class__) as exception:
            callback()
        assert str(exception.value) == str(expected)
    else:
        assert callback() == expected
