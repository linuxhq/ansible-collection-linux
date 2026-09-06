---
name: pyenv
description: Install the project's pinned Python version.
---

# pyenv

Use `pyenv` when the Python pinned in `.python-version` is unavailable. On macOS with Homebrew:

```sh
brew install pyenv
eval "$(pyenv init -)"
pyenv install -s "$(cat .python-version)"
```

`.python-version` already pins the version, so pyenv selects it automatically once the shims are
active. Confirm:

```sh
pyenv version
python --version
```

- Run once, before the `tox` skill, if the pinned Python isn't installed.
- Do not modify a shell profile unless the user explicitly requests a persistent setup.
- On other platforms, use the platform's supported pyenv installation method rather than
  Homebrew.

## Dependencies

- `pyenv`; Homebrew is required only for the macOS installation command above.
