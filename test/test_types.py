import ast
import os
import tempfile
from typing import Tuple

import pytest

from pytoschema.annotations import NameToSchemaMap, TypingNamespace
from pytoschema.common import init_typing_namespace, init_name_to_schema_map
from pytoschema.types import (
    ANY_SCHEMA,
    process_alias,
    process_import,
    process_import_from,
    process_assign,
    process_class_def,
)


@pytest.mark.parametrize(
    ["alias_object", "expected"],
    [
        [ast.parse("import typing as foo").body[0].names[0], "foo"],
        [ast.parse("import typing").body[0].names[0], "typing"],
    ],
    ids=["alias", "no_alias"],
)
def test_process_alias(alias_object, expected):
    assert process_alias(alias_object) == expected


@pytest.mark.parametrize(
    ["ast_import", "expected"],
    [
        [
            ast.parse("import typing as foo").body[0],
            (
                {
                    "Union": {"foo.Union"},
                    "List": {"foo.List"},
                    "Dict": {"foo.Dict"},
                    "Optional": {"foo.Optional"},
                    "Any": {"foo.Any"},
                    "TypedDict": {"foo.TypedDict"},
                    "Literal": {"foo.Literal"},
                },
                dict(
                    init_name_to_schema_map(),
                    **{
                        "foo.Any": {
                            "anyOf": [
                                {"type": "object"},
                                {"type": "array"},
                                {"type": "null"},
                                {"type": "string"},
                                {"type": "boolean"},
                                {"type": "integer"},
                                {"type": "number"},
                            ]
                        }
                    },
                ),
            ),
        ],
        [
            ast.parse("import os").body[0],
            (
                {
                    "Union": set(),
                    "List": set(),
                    "Dict": set(),
                    "Optional": set(),
                    "Any": set(),
                    "TypedDict": set(),
                    "Literal": set(),
                },
                init_name_to_schema_map(),
            ),
        ],
    ],
    ids=["typing", "no_typing_nor_enum"],
)
def test_process_import(ast_import: ast.Import, expected: Tuple[TypingNamespace, NameToSchemaMap]):
    typing_namespace, name_to_schema_map = init_typing_namespace(), init_name_to_schema_map()
    process_import(ast_import, typing_namespace, name_to_schema_map)
    assert expected[0] == typing_namespace
    assert expected[1] == name_to_schema_map


@pytest.mark.parametrize(
    ["ast_assign", "typing_namespace", "name_to_schema_map", "expected"],
    [
        [
            ast.parse("a = typing.Optional[str]").body[0],
            dict(init_typing_namespace(), **{"Optional": {"typing.Optional"}}),
            init_name_to_schema_map(),
            dict(init_name_to_schema_map(), **{"a": {"anyOf": [{"type": "string"}, {"type": "null"}]}}),
        ],
        [ast.parse("a = b[34]").body[0], init_typing_namespace(), init_name_to_schema_map(), init_name_to_schema_map()],
    ],
    ids=["processed", "not_processed"],
)
def test_process_assign(
    ast_assign: ast.Assign,
    typing_namespace: TypingNamespace,
    name_to_schema_map: NameToSchemaMap,
    expected: NameToSchemaMap,
):
    process_assign(ast_assign, typing_namespace, name_to_schema_map)
    assert expected == name_to_schema_map


@pytest.mark.parametrize(
    ["ast_class_def", "typing_namespace", "name_to_schema_map", "expected"],
    [
        [
            ast.parse("class Foo: pass").body[0],
            init_typing_namespace(),
            init_name_to_schema_map(),
            init_name_to_schema_map(),
        ],
        [
            ast.parse("class Foo(bar): pass").body[0],
            init_typing_namespace(),
            init_name_to_schema_map(),
            init_name_to_schema_map(),
        ],
        [
            ast.parse(
                """class Car(typing.TypedDict):
    '''Some docstring'''
    model: str
    plate: str"""
            ).body[0],
            dict(init_typing_namespace(), **{"TypedDict": {"typing.TypedDict"}}),
            init_name_to_schema_map(),
            dict(
                init_name_to_schema_map(),
                **{
                    "Car": {
                        "additionalProperties": False,
                        "properties": {"model": {"type": "string"}, "plate": {"type": "string"}},
                        "required": ["model", "plate"],
                        "type": "object",
                    }
                },
            ),
        ],
        [
            ast.parse(
                """class Car(typing.TypedDict, total=False, not_relevant="fake"):
    '''Some docstring'''
    model: str
    plate: str"""
            ).body[0],
            dict(init_typing_namespace(), **{"TypedDict": {"typing.TypedDict"}}),
            init_name_to_schema_map(),
            dict(
                init_name_to_schema_map(),
                **{
                    "Car": {
                        "additionalProperties": False,
                        "properties": {"model": {"type": "string"}, "plate": {"type": "string"}},
                        "required": [],
                        "type": "object",
                    }
                },
            ),
        ],
    ],
    ids=["not_typed_dict", "not_typed_dictwith_base_class", "typed_dict", "typed_dict_not_required"],
)
def test_process_class_def(
    ast_class_def: ast.ClassDef,
    typing_namespace: TypingNamespace,
    name_to_schema_map: NameToSchemaMap,
    expected: NameToSchemaMap,
):
    process_class_def(ast_class_def, typing_namespace, name_to_schema_map)
    assert expected == name_to_schema_map


@pytest.mark.parametrize(
    ["ast_import_from", "base_path", "expected"],
    [
        [
            ast.parse("from typing import Any").body[0],
            ".",
            (dict(init_typing_namespace(), **{"Any": {"Any"}}), dict(init_name_to_schema_map(), **{"Any": ANY_SCHEMA})),
        ],
        [
            ast.parse("from typing import Union").body[0],
            ".",
            (dict(init_typing_namespace(), **{"Union": {"Union"}}), init_name_to_schema_map()),
        ],
        [ast.parse("from enum import foo").body[0], ".", (init_typing_namespace(), init_name_to_schema_map())],
        [ast.parse("from typing import foo").body[0], ".", (init_typing_namespace(), init_name_to_schema_map())],
        [ast.parse("from os import path").body[0], ".", (init_typing_namespace(), init_name_to_schema_map())],
    ],
    ids=["typing_any", "typing_union", "else_typing", "else_enum", "else_no_typing_nor_enum"],
)
def test_process_import_from_external(
    ast_import_from: ast.ImportFrom, base_path: str, expected: Tuple[TypingNamespace, NameToSchemaMap]
):
    typing_namespace, name_to_schema_map = init_typing_namespace(), init_name_to_schema_map()
    process_import_from(ast_import_from, base_path, typing_namespace, name_to_schema_map)
    assert expected[0] == typing_namespace
    assert expected[1] == name_to_schema_map


def test_process_import_from_local():
    with tempfile.TemporaryDirectory() as package:
        # Package creation
        subpackage = os.path.join(package, "subpackage")
        os.mkdir(subpackage)
        package_init = os.path.join(package, "__init__.py")
        package_foo = os.path.join(package, "foo.py")
        subpackage_init = os.path.join(subpackage, "__init__.py")
        subpackage_bar = os.path.join(subpackage, "bar.py")
        subpackage_baz = os.path.join(subpackage, "baz.py")
        with open(package_init, "w") as f:
            f.write("import typing\n\nfrom .foo import B\n\n\nclass A(typing.TypedDict):\n    param: B\n")
        with open(package_foo, "w") as f:
            f.write("import typing\n\n\nclass B(typing.TypedDict):\n    param: int\n")
        with open(subpackage_init, "w") as f:
            f.write("import typing\n\n\nC = typing.Union[bool, float]\n\n\neval(3)")
        with open(subpackage_bar, "w") as f:
            f.write(
                "from .. import A\nfrom ..foo import B\nfrom . import C\nfrom .baz import D\nfrom .baz import bad\n"
            )
        with open(subpackage_baz, "w") as f:
            f.write("import typing\n\n\nD = typing.Dict[str, int]\n")
        # Tests
        typing_namespace = init_typing_namespace()
        b_schema = {
            "type": "object",
            "properties": {"param": {"type": "integer"}},
            "required": ["param"],
            "additionalProperties": False,
        }
        a_schema = {
            "type": "object",
            "properties": {"param": b_schema},
            "required": ["param"],
            "additionalProperties": False,
        }
        with open(package_init) as f:
            name_to_schema_map = init_name_to_schema_map()
            process_import_from(ast.parse(f.read()).body[1], package, typing_namespace, name_to_schema_map)
            assert name_to_schema_map == {
                "bool": {"type": "boolean"},
                "int": {"type": "integer"},
                "float": {"type": "number"},
                "str": {"type": "string"},
                "B": b_schema,
            }
        with open(subpackage_bar) as f:
            file_content = f.read()
            name_to_schema_map = init_name_to_schema_map()
            process_import_from(ast.parse(file_content).body[0], subpackage, typing_namespace, name_to_schema_map)
            assert name_to_schema_map == {
                "bool": {"type": "boolean"},
                "int": {"type": "integer"},
                "float": {"type": "number"},
                "str": {"type": "string"},
                "A": a_schema,
            }
            name_to_schema_map = init_name_to_schema_map()
            process_import_from(ast.parse(file_content).body[1], subpackage, typing_namespace, name_to_schema_map)
            assert name_to_schema_map == {
                "bool": {"type": "boolean"},
                "int": {"type": "integer"},
                "float": {"type": "number"},
                "str": {"type": "string"},
                "B": b_schema,
            }
            name_to_schema_map = init_name_to_schema_map()
            process_import_from(ast.parse(file_content).body[2], subpackage, typing_namespace, name_to_schema_map)
            assert name_to_schema_map == {
                "bool": {"type": "boolean"},
                "int": {"type": "integer"},
                "float": {"type": "number"},
                "str": {"type": "string"},
                "C": {"anyOf": [{"type": "boolean"}, {"type": "number"}]},
            }
            name_to_schema_map = init_name_to_schema_map()
            process_import_from(ast.parse(file_content).body[3], subpackage, typing_namespace, name_to_schema_map)
            assert name_to_schema_map == {
                "bool": {"type": "boolean"},
                "int": {"type": "integer"},
                "float": {"type": "number"},
                "str": {"type": "string"},
                "D": {"additionalProperties": {"type": "integer"}, "type": "object"},
            }
            name_to_schema_map = init_name_to_schema_map()
            process_import_from(ast.parse(file_content).body[4], subpackage, typing_namespace, name_to_schema_map)
            assert name_to_schema_map == {
                "bool": {"type": "boolean"},
                "int": {"type": "integer"},
                "float": {"type": "number"},
                "str": {"type": "string"},
            }
