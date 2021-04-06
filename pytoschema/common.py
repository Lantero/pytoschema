import ast

from .annotations import AstElement, NameToSchemaMap, TypingNamespace


BASE_NAME_TO_SCHEMA_MAP = {
    "bool": {"type": "boolean"},
    "float": {"type": "number"},
    "int": {"type": "integer"},
    "str": {"type": "string"},
}

VALID_SUBSCRIPT_TYPES = frozenset({"Union", "List", "Dict", "Optional", "Literal"})
VALID_TYPES = VALID_SUBSCRIPT_TYPES | frozenset({"TypedDict", "Any"})


class InvalidTypeAnnotation(Exception):
    def __init__(self, ast_element: AstElement, error: str):
        self.ast_object = ast_element
        if ast_element.lineno == ast_element.end_lineno:
            line_str = f"line {ast_element.lineno}"
        else:
            line_str = f"lines {ast_element.lineno} to {ast_element.end_lineno}"
        column_str = f"character position [{ast_element.col_offset}:{ast_element.end_col_offset}]"
        super().__init__(f"Invalid type annotation on {line_str}, {column_str}. Reason: {error}")


def init_typing_namespace() -> TypingNamespace:
    return {valid_type: set() for valid_type in VALID_TYPES}


def init_name_to_schema_map() -> NameToSchemaMap:
    return {key: value for key, value in BASE_NAME_TO_SCHEMA_MAP.items()}


def get_ast_name_or_attribute_string(ast_element: AstElement) -> str:
    if isinstance(ast_element, ast.Name):
        return ast_element.id
    elif isinstance(ast_element.value, ast.Name):
        return f"{ast_element.value.id}.{ast_element.attr}"
    else:
        return f"{get_ast_name_or_attribute_string(ast_element.value)}.{ast_element.attr}"
