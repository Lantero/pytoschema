import ast
import os

from .annotations import NameToSchemaMap, TypingNamespace
from .common import (
    get_ast_name_or_attribute_string,
    init_name_to_schema_map,
    init_typing_namespace,
    VALID_SUBSCRIPT_TYPES,
    VALID_TYPES,
)
from .jsonschema import get_schema_from_ast_element


ANY_SCHEMA = {
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


def process_alias(ast_alias: ast.alias) -> str:
    if ast_alias.asname is None:
        return ast_alias.name
    else:
        return ast_alias.asname


def process_import(ast_import: ast.Import, typing_namespace: TypingNamespace, name_to_schema_map: NameToSchemaMap):
    for import_name in ast_import.names:
        module_element = process_alias(import_name)
        if import_name.name == "typing":
            for valid_type in VALID_TYPES:
                element = f"{module_element}.{valid_type}"
                typing_namespace[valid_type].add(element)
                if valid_type == "Any":
                    name_to_schema_map[element] = ANY_SCHEMA


def process_import_from(
    ast_import_from: ast.ImportFrom,
    base_path: str,
    typing_namespace: TypingNamespace,
    name_to_schema_map: NameToSchemaMap,
):
    # Level == 0 are absolute imports. We only follow the ones that targets typing
    if ast_import_from.level == 0:
        for import_name in ast_import_from.names:
            element = process_alias(import_name)
            if ast_import_from.module == "typing":
                if import_name.name in VALID_TYPES:
                    typing_namespace[import_name.name].add(element)
                    if import_name.name == "Any":
                        name_to_schema_map[element] = ANY_SCHEMA
    # Level >= 1 are relative imports. 1 is the current directory, 2 the parent, 3 the grandparent, and so on.
    else:
        module = f"{ast_import_from.module}.py" if ast_import_from.module else "__init__.py"
        new_base_path = base_path
        for _ in range(ast_import_from.level - 1):
            new_base_path = os.path.join(new_base_path, os.pardir)
        path = os.path.join(new_base_path, module)
        with open(path) as f:
            ast_module = ast.parse(f.read())
        new_typing_namespace = init_typing_namespace()
        new_name_to_schema_map = init_name_to_schema_map()
        for node in ast_module.body:
            if isinstance(node, ast.Import):
                process_import(node, new_typing_namespace, new_name_to_schema_map)
            elif isinstance(node, ast.ImportFrom):
                process_import_from(node, new_base_path, new_typing_namespace, new_name_to_schema_map)
            elif isinstance(node, ast.Assign) and node.targets[0].id:
                process_assign(node, new_typing_namespace, new_name_to_schema_map)
            elif isinstance(node, ast.ClassDef) and node.name:
                process_class_def(node, new_typing_namespace, new_name_to_schema_map)
        for import_name in ast_import_from.names:
            item = new_name_to_schema_map.get(import_name.name)
            # Import could be something we didn't care about and hence didn't put in name_to_schema_map
            if item is not None:
                name_to_schema_map[import_name.name] = item


def process_class_def(
    ast_class_def: ast.ClassDef, typing_namespace: TypingNamespace, name_to_schema_map: NameToSchemaMap
):
    # This supports TypedDict class syntax
    if ast_class_def.bases:
        if get_ast_name_or_attribute_string(ast_class_def.bases[0]) in typing_namespace.get("TypedDict", set()):
            properties = {}
            required = []
            all_properties_required = True
            for keyword in ast_class_def.keywords:
                if (
                    keyword.arg == "total"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, bool)
                ):
                    all_properties_required = bool(keyword.value.value)
            for index, node in enumerate(ast_class_def.body):
                if isinstance(node, ast.AnnAssign):
                    properties[node.target.id] = get_schema_from_ast_element(
                        node.annotation, typing_namespace, name_to_schema_map
                    )
                    if all_properties_required:
                        required.append(node.target.id)
            name_to_schema_map[ast_class_def.name] = {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            }


def process_assign(ast_assign: ast.Assign, typing_namespace: TypingNamespace, name_to_schema_map: NameToSchemaMap):
    if (
        isinstance(ast_assign.targets[0], ast.Name)
        and isinstance(ast_assign.value, ast.Subscript)
        and get_ast_name_or_attribute_string(ast_assign.value.value)
        in (
            item
            for values in (typing_namespace[subscript_type] for subscript_type in VALID_SUBSCRIPT_TYPES)
            for item in values
        )
    ):
        name_to_schema_map[ast_assign.targets[0].id] = get_schema_from_ast_element(
            ast_assign.value, typing_namespace, name_to_schema_map
        )
