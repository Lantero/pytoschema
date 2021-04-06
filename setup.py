import os
from setuptools import setup

TEST_DEPENDENCIES = [
    "black==20.8b1",
    "flake8==3.9.0",
    "pytest==6.2.3",
    "pytest-cov==2.11.1",
]

with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.md"), encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

setup(
    name="pytoschema",
    description="A package to convert Python type annotations into JSON schemas",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    version="1.0.0",
    author="Carlos Ruiz Lantero",
    author_email="carlos.ruiz.lantero@comprehensivetech.co.uk",
    maintainer="Carlos Ruiz Lantero",
    maintainer_email="carlos.ruiz.lantero@comprehensivetech.co.uk",
    url="https://github.com/comprehensivetech/pytoschema",
    packages=["pytoschema"],
    classifiers=[
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    tests_require=TEST_DEPENDENCIES,
    extras_require={"test": TEST_DEPENDENCIES},
)
