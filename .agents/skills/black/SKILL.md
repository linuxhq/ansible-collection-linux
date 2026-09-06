---
name: black
description: Format Python code with black.
---

# black

Matches CI's pre-commit hook.

```sh
tox run -e black -- plugins/modules/{{ file }}.py
tox run -m format
tox run -m lint
```

- Re-read a file if black rewrote it.
- black only formats — lint with `ruff`.

## Dependencies

- `tox` skill
