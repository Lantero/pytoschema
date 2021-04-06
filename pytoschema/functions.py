import ast
import fnmatch
import logging
import os
import pkgutil
import typing

from .annotations import TypingNamespace, NameToSchemaMap, Schema
from .common import init_typing_namespace, init_name_to_schema_map
from .jsonschema import get_schema_from_ast_element, InvalidTypeAnnotation
from .types import process_import, process_import_from, process_assign, process_class_def

JSON_SCHEMA_DRAFT = "http://json-schema.org/draft-07/schema#"
LOGGER = logging.getLogger()


def process_function_def(
    ast_function_def: ast.FunctionDef,
    typing_namespace: TypingNamespace,
    name_to_schema_map: NameToSchemaMap,
) -> Schema:
    LOGGER.info(f"Processing function {ast_function_def.name} ...")
    # Validation of not supported: Python 3.8 positional-only arguments and *args. Reason: We pass args as key-value
    if getattr(ast_function_def.args, "posonlyargs", None):
        raise InvalidTypeAnnotation(
            ast_function_def, f"Function '{ast_function_def.name}' contains positional only arguments"
        )
    if getattr(ast_function_def.args, "vararg", None):
        raise InvalidTypeAnnotation(
            ast_function_def,
            f"Function '{ast_function_def.name}' contains a variable number positional arguments i.e. *args",
        )
    schema = {
        "$schema": JSON_SCHEMA_DRAFT,
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }
    # Process **kwargs
    if ast_function_def.args.kwarg is not None:
        if ast_function_def.args.kwarg.annotation is None:
            raise InvalidTypeAnnotation(
                ast_function_def,
                f"Function '{ast_function_def.name}' is missing its "
                f"**{ast_function_def.args.kwarg.arg} type annotation",
            )
        schema["additionalProperties"] = get_schema_from_ast_element(
            ast_function_def.args.kwarg.annotation, typing_namespace, name_to_schema_map
        )
    # Positional argument defaults is a non-padded list because you cannot have defaults before non-defaulted args
    # Keyword-only arguments, on the other side, can have defaults at random positions, and the default list is padded
    positional_arg_defaults_padding = len(ast_function_def.args.args) - len(ast_function_def.args.defaults)
    padded_positional_arg_defaults = [None] * positional_arg_defaults_padding + ast_function_def.args.defaults
    for argument, default in zip(
        ast_function_def.args.args + ast_function_def.args.kwonlyargs,
        padded_positional_arg_defaults + ast_function_def.args.kw_defaults,
    ):
        if argument.annotation is None:
            raise InvalidTypeAnnotation(
                ast_function_def,
                f"Function '{ast_function_def.name}' is missing type annotation for the parameter '{argument.arg}'",
            )
        schema["properties"][argument.arg] = get_schema_from_ast_element(
            argument.annotation, typing_namespace, name_to_schema_map
        )
        if default is None:
            schema["required"].append(argument.arg)
    return schema


def filter_by_patterns(
    name: str,
    include_patterns: typing.Optional[typing.List[str]] = None,
    exclude_patterns: typing.Optional[typing.List[str]] = None,
):
    def _is_a_pattern(patterns: typing.List[str]):
        for pattern in patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False

    is_included = True
    is_excluded = False
    if include_patterns:
        is_included = _is_a_pattern(include_patterns)
    if exclude_patterns:
        is_excluded = _is_a_pattern(exclude_patterns)
    if is_excluded or not is_included:
        return False
    return True


def process_file(
    file_path: str,
    include_patterns: typing.Optional[typing.List[str]] = None,
    exclude_patterns: typing.Optional[typing.List[str]] = None,
) -> NameToSchemaMap:
    with open(file_path) as f:
        ast_body = ast.parse(f.read()).body
    name_to_schema_map = init_name_to_schema_map()
    typing_namespace = init_typing_namespace()
    function_schema_map = {}

    def _process_function(ast_function_def: ast.FunctionDef):
        if not filter_by_patterns(ast_function_def.name, include_patterns, exclude_patterns):
            LOGGER.info(f"Function {ast_function_def.name} skipped")
        else:
            function_schema_map[ast_function_def.name] = process_function_def(
                ast_function_def, typing_namespace, name_to_schema_map
            )

    for node in ast_body:
        node_type = type(node)
        process_map = {
            ast.Import: lambda: process_import(node, typing_namespace, name_to_schema_map),
            ast.ImportFrom: lambda: process_import_from(
                node, os.path.dirname(file_path), typing_namespace, name_to_schema_map
            ),
            ast.Assign: lambda: process_assign(node, typing_namespace, name_to_schema_map),
            ast.ClassDef: lambda: process_class_def(node, typing_namespace, name_to_schema_map),
            ast.FunctionDef: lambda: _process_function(node),
        }
        if node_type in process_map:
            process_map[node_type]()
    return function_schema_map


def package_iterator(
    package_path: str,
    include_patterns: typing.Optional[typing.List[str]] = None,
    exclude_patterns: typing.Optional[typing.List[str]] = None,
    import_prefix: typing.Optional[str] = None,
) -> typing.Generator[typing.Tuple[str, str], None, None]:
    package_path = os.path.normpath(package_path)
    package_name = os.path.basename(package_path)
    if import_prefix is None:
        import_path = package_name
    else:
        import_path = f"{import_prefix}.{package_name}"
    yield import_path, os.path.join(package_path, "__init__.py")
    for child_module in pkgutil.iter_modules([package_path]):
        if not filter_by_patterns(child_module.name, include_patterns, exclude_patterns):
            LOGGER.info(f"Module {package_name}.{child_module.name} skipped")
            continue
        if not child_module.ispkg:
            if import_prefix is None:
                import_path = f"{package_name}.{child_module.name}"
            else:
                import_path = f"{import_prefix}.{package_name}.{child_module.name}"
            yield import_path, os.path.join(package_path, f"{child_module.name}.py")
        else:
            if import_prefix is None:
                new_prefix = package_name
            else:
                new_prefix = f"{import_prefix}.{package_name}"
            for inner_import_path, inner_module_math in package_iterator(
                os.path.join(package_path, child_module.name), include_patterns, exclude_patterns, new_prefix
            ):
                yield inner_import_path, inner_module_math


def process_package(
    package_path: str,
    include_patterns: typing.Optional[typing.List[str]] = None,
    exclude_patterns: typing.Optional[typing.List[str]] = None,
) -> NameToSchemaMap:
    function_schema_map = {}
    for package_chain, package_file_path in package_iterator(package_path, include_patterns, exclude_patterns):
        function_schema_map.update(
            **{
                f"{package_chain}.{func_name}": func_schema
                for func_name, func_schema in process_file(
                    package_file_path, include_patterns, exclude_patterns
                ).items()
            }
        )
    return function_schema_map
