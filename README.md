# uno

[![PyPI - Version](https://img.shields.io/pypi/v/uno.svg)](https://pypi.org/project/uno)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/uno.svg)](https://pypi.org/project/uno)

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install uno
```

## License

`uno` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## TESTING PROCESS - run the following commands in order

- hatch dropdb (to completely destroy the database)
- hatch createdb (to recreate the database from scratch)
- hatch test
- hatch cov
- hatch cov-report
- hatch test-html
- open htmlcov/index.html