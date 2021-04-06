![Test](https://github.com/comprehensivetech/pytoschema/workflows/Test/badge.svg?branch=master)

# pytoschema

Package that uses static analysis - `ast` - to convert Python 3 function type annotations to JSON schemas.

- [https://docs.python.org/3/library/typing.html](https://docs.python.org/3/library/typing.html)
- [https://json-schema.org/](https://json-schema.org/)

This allows you to auto-generate the validation schemas for JSON-RPC backend functions written in Python.

Current support is for Python 3.8+ and JSON schema draft 7+.

## Getting started

#### Installation

From a Python 3.8+ environment, run `pip install pytoschema`.

#### Scan a package

After installing the package, you can open a python terminal from the root of the repo and run:

```python
import os
from pprint import pprint

from pytoschema.functions import process_package

pprint(process_package(os.path.join("test", "example")))
```

The example package will be scanned and JSON schemas will be generated for all the top level functions it can find.
  
#### Scan a file

You can also target specific files, which won't include the package namespacing in the result value. Following on the
same terminal:

```python
from pytoschema.functions import process_file

pprint(process_file(os.path.join("test", "example", "service.py")))
```

#### Include and exclude patterns

Include and exclude unix-like patterns can be used to filter function and module names we want to allow/disallow for
scanning. See the difference when you now run this instead:

```python
pprint(process_package(os.path.join("test", "example"), exclude_patterns=["_*"]))
```

Similarly, but applied to specific files:

```python
pprint(process_file(os.path.join("test", "example", "service.py"), include_patterns=["_*"]))
```

Things to take into account:
- Exclude pattern matching overwrite include matches. 
- `__init__.py` files are not affected by pattern rules and are always scanned. However, you can still filter its
  internal functions.

## Type annotation rules

Fitting Python's typing model to JSON means not everything is allowed in your function signatures. This is a natural
restriction that comes with JSON data serialization. Hopefully, most of the useful stuff you need is allowed.

#### Allowed types

##### Base types

Basic types `bool`, `int`, `float`, `str`, `None` and `typing.Any` are allowed. Also, you can build more complex, nested
structures with the usage of `typing.Union`, `typing.Optional`, `typing.Dict` (Only `str` keys are allowed),
`typing.List` and `typing.Literal`. All these types have a direct, non-ambiguous representation in both JSON and JSON 
schema.

##### Custom types

Your functions can also use custom types like the ones defined using an assignment of `typing.Union`, `typing.List`, 
`typing.Dict`, `typing.Literal` and `typing.Optional`, as in:

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

The flag `total=False` is there to indicate that not all properties are required, default is `True`.

##### Importing types from other files

You can import these custom types within your package and they will be picked up. However, due to the static nature of
the scan, custom types coming from external packages can't be followed and hence not supported. In other words, you can
only share these types within your package, using relative imports.

Other static analysis tools like `mypy` use a repository with stub files to solve this issue, see
[https://mypy.readthedocs.io/en/stable/stubs.html](https://mypy.readthedocs.io/en/stable/stubs.html). This is out of the
scope for a young project like this, at least for now.

#### Rules

1. The functions you want to scan need to be type annotated.

2. Only the types defined in the previous section can be used. They are the types that can be safely serialised as JSON.

3. Function arguments are meant to be passed in key-value format, like a json object. This puts a couple of restrictions
   regarding *args, **kwargs, positional-only and keyword-only arguments:
   
   The following is allowed:
   - ****kwargs**: `def func(**kwargs): pass`
   - **keyword-only arguments**: `def func(*, a): pass`
   
   The following is not allowed:
   - ***args**: `def func(*args): pass`
   - **positional-only arguments**: `def func(a, /): pass`