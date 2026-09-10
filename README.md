# linuxhq.linux

[![License](https://img.shields.io/badge/license-GPLv3-lightgreen)](https://www.gnu.org/licenses/gpl-3.0.en.html#license-text)
[![Ansible Galaxy](https://img.shields.io/badge/collection-linuxhq.linux-blue)](https://galaxy.ansible.com/linuxhq/linux)
[![Lint](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/pre-commit.yml)
[![Release](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/release.yml/badge.svg)](https://github.com/linuxhq/ansible-collection-linux/actions/workflows/release.yml)

An Ansible collection of Linux modules, plugins, and roles.

## Requirements

See [requirements.yml](requirements.yml).

## Installation

```sh
ansible-galaxy collection install linuxhq.linux
```

## Development

Local Tox environments use the Python version selected by `.python-version`.

With Tox installed, install the pre-commit hook:

```sh
tox run -e pre-commit
```

Tox manages isolated environments under `.tox/`; no environment activation is required.

### Checks

Run the default checks:

```sh
tox
```

Run grouped checks:

```sh
tox run -m format
tox run -m lint
tox run -m unit
```

Run Ansible sanity tests for a module:

```sh
tox run -e ansible-test -- sanity plugins/modules/systemd_timedate.py
```

### Molecule

Each role has a Molecule scenario that also serves as an example playbook. Set `MOLECULE_ROLE`
to select a role:

```sh
MOLECULE_ROLE=group tox run -e molecule -- test -s default
```

### Changelog and build

```sh
tox run -e changelog -- generate
tox run -e build
```
