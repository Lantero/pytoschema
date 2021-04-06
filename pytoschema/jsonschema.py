import ast

from .annotations import AstAnnotationElement, LiteralValue, Schema, NameToSchemaMap, TypingNamespace
from .common import get_ast_name_or_attribute_string, InvalidTypeAnnotation, VALID_SUBSCRIPT_TYPES


def _validate_literal_value(ast_element: AstAnnotationElement) -> LiteralValue:
    if not isinstance(ast_element, ast.Constant):
        raise InvalidTypeAnnotation(ast_element, "Literal values must be constants")
    elif not isinstance(ast_element.value, (type(None), bool, str, int, float)):
        raise InvalidTypeAnnotation(ast_element, "Literal values must be either None, bool, str, int or float")
    return ast_element.value


def get_schema_from_ast_element(
    ast_element: AstAnnotationElement,
    type_namespace: TypingNamespace,
    schema_map: NameToSchemaMap,
) -> Schema:
    if isinstance(ast_element, ast.Constant):
        if ast_element.value is None:
            return {"type": "null"}
        else:
            raise InvalidTypeAnnotation(ast_element, "Only valid constant type annotation is the None value")
    elif isinstance(ast_element, (ast.Name, ast.Attribute)):
        element_string = get_ast_name_or_attribute_string(ast_element)
        if element_string not in schema_map:
            raise InvalidTypeAnnotation(
                ast_element,
                f"Only valid named type annotations are {', '.join(sorted(schema_map.keys()))}. "
                f"Are you missing an import?",
            )
        return schema_map[element_string]
    elif isinstance(ast_element, ast.Subscript):
        # 1. Validate subscript type: Dict, List, Literal, Optional and Union
        subscript_string = get_ast_name_or_attribute_string(ast_element.value)
        for key in VALID_SUBSCRIPT_TYPES:
            if subscript_string in type_namespace.get(key, {}):
                subscript_type = key
                break
        else:
            raise InvalidTypeAnnotation(
                ast_element,
                f"Only valid subscript type annotations are {', '.join(sorted(list(VALID_SUBSCRIPT_TYPES)))}. "
                f"Are you missing an import?",
            )
        # 2.1. If subscript only has one child
        if isinstance(ast_element.slice.value, (ast.Constant, ast.Name, ast.Attribute, ast.Subscript)):
            if subscript_type == "List":
                return {
                    "type": "array",
                    "items": get_schema_from_ast_element(ast_element.slice.value, type_namespace, schema_map),
                }
            elif subscript_type == "Literal":
                return {"enum": [_validate_literal_value(ast_element.slice.value)]}
            elif subscript_type == "Optional":
                return {
                    "anyOf": [
                        get_schema_from_ast_element(ast_element.slice.value, type_namespace, schema_map),
                        {"type": "null"},
                    ]
                }
            elif subscript_type == "Union":
                return {"anyOf": [get_schema_from_ast_element(ast_element.slice.value, type_namespace, schema_map)]}
            else:
                raise InvalidTypeAnnotation(ast_element, f"{subscript_type} must contain more than one element")
        # 2.1. If subscript has multiple children
        elif isinstance(ast_element.slice.value, ast.Tuple):
            if subscript_type == "Dict":
                if not (
                    isinstance(ast_element.slice.value.elts[0], ast.Name)
                    and ast_element.slice.value.elts[0].id == "str"
                ):
                    raise InvalidTypeAnnotation(ast_element, "Dict keys must be strings")
                return {
                    "type": "object",
                    "additionalProperties": get_schema_from_ast_element(
                        ast_element.slice.value.elts[1], type_namespace, schema_map
                    ),
                }
            elif subscript_type == "Literal":
                return {"enum": [_validate_literal_value(element) for element in ast_element.slice.value.elts]}
            elif subscript_type == "Union":
                return {
                    "anyOf": [
                        get_schema_from_ast_element(element, type_namespace, schema_map)
                        for element in ast_element.slice.value.elts
                    ]
                }
            else:
                raise InvalidTypeAnnotation(ast_element, f"{subscript_type} must not contain more than one element")
        else:
            raise InvalidTypeAnnotation(ast_element, f"Invalid subscript child ast element '{str(type(ast_element))}'")
    else:
        raise InvalidTypeAnnotation(ast_element, f"Invalid type annotation ast element '{str(type(ast_element))}'")
