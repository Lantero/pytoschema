import ast
from typing import Any, Dict, Set, Union


AstNameOrAttribute = Union[ast.Name, ast.Attribute]
AstAnnotationElement = Union[AstNameOrAttribute, ast.Constant, ast.Subscript]
AstElement = Union[AstAnnotationElement, ast.FunctionDef]

LiteralValue = Union[None, bool, str, int, float]

Schema = Dict[str, Any]
NameToSchemaMap = Dict[str, Schema]

TypingNamespace = Dict[str, Set[str]]
