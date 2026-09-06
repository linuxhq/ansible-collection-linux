---
name: ruff
description: Lint Python code with ruff.
---

# ruff

```sh
tox run -e ruff-lint -- plugins/modules/{{ file }}.py
tox run -e ruff -- plugins/modules/{{ file }}.py
tox run -m lint
tox run -m format
```

- Clean run: `All checks passed!`.
- Fix by hand what `--fix` can't; re-read rewritten files.
- ruff only lints — format with `black`.

## Dependencies

- `tox` skill
