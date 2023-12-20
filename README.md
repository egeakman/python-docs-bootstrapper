# python-docs-bootstrapper

This repository contains the scripts and data used to bootstrap a new translation of the Python documentation.

## Why python-docs-bootstrapper?

...

## Installation

```bash
$ pip install python-docs-bootstrapper
```

## Usage

```bash
$ bootstrapper --help
usage: bootstrapper [-h] [-b BRANCH] language

positional arguments:
  language              IETF language tag (e.g. tr, pt-br)

options:
  -h, --help            show this help message and exit
  -b BRANCH, --branch BRANCH
                        CPython branch (e.g. 3.12)
```

## Example

```bash
$ bootstrapper tr --branch 3.12
```
