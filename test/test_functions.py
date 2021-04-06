import ast
import functools
import os
import tempfile
from typing import List, Optional

import pytest

from pytoschema.annotations import Schema
from pytoschema.common import init_name_to_schema_map, InvalidTypeAnnotation
from pytoschema.functions import filter_by_patterns, process_function_def, process_file, process_package

from .conftest import assert_expected_value_or_exception, TEST_TYPING_NAMESPACE


@pytest.mark.parametrize(
    ["ast_function_def", "expected"],
    [
        [
            ast.parse("def foo(a, /): pass").body[0],
            InvalidTypeAnnotation(
                ast.parse("def foo(a, /): pass").body[0], "Function 'foo' contains positional only arguments"
            ),
        ],
        [
            ast.parse("def foo(a, *args): pass").body[0],
            InvalidTypeAnnotation(
                ast.parse("def foo(a, *args): pass").body[0],
                "Function 'foo' contains a variable number positional arguments i.e. *args",
            ),
        ],
        [
            ast.parse("def foo(**bar): pass").body[0],
            InvalidTypeAnnotation(
                ast.parse("def foo(**bar): pass").body[0], "Function 'foo' is missing its **bar type annotation"
            ),
        ],
        [
            ast.parse("def foo(**bar: int): pass").body[0],
            {
                "input": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": {"type": "integer"},
                },
                "output": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "null",
                },
            },
        ],
        [
            ast.parse("def foo(a): pass").body[0],
            InvalidTypeAnnotation(
                ast.parse("def foo(a): pass").body[0], "Function 'foo' is missing type annotation for the parameter 'a'"
            ),
        ],
        [
            ast.parse("def foo(a: int = 3): pass").body[0],
            {
                "input": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "properties": {"a": {"type": "integer"}},
                    "required": [],
                    "additionalProperties": False,
                },
                "output": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "null",
                },
            },
        ],
        [
            ast.parse("def foo(a: int): pass").body[0],
            {
                "input": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "properties": {"a": {"type": "integer"}},
                    "required": ["a"],
                    "additionalProperties": False,
                },
                "output": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "null",
                },
            },
        ],
        [
            ast.parse("def foo() -> int: pass").body[0],
            {
                "input": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                "output": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "integer",
                },
            },
        ],
    ],
    ids=[
        "posonly_args",
        "args",
        "missing_kwargs_annotation",
        "valid_kwargs",
        "missing_arg",
        "arg_default",
        "arg_no_default",
        "return",
    ],
)
def test_process_function_def(ast_function_def: ast.FunctionDef, expected: Schema):
    assert_expected_value_or_exception(
        functools.partial(process_function_def, ast_function_def, TEST_TYPING_NAMESPACE, init_name_to_schema_map()),
        expected,
    )


@pytest.mark.parametrize(
    "name, include_patterns, exclude_patterns, expected",
    [
        ["foo", None, None, True],
        ["foo", ["bar*"], None, False],
        ["foo", ["foo*"], None, True],
        ["foo", None, ["bar*"], True],
        ["foo", None, ["foo*"], False],
        ["foo", ["foo*"], ["bar*"], True],
        ["foo", ["foo*"], ["foo*"], False],
    ],
    ids=[
        "no_patterns",
        "include_miss",
        "include_finds",
        "exclude_miss",
        "exclude_finds",
        "exclude_override_miss",
        "exclude_override_finds",
    ],
)
def test_filter_by_patterns(
    name: str, include_patterns: Optional[List[str]], exclude_patterns: Optional[List[str]], expected: bool
):
    assert filter_by_patterns(name, include_patterns, exclude_patterns) == expected


def test_process_file():
    with tempfile.NamedTemporaryFile("w") as f:
        f.write("import typing\n\n\ndef foo(a: int): pass\n\n\ndef bar(b: int): pass\n\n\neval(3)")
        f.flush()
        assert process_file(f.name, None, ["bar*"]) == {
            "foo": {
                "input": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "properties": {"a": {"type": "integer"}},
                    "required": ["a"],
                    "additionalProperties": False,
                },
                "output": {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "null",
                },
            }
        }


def test_process_package():
    init_schema = {
        "example.version": {
            "input": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "additionalProperties": False,
                "properties": {},
                "required": [],
                "type": "object",
            },
            "output": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "string",
            },
        },
        "example.config.dev.common.get_config": {
            "input": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "additionalProperties": False,
                "properties": {},
                "required": [],
                "type": "object",
            },
            "output": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "additionalProperties": {
                    "type": "string",
                },
                "type": "object",
            },
        },
        "example.config.prod.common.get_config": {
            "input": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "additionalProperties": False,
                "properties": {},
                "required": [],
                "type": "object",
            },
            "output": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "additionalProperties": {
                    "type": "string",
                },
                "type": "object",
            },
        },
    }
    expected = {
        "example.service.start": {
            "input": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "additionalProperties": False,
                "properties": {
                    "service": {
                        "additionalProperties": False,
                        "properties": {
                            "address": {"type": "string"},
                            "config": {
                                "additionalProperties": {
                                    "anyOf": [
                                        {"type": "object"},
                                        {"type": "array"},
                                        {"type": "null"},
                                        {"type": "string"},
                                        {"type": "boolean"},
                                        {"type": "integer"},
                                        {"type": "number"},
                                    ]
                                },
                                "type": "object",
                            },
                            "state": {"enum": ["RUNNING", "STOPPED", "UNKNOWN"]},
                            "debug": {"type": "boolean"},
                            "port": {"anyOf": [{"type": "integer"}, {"type": "number"}]},
                            "tags": {"items": {"type": "string"}, "type": "array"},
                        },
                        "required": [],
                        "type": "object",
                    }
                },
                "required": ["service"],
                "type": "object",
            },
            "output": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "null",
            },
        },
        "example.service._secret": {
            "input": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "additionalProperties": False,
                "properties": {"secret": {"anyOf": [{"type": "string"}, {"type": "null"}]}},
                "required": [],
                "type": "object",
            },
            "output": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "null",
            },
        },
    }
    expected.update(init_schema)
    assert process_package(os.path.join("test", "example")) == expected
    assert process_package(os.path.join("test", "example"), exclude_patterns=["service*"]) == init_schema
    current_dir = os.getcwd()
    os.chdir("test")
    try:
        assert process_package("example") == expected
    finally:
        os.chdir(current_dir)
