import pytest

from pytoschema.annotations import AstNameOrAttribute, AstAnnotationElement
from pytoschema.common import (
    init_typing_namespace,
    init_name_to_schema_map,
    get_ast_name_or_attribute_string,
    InvalidTypeAnnotation,
)

from .conftest import build_ast_annotation_element


def test_init_typing_namespace():
    assert init_typing_namespace() == {
        "Any": set(),
        "Dict": set(),
        "List": set(),
        "Literal": set(),
        "Optional": set(),
        "TypedDict": set(),
        "Union": set(),
    }


def test_init_name_to_schema_map():
    assert init_name_to_schema_map() == {
        "bool": {"type": "boolean"},
        "float": {"type": "number"},
        "int": {"type": "integer"},
        "str": {"type": "string"},
    }


@pytest.mark.parametrize(
    ["ast_element", "expected"],
    [
        [build_ast_annotation_element("a"), "a"],
        [build_ast_annotation_element("a.b"), "a.b"],
        [build_ast_annotation_element("a.b.c"), "a.b.c"],
        [build_ast_annotation_element("a.b.c.d"), "a.b.c.d"],
    ],
    ids=["single", "double", "triple", "quadruple"],
)
def test_get_ast_attribute_string(ast_element: AstNameOrAttribute, expected: str):
    assert get_ast_name_or_attribute_string(ast_element) == expected


@pytest.mark.parametrize(
    ["ast_element", "expected"],
    [
        [
            build_ast_annotation_element("List[str]"),
            "Invalid type annotation on line 1, character position [0:9]. Reason: test reason",
        ],
        [
            build_ast_annotation_element("List[\n    str\n]"),
            "Invalid type annotation on lines 1 to 3, character position [0:1]. Reason: test reason",
        ],
    ],
    ids=["single", "multiple"],
)
def test_invalid_type_annotation(ast_element: AstAnnotationElement, expected: str):
    assert str(InvalidTypeAnnotation(ast_element, "test reason")) == expected
