#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_snapshot
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Create a kopia snapshot
description:
  - Create a snapshot of a local path in the connected kopia repository.
  - The module is deliberately one-shot. Every run asks kopia to take a new
    snapshot, the same way C(kopia snapshot create) behaves, so it is not
    idempotent and belongs in a play that is meant to run on a schedule rather
    than in a converge that is expected to settle.
  - When the policy for the path sets C(retention.ignore_identical_snapshots)
    and no files have changed since the previous snapshot, kopia does not save
    a new snapshot. The module then reports RV(ignore:changed) as V(false) and
    returns the existing newest snapshot. Otherwise it reports
    RV(ignore:changed) as V(true).
  - When kopia printed the snapshot it saved, then exited with an error, for
    example fatal errors found while snapshotting or automatic maintenance
    failing afterwards, the module fails. It reports RV(ignore:changed) as
    V(true) and returns the snapshot in RV(snapshot) when kopia lists it, and
    fails without reporting a change when kopia does not list it, for example
    because its final repository flush failed. When the snapshots cannot be
    listed, it reports RV(ignore:changed) as V(true), as the snapshot may have
    been saved, with an empty RV(snapshot).
  - O(path) is made absolute and cleaned, as kopia does, and its snapshots
    are listed by that path, to which kopia adds the client user and host.
    kopia reads a bare path in which an V(@) comes before any V(:) as
    C(user@host) or C(user@host:path), so when the absolute path is such a
    path, such as V(/home/alice@example.com), it is listed by the source kopia
    records, C(user@host:/path), taken from the snapshot kopia printed or, when
    it printed none, from the client user and host reported by
    C(kopia repository status). A path with a V(:) before its first V(@), such
    as V(/srv/a:b@c), is read as a path.
  - kopia splits C(user@host:/path) at the first V(@) and the first V(:), so an
    absolute path in which an V(@) comes before any V(:) cannot be listed when
    the client user contains V(@) or V(:), such as V(alice@corp.example.com),
    or the host contains V(:). The module then fails before taking the
    snapshot.
notes:
  - A failure reported by kopia after it saved the snapshot without printing
    it, such as applying the retention policy, cannot be told apart from a
    snapshot that was not saved. The module then fails without reporting a
    change.
options:
  config_file:
    description:
      - Path to the kopia configuration file describing the connection.
      - Defaults to kopia's own configuration path when unset.
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
    type: path
  description:
    description:
      - Description recorded on the snapshot.
      - A description that is not valid UTF-8, such as one with a lone
        surrogate code point, is rejected before kopia runs, also in check
        mode, because kopia records it with U+FFFD in its place.
    type: str
  password:
    description:
      - Password securing the kopia repository.
      - Only needed when the repository configuration does not already hold the
        key, and exported to the kopia CLI as E(KOPIA_PASSWORD) rather than
        placed on the command line.
    type: str
  path:
    description:
      - Local path to snapshot.
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
      - A path that is not valid UTF-8, such as one with a lone surrogate code
        point, which Ansible uses for a byte that is not valid UTF-8, is
        rejected before kopia runs, also in check mode, because kopia records
        it with U+FFFD in its place and cannot list its snapshots.
    type: path
    required: true
  tags:
    description:
      - Tags to record on the snapshot.
      - Each entry becomes one C(--tags key:value) flag, with the key used as
        given.
      - kopia splits each flag at its first V(:), so a key containing V(:) is
        rejected before kopia runs. Values may contain V(:).
      - Values must be strings. Any other value, such as a number, Boolean,
        null, list or dictionary, is rejected before kopia runs. Quote literal
        numbers, Booleans and values that YAML reads as numbers, such as
        V("42"), V("true") or V("12:30"), to record them as text. A templated
        value can still be a number, because Ansible keeps the type a template
        renders, so convert it with C(| string), as in
        V("{{ build_number | string }}").
      - A key or value that is not valid UTF-8, such as one with a lone
        surrogate code point, is rejected before kopia runs, also in check
        mode, because kopia records it with U+FFFD in its place.
    type: dict
requirements:
  - kopia
attributes:
  check_mode:
    description:
      - Reports changed without creating a snapshot.
      - When the absolute O(path) is one in which an V(@) comes before any
        V(:), fails as a real run would when the snapshots of the path cannot
        be listed and kopia is installed.
      - Check mode cannot tell whether kopia would skip an identical snapshot,
        so it reports changed even when C(retention.ignore_identical_snapshots)
        would leave the repository unchanged.
    support: full
  diff_mode:
    description: Diff mode is not supported.
    support: none
"""

EXAMPLES = r"""
- name: Ensure kopia snapshot is created
  linuxhq.linux.kopia_snapshot:
    path: /home/vagrant

- name: Ensure kopia snapshot is created with a description and tags
  linuxhq.linux.kopia_snapshot:
    description: nightly
    path: /srv/data
    tags:
      role: database
      tier: production
"""

RETURN = r"""
snapshot:
  description:
    - Snapshot for the path, as reported by C(kopia snapshot list).
    - This is the snapshot just created, identified by the ID kopia prints when
      it saves it, or the existing newest snapshot when kopia skipped an
      identical snapshot. When the printed ID cannot be read or is not listed,
      the newest snapshot is returned.
    - Also returned when the module fails because kopia printed the snapshot
      it saved, then exited with an error, and kopia lists that snapshot.
    - Keys under C(tags) are returned as kopia reports them, such as
      C(tag:role).
    - Empty in check mode and when the snapshot manifest cannot be read back.
  returned: always
  type: dict
  sample:
    id: k9c8f0b1c2d3e4f5
    description: nightly
    start_time: '2026-07-25T10:15:00.000000-07:00'
    end_time: '2026-07-25T10:15:04.000000-07:00'
    stats:
      total_size: 10485760
"""

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    absolute_path,
    check_utf8,
    kopia_available,
    kopia_command,
    reads_as_user_host,
    snapshot_source,
)

OPERATION = "create kopia snapshot"
SOURCE_KEYS = ("userName", "host", "path")


def created_manifest(stdout):
    try:
        manifest = json.loads(stdout)
    except ValueError:
        return {}

    return manifest if isinstance(manifest, dict) else {}


def listed_source(manifest, source):
    # a source qualified as user@host:/path is listed as kopia recorded it when it printed one
    recorded = manifest.get("source")

    if (
        reads_as_user_host(source)
        and isinstance(recorded, dict)
        and all(isinstance(recorded.get(key), str) and recorded[key] for key in SOURCE_KEYS)
    ):
        return "{userName}@{host}:{path}".format(**recorded)

    return source


def list_snapshots(module, source):
    rc, stdout, _dummy = kopia_command(
        module, ["snapshot", "list", source, "--json"], password=module.params["password"]
    )

    if rc != 0:
        return None

    try:
        return json.loads(stdout) or []
    except ValueError:
        return None


def find_snapshot(snapshots, snapshot_id):
    return next((entry for entry in snapshots if snapshot_id and entry.get("id") == snapshot_id), None)


def snapshot_result(snapshot):
    return camel_dict_to_snake_dict(snapshot, ignore_list=["tags"]) if snapshot else {}


def latest_snapshot(module, source, snapshot_id=None):
    snapshots = list_snapshots(module, source) or []

    # another snapshot of the path, such as a scheduled one, can be newer than the one just created
    snapshot = find_snapshot(snapshots, snapshot_id) or (snapshots[-1] if snapshots else None)

    return snapshot_result(snapshot)


def ensure_present(module):
    path = module.params["path"]

    check_utf8(module, [(name, module.params[name]) for name in ("path", "description", "tags")])

    for key, value in (module.params["tags"] or {}).items():
        if ":" in key:
            module.fail_json(msg=f"invalid tag key {key!r}: kopia splits tags at the first ':'")

        if not isinstance(value, str):
            module.fail_json(
                msg=f"tag {key!r} value is not a string; pass it as a string, for example quoted or with the string filter"
            )

    if module.check_mode:
        if reads_as_user_host(absolute_path(path)) and kopia_available(module):
            snapshot_source(module, path, OPERATION)

        module.exit_json(changed=True, snapshot={})

    # a path that cannot be listed fails before kopia takes the snapshot
    source = snapshot_source(module, path, OPERATION)

    # an absolute path keeps a name such as "--all" from being read as an option
    command = ["snapshot", "create", absolute_path(path), "--json"]

    if module.params["description"]:
        command.append(f"--description={module.params['description']}")

    for key, value in sorted((module.params["tags"] or {}).items()):
        command.append(f"--tags={key}:{value}")

    rc, stdout, stderr = kopia_command(module, command, password=module.params["password"])
    manifest = created_manifest(stdout)
    snapshot_id = manifest.get("id")

    if rc != 0 and snapshot_id:
        # kopia prints the manifest once the snapshot is saved, then can fail on
        # fatal errors found while snapshotting or in automatic maintenance, but
        # also in the final repository flush, which leaves the snapshot unsaved
        snapshots = list_snapshots(module, listed_source(manifest, source))
        if snapshots is None:
            module.fail_json(
                msg=(
                    f"kopia snapshot {snapshot_id} of {path} may have been created, but kopia reported errors "
                    f"and the snapshots could not be listed: {stderr.strip()}"
                ),
                changed=True,
                snapshot={},
            )

        snapshot = find_snapshot(snapshots, snapshot_id)
        if snapshot:
            module.fail_json(
                msg=f"created kopia snapshot {snapshot_id} of {path}, but kopia reported errors: {stderr.strip()}",
                changed=True,
                snapshot=snapshot_result(snapshot),
            )

    if rc != 0:
        module.fail_json(msg=f"unable to create kopia snapshot of {path}: {stderr.strip()}", snapshot={})

    # kopia prints the new manifest only when it saves a snapshot; nothing is
    # printed when ignore_identical_snapshots skips an unchanged source.
    if not stdout.strip():
        module.exit_json(changed=False, snapshot=latest_snapshot(module, source))

    module.exit_json(changed=True, snapshot=latest_snapshot(module, listed_source(manifest, source), snapshot_id))


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "description": {"type": "str"},
        "password": {"type": "str", "no_log": True},
        "path": {"type": "path", "required": True},
        "tags": {"type": "dict"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    ensure_present(module)


if __name__ == "__main__":
    main()
