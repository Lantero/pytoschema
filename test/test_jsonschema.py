import functools

import pytest

from pytoschema.common import init_name_to_schema_map, InvalidTypeAnnotation
from pytoschema.jsonschema import get_schema_from_ast_element

from .conftest import assert_expected_value_or_exception, build_ast_annotation_element, TEST_TYPING_NAMESPACE


@pytest.mark.parametrize(
    ["ast_element", "expected"],
    [
        [build_ast_annotation_element("None"), {"type": "null"}],
        [
            build_ast_annotation_element("3"),
            InvalidTypeAnnotation(
                build_ast_annotation_element("3"), "Only valid constant type annotation is the None value"
            ),
        ],
        [build_ast_annotation_element("bool"), {"type": "boolean"}],
        [build_ast_annotation_element("str"), {"type": "string"}],
        [build_ast_annotation_element("int"), {"type": "integer"}],
        [build_ast_annotation_element("float"), {"type": "number"}],
        [
            build_ast_annotation_element("complex"),
            InvalidTypeAnnotation(
                build_ast_annotation_element("complex"),
                "Only valid named type annotations are bool, float, int, str. Are you missing an import?",
            ),
        ],
        [
            build_ast_annotation_element("Foo[2]"),
            InvalidTypeAnnotation(
                build_ast_annotation_element("Foo[2]"),
                "Only valid subscript type annotations are Dict, List, Literal, Optional, Union. "
                "Are you missing an import?",
            ),
        ],
        [build_ast_annotation_element("typing.List[str]"), {"items": {"type": "string"}, "type": "array"}],
        [build_ast_annotation_element("typing.Literal['red']"), {"enum": ["red"]}],
        [
            build_ast_annotation_element("typing.Literal[str]"),
            InvalidTypeAnnotation(
                build_ast_annotation_element("typing.Literal[str]").slice.value,
                "Literal values must be constants",
            ),
        ],
        [
            build_ast_annotation_element("typing.Literal[2j]"),
            InvalidTypeAnnotation(
                build_ast_annotation_element("typing.Literal[2j]").slice.value,
                "Literal values must be either None, bool, str, int or float",
            ),
        ],
        [build_ast_annotation_element("typing.Optional[str]"), {"anyOf": [{"type": "string"}, {"type": "null"}]}],
        [build_ast_annotation_element("typing.Union[str]"), {"anyOf": [{"type": "string"}]}],
        [
            build_ast_annotation_element("typing.Dict[str]"),
            InvalidTypeAnnotation(
                build_ast_annotation_element("typing.Dict[str]"),
                "Dict must contain more than one element",
            ),
        ],
        [
            build_ast_annotation_element("typing.Dict[str, int]"),
            {"additionalProperties": {"type": "integer"}, "type": "object"},
        ],
        [
            build_ast_annotation_element("typing.Dict[int, int]"),
            InvalidTypeAnnotation(
                build_ast_annotation_element("typing.Dict[int, int]"),
                "Dict keys must be strings",
            ),
        ],
        [build_ast_annotation_element("typing.Literal['red', 5.0]"), {"enum": ["red", 5.0]}],
        [build_ast_annotation_element("typing.Union[str, int]"), {"anyOf": [{"type": "string"}, {"type": "integer"}]}],
        [
            build_ast_annotation_element("typing.List[str, int]"),
            InvalidTypeAnnotation(
                build_ast_annotation_element("typing.List[str, int]"),
                "List must not contain more than one element",
            ),
        ],
        [
            build_ast_annotation_element("typing.List[eval(3)]"),
            InvalidTypeAnnotation(
                build_ast_annotation_element("typing.List[eval(3)]"),
                "Invalid subscript child ast element '<class '_ast.Subscript'>'",
            ),
        ],
        [
            build_ast_annotation_element("eval(4)"),
            InvalidTypeAnnotation(
                build_ast_annotation_element("eval(4)"),
                "Invalid type annotation ast element '<class '_ast.Call'>'",
            ),
        ],
    ],
    ids=[
        "constant_none",
        "constant_invalid",
        "name_bool",
        "name_string",
        "name_int",
        "name_float",
        "name_invalid",
        "subscript_invalid",
        "subscript_single_list",
        "subscript_single_literal",
        "subscript_single_literal_invalid_no_constant",
        "subscript_single_literal_invalid_bad_constant_type",
        "subscript_single_optional",
        "subscript_single_union",
        "subscript_single_invalid",
        "subscript_multiple_dict",
        "subscript_multiple_dict_bad_keys",
        "subscript_multiple_literal",
        "subscript_multiple_union",
        "subscript_multiple_invalid",
        "subscript_invalid_children",
        "invalid_annotation",
    ],
)
def test_get_json_schema_from_ast_element(ast_element, expected):
    assert_expected_value_or_exception(
        functools.partial(get_schema_from_ast_element, ast_element, TEST_TYPING_NAMESPACE, init_name_to_schema_map()),
        expected,
    )
