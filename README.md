![Test](https://github.com/comprehensivetech/pytoschema/workflows/Test/badge.svg?branch=master)

# pytoschema

1. [Overview](#overview)

2. [Getting started](#getting-started)
   
   1. [Installation](#installation)

      1. [Supported versions](#supported-versions)      

   2. [Scan a package](#scan-a-package)
   3. [Scan a file](#scan-a-file)
   4. [Include and exclude patterns](#include-and-exclude-patterns)
   
3. [Type annotation rules](#type-annotation-rules)

   1. [Rules](#rules)
   2. [Allowed annotations](#allowed-annotations)
      
      1. [Atomic types](#atomic-types)
      2. [Composite types](#composite-types)
   
   3. [Default function arguments](#default-function-arguments)
   
4. [References](#references)

## Overview

This is a Python package that uses static analysis - `ast` - to convert Python type annotations into JSON schemas.

This allows you to auto-generate the validation schemas from backend functions written in Python, so they can be used by
other layers of your application, normally the frontend. As an example, let's look at this file:

```python
from typing import List, Literal, TypedDict


class UserProperties(TypedDict, total=False):
   username: str
   is_superadmin: bool
   groups: List[str]
   status: Literal["ACTIVE", "DISABLED"]
   

def update_user(user_id: str, user_properties: UserProperties) -> bool:
    pass  # Your function code
```

We could now use the library to process this file, and it would create the following JSON schemas:

```json
{
    "update_user": {
        "input": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string"
                },
                "user_properties": {
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string"
                        },
                        "is_superadmin": {
                            "type": "boolean"
                        },
                        "groups": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },
                        "status": {
                            "enum": [
                                "ACTIVE",
                                "DISABLED"
                            ]
                        }
                    },
                    "required": [],
                    "additionalProperties": false
                }
            },
            "required": [
                "user_id",
                "user_properties"
            ],
            "additionalProperties": false
        },
        "output": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "boolean"
        }
    }
}
```

This allows you to document and validate your functions in a single place, next to your code, using native Python.

## Getting started

### Installation

- `pip install pytoschema`.

#### Supported versions

- Python 3.8+ 
- JSON schema draft 7+

### Scan a package

After installing the package, you can open a python terminal from the root of the repo and run:

```python
import os
import json

from pytoschema.functions import process_package

print(json.dumps(process_package(os.path.join("test", "example")), indent=4))
```

The example package will be scanned and JSON schemas will be generated for all the top level functions it can find.

### Scan a file

You can also target specific files, which won't include the package namespacing in the result value. Following on the
same terminal:

```python
from pytoschema.functions import process_file

print(json.dumps(process_file(os.path.join("test", "example", "service.py")), indent=4))
```

### Include and exclude patterns

Include and exclude unix-like patterns can be used to filter function and module names we want to allow/disallow for
scanning. See the difference when you now run this instead:

```python
print(json.dumps(process_package(os.path.join("test", "example"), exclude_patterns=["_*"]), indent=4))
```

Similarly, but applied to specific files:

```python
print(json.dumps(process_file(os.path.join("test", "example", "service.py"), include_patterns=["_*"]), indent=4))
```

Things to take into account:
- Exclude pattern matching overwrite include matches. 
- `__init__.py` files are not affected by pattern rules and are always scanned. However, you can still filter its
  internal functions.

## Type annotation rules

Fitting Python's typing model to JSON means not everything is allowed in your function signatures. This is a natural
restriction that comes with JSON data serialization. Hopefully, most of the useful stuff you need is allowed, provided
you follow these simple rules.

### Rules

1. The functions you want to scan need to be type annotated, using the annotations described in the next section.

2. Function arguments are meant to be passed in key-value format, like a json object. This puts a couple of restrictions
   regarding *args, **kwargs, positional-only and keyword-only arguments:
   
   The following is allowed:
   - ****kwargs**: `def func(**kwargs): pass`
   - **keyword-only arguments**: `def func(*, a): pass`
   
   The following is not allowed:
   - ***args**: `def func(*args): pass`
   - **positional-only arguments**: `def func(a, /): pass`

### Allowed annotations

#### Atomic types

See Python type annotations and its JSON schema counterparts.

- `bool`
  ```json
  {"type": "boolean"}
  ```
- `int`
  ```json
  {"type": "integer"}
  ```
- `float`
  ```json
  {"type": "number"}
  ```
- `str`
  ```json
  {"type": "string"}
  ```
- `None`
  ```json
  {"type": "null"}
  ```
- `typing.Any`
  ```json
  {
      "anyOf": [
          {"type": "object"},
          {"type": "array"},
          {"type": "null"},
          {"type": "string"},
          {"type": "boolean"},
          {"type": "integer"},
          {"type": "number"}
      ]
  }
  ```

#### Composite types

You can use the following composite types to build more complex validation. These examples are nested with atomic types,
so they are easy to understand, but you can nest your composite types with other composite types.

- `typing.Dict[str, int]`
  ```json
  {
      "type": "object",
      "additionalProperties": {
          "type": "integer"
      }
  }
  ```
- `typing.List[int]`
  ```json
  {
      "type": "array",
      "items": {
          "type": "integer"
      }
  }
  ```
- `typing.Literal["red", 5, 5.0, None, False]`
  ```json
  {
      "enum": ["red", 5, 5.0, null, false]
  }
  ```
- `typing.Optional[boolean]`
  ```json
  {
      "anyOf": [
          {"type": "null"},
          {"type": "boolean"}
      ]
  }
  ```
- `typing.Union[float, boolean]`
  ```json
  {
      "anyOf": [
          {"type": "number"},
          {"type": "boolean"}
      ]
  }
  ```

You can define your own types and re-use them:

```python
ServicePort = typing.Union[int, float]
ServiceConfig = typing.Dict[str, typing.Any]
ServiceState = typing.Literal["RUNNING", "STOPPED", "UNKNOWN"]
```

You can use `typing.TypedDict`, to build stronger validation on dict-like objects (Only class-based syntax). See how you
can chain types with no restrictions:

```python
class Service(typing.TypedDict, total=False):
    address: str
    port: ServicePort
    config: ServiceConfig
    state: ServiceState
    tags: typing.List[str]
    debug: bool
```

The flag `total=False` is there to indicate that the properties are not required, default value is `True`. See the
result:

```json
{
     "type": "object",
     "additionalProperties": false,
     "required": [],
     "properties": {
         "address": {
              "type": "string"
         },
         "port": {
              "anyOf": [
                   {"type": "integer"}, 
                   {"type": "number"}
              ]
         },
         "config": {
             "additionalProperties": {
                 "anyOf": [
                     {"type": "object"},
                     {"type": "array"},
                     {"type": "null"},
                     {"type": "string"},
                     {"type": "boolean"},
                     {"type": "integer"},
                     {"type": "number"}
                 ]
             },
             "type": "object"
         },
         "state": {
              "enum": ["RUNNING", "STOPPED", "UNKNOWN"]
         },
         "tags": {
              "type": "array",
              "items": {"type": "string"}
         },
         "debug": {
              "type": "boolean"
         }
     }
}
```

You can import these user-defined types within your package, and they will be picked up. However, due to the static
nature of the scan, custom types coming from external packages can't be easily followed and hence not supported yet.

### Default function arguments

Giving default values to your function arguments would make those properties not required in the output schema.

See this function:

```python
import typing


def my_func(a: str, b: int = 3):
    pass  # Some code
```

Now compare it with its JSON schema representation:

```json
{
    "my_func": {
        "input": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "a": {"type": "string"},
                "b": {"type": "integer"}
            },
            "required": ["a"],
            "additionalProperties": false
        },
        "output": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "null"
        }
    }
}
```

## References

- Typing module docs: [https://docs.python.org/3/library/typing.html](https://docs.python.org/3/library/typing.html)
- JSON schema SPEC: [https://json-schema.org/](https://json-schema.org/)
