---
name: yamllint
description: Lint YAML files with yamllint.
---

# yamllint

Matches CI's `--strict` mode.

```sh
tox run -e yamllint -- roles/{{ role }}/tasks/main.yml
tox run -m lint
```

- Clean run prints nothing; fix each line by hand.
- Checks raw YAML only — also run `ansible-lint` on role changes.

## Dependencies

- `tox` skill
