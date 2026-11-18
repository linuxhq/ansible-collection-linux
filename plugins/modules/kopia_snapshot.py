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
    and no files have changed since the newest complete snapshot, kopia does
    not save a new snapshot. The module then reports RV(ignore:changed) as
    V(false) and returns that snapshot, never a newer incomplete one, such as
    a checkpoint. Otherwise it reports
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
    C(user@host) or C(user@host:path), and rejects one with no V(:) whose only
    V(@) is its last character, so when the absolute path is such a path, such
    as V(/home/alice@example.com) or V(/srv/backup@), it is listed by the
    source kopia records, C(user@host:/path), taken from the snapshot kopia
    printed or, when it printed none, from the client user and host reported
    by C(kopia repository status). A path with a V(:) before its first V(@),
    such as V(/srv/a:b@c), is read as a path.
  - kopia splits C(user@host:/path) at the first V(@) and the first V(:), so an
    absolute path in which an V(@) comes before any V(:) cannot be listed when
    the client user contains V(@) or V(:), such as V(alice@corp.example.com),
    or the host contains V(:). The module then fails before taking the
    snapshot.
notes:
  - While another client upgrades the repository format, kopia fails rather
    than waiting for the upgrade to end.
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
      - kopia looks up a bare file name, without a directory, in its
        configuration directory, C($XDG_CONFIG_HOME/kopia) or
        C(~/.config/kopia), not in the working directory, so write V(./name)
        for a file in the working directory.
      - A path with a lone surrogate code point from U+D800 to U+DC7F, which
        cannot be passed to kopia, is rejected before kopia runs, also in
        check mode. U+DC80 to U+DCFF, which Ansible uses for bytes that are
        not valid UTF-8, are passed as those bytes.
    type: path
  description:
    description:
      - Description recorded on the snapshot.
      - A description with a lone surrogate code point from U+D800 to U+DC7F,
        which cannot be passed to kopia, is rejected before kopia runs, also in
        check mode. U+DC80 to U+DCFF, which Ansible uses for bytes that are not
        valid UTF-8, are passed as those bytes, which kopia records with U+FFFD
        in their place.
    type: str
  password:
    description:
      - Password securing the kopia repository.
      - Only needed when the repository configuration does not already hold the
        key, and exported to the kopia CLI as E(KOPIA_PASSWORD) rather than
        placed on the command line.
      - When it is not given, kopia reads the password persisted next to the
        configuration file, in a file named after it with C(.kopia-password)
        added. When there is none, such as for a connection made with
        C(persist_credentials) set to V(false), the module fails rather than
        kopia waiting for the password on its standard input.
      - kopia reads an empty password as no password, so it reads the
        persisted one, as when the password is not given.
      - kopia removes whitespace around a given password, so a password of
        only whitespace is used as an empty password, without falling back to
        the persisted one.
    type: str
  path:
    description:
      - Local path to snapshot.
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
      - A path that is not valid UTF-8, with a lone surrogate code point,
        including U+DC80 to U+DCFF, which Ansible uses for bytes that are not
        valid UTF-8, is rejected before kopia runs, also in check mode. Ansible
        cannot run a task with such a path, as it fails while logging the
        arguments, or with C(no_log) rejects the module result after kopia
        saved the snapshot.
      - An empty path, which Ansible can pass for V(null), is made absolute
        as the working directory of the module, such as the home directory of
        the remote user, and that directory is snapshotted, as kopia does.
    type: path
    required: true
  tags:
    description:
      - Tags to record on the snapshot.
      - Each entry becomes one C(--tags key:value) flag, with the key used as
        given and the value written as Python writes it.
      - kopia splits each flag at its first V(:), so a key containing V(:) is
        recorded as a different key and value. Values may contain V(:).
      - Quote a value that YAML reads as a number, a Boolean or null whose
        text differs, such as V("1.10"), V("0755"), V("12:30") or V("true"),
        to record it as written.
      - A key or value with a lone surrogate code point from U+D800 to
        U+DC7F, which cannot be passed to kopia, is rejected before kopia runs,
        also in check mode. U+DC80 to U+DCFF, which Ansible uses for bytes that
        are not valid UTF-8, are passed as those bytes, which kopia records with
        U+FFFD in their place.
    type: dict
requirements:
  - kopia
attributes:
  check_mode:
    description:
      - Reports changed without creating a snapshot.
      - When the absolute O(path) is one in which an V(@) comes before any
        V(:), fails as a real run would when the snapshots of the path cannot
        be listed, kopia is installed and a repository is connected.
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
      it saves it, or the newest complete snapshot of the path when kopia
      skipped an identical snapshot, or empty when the path has no complete
      snapshot. When the printed ID cannot be read or is not listed, the newest
      snapshot of the path is returned, never one of a parent directory, which
      C(kopia snapshot list) also reports, or empty when the path has none,
      such as when another client deleted the new snapshot before the module
      listed it.
    - Also returned when the module fails because kopia printed the snapshot
      it saved, then exited with an error, and kopia lists that snapshot.
      Otherwise empty when the module fails after running kopia.
    - Keys under C(tags) are returned as kopia reports them, such as
      C(tag:role).
    - Empty in check mode and when the snapshot manifest cannot be read back.
    - Empty when the module fails before running kopia, such as for an option
      value the module rejects. Not returned when Ansible rejects the arguments,
      such as a missing required option, a value of the wrong type or an invalid
      choice, or fails to log them, such as for a lone surrogate code point in
      an option that is not secret, or when the kopia command is not found or
      cannot be started, such as for a NUL character in a value passed to it.
  returned: unless Ansible rejects or cannot log the arguments or start kopia
  type: dict
  contains:
    description:
      description:
        - Description of the snapshot, empty when none was given.
      returned: always
      type: str
    end_time:
      description:
        - Time the snapshot ended, in UTC with nanoseconds, such as
          C(2026-07-25T17:15:04.123456789Z).
      returned: always
      type: str
    id:
      description:
        - Manifest ID of the snapshot, 32 lowercase hexadecimal digits.
      returned: always
      type: str
    incomplete:
      description:
        - Reason kopia saved the snapshot incomplete.
      returned: when the snapshot is incomplete
      type: str
    pins:
      description:
        - Pins that keep the snapshot from expiring.
      returned: when the snapshot is pinned
      type: list
      elements: str
    retention_reason:
      description:
        - Retention rules that keep the snapshot, such as C(latest-1).
      returned: when a retention rule keeps the snapshot
      type: list
      elements: str
    root_entry:
      description:
        - Root directory entry of the snapshot.
        - Other fields kopia reports are passed through.
      returned: always
      type: dict
      contains:
        mode:
          description:
            - Permissions of the directory in octal, such as C(0755).
          returned: unless the directory has no permission bits set
          type: str
        mtime:
          description:
            - Modification time of the directory, in UTC with nanoseconds.
          returned: always
          type: str
        name:
          description:
            - Name of the directory.
          returned: always
          type: str
        obj:
          description:
            - Object ID of the directory listing.
          returned: always
          type: str
        summ:
          description:
            - Summary of the directory tree.
            - Other fields kopia reports are passed through.
          returned: always
          type: dict
          contains:
            dirs:
              description:
                - Number of directories.
              returned: always
              type: int
            files:
              description:
                - Number of files.
              returned: always
              type: int
            max_time:
              description:
                - Latest modification time in the tree, in UTC with
                  nanoseconds.
              returned: always
              type: str
            num_failed:
              description:
                - Number of entries that failed.
              returned: always
              type: int
            size:
              description:
                - Total size of the files in bytes.
              returned: always
              type: int
            symlinks:
              description:
                - Number of symbolic links.
              returned: always
              type: int
        type:
          description:
            - Entry type, C(d) for a directory.
          returned: always
          type: str
    source:
      description:
        - Source of the snapshot.
      returned: always
      type: dict
      contains:
        host:
          description:
            - Host name of the client that took the snapshot.
          returned: always
          type: str
        path:
          description:
            - Absolute path of the snapshotted directory.
          returned: always
          type: str
        user_name:
          description:
            - User name of the client that took the snapshot.
          returned: always
          type: str
    start_time:
      description:
        - Time the snapshot started, in UTC with nanoseconds, such as
          C(2026-07-25T17:15:00.123456789Z).
      returned: always
      type: str
    stats:
      description:
        - Statistics of the snapshot.
      returned: always
      type: dict
      contains:
        cached_files:
          description:
            - Number of files found unchanged in the previous snapshot.
          returned: always
          type: int
        dir_count:
          description:
            - Number of directories.
          returned: always
          type: int
        error_count:
          description:
            - Number of errors.
          returned: always
          type: int
        excluded_dir_count:
          description:
            - Number of excluded directories.
          returned: always
          type: int
        excluded_file_count:
          description:
            - Number of excluded files.
          returned: always
          type: int
        excluded_total_size:
          description:
            - Total size of the excluded files in bytes.
          returned: always
          type: int
        file_count:
          description:
            - Number of files read.
          returned: always
          type: int
        ignored_error_count:
          description:
            - Number of ignored errors.
          returned: always
          type: int
        non_cached_files:
          description:
            - Number of files read because they changed.
          returned: always
          type: int
        total_size:
          description:
            - Total size of the files in bytes.
          returned: always
          type: int
    storage_stats:
      description:
        - Storage used by the snapshot, as kopia reports it.
        - Its fields are passed through.
      returned: when kopia has computed it
      type: dict
    tags:
      description:
        - Tags of the snapshot, keyed as kopia reports them, such as
          C(tag:role).
      returned: when the snapshot has tags
      type: dict
  sample:
    description: nightly
    end_time: '2026-07-25T17:15:04.008021971Z'
    id: 18667b2ef651cb5660945854da507d80
    retention_reason:
      - latest-1
      - daily-1
    root_entry:
      mode: '0755'
      mtime: '2026-07-25T17:10:43.219843589Z'
      name: vagrant
      obj: k0188cac21bdbd0700f80f3623444f0dc
      summ:
        dirs: 4
        files: 120
        max_time: '2026-07-25T17:10:43.219843589Z'
        num_failed: 0
        size: 10485760
        symlinks: 0
      type: d
    source:
      host: server
      path: /home/vagrant
      user_name: root
    start_time: '2026-07-25T17:15:00.005833669Z'
    stats:
      cached_files: 0
      dir_count: 4
      error_count: 0
      excluded_dir_count: 0
      excluded_file_count: 0
      excluded_total_size: 0
      file_count: 120
      ignored_error_count: 0
      non_cached_files: 120
      total_size: 10485760
    tags:
      tag:role: web
"""

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    absolute_path,
    check_connection,
    check_utf8,
    client_source,
    kopia_available,
    kopia_command,
    reads_as_user_host,
    repository_status,
    snapshot_source,
    text_label,
)

OPERATION = "create kopia snapshot"


def created_manifest(stdout):
    # kopia prints nothing when it skips an identical snapshot
    try:
        return json.loads(stdout)
    except ValueError:
        return {}


def listed_source(manifest, source):
    # a source qualified as user@host:/path is listed as kopia recorded it when it printed one
    recorded = manifest.get("source")

    if reads_as_user_host(source) and recorded:
        return "{userName}@{host}:{path}".format(**recorded)

    return source


def list_snapshots(module, source):
    rc, stdout, _dummy = kopia_command(
        module, ["snapshot", "list", "--json", "--", source], password=module.params["password"]
    )

    if rc != 0:
        return None

    return json.loads(stdout)


def find_snapshot(snapshots, snapshot_id):
    return next((entry for entry in snapshots if snapshot_id and entry.get("id") == snapshot_id), None)


def snapshot_result(snapshot):
    return camel_dict_to_snake_dict(snapshot, ignore_list=["tags"]) if snapshot else {}


def recorded_path(manifest, path):
    """Return the path of the source kopia recorded, as it printed it or, when it printed none, as it records path."""
    recorded = manifest.get("source")

    return recorded["path"] if recorded else absolute_path(path)


def latest_snapshot(module, source, path, snapshot_id=None, complete=False):
    snapshots = list_snapshots(module, source) or []

    # another snapshot of the path, such as a scheduled one, can be newer than the one just created
    snapshot = find_snapshot(snapshots, snapshot_id)

    # another client can delete the new snapshot before it is listed, and kopia also lists the snapshots of every
    # parent directory of the source, for the same user and host, and incomplete ones, such as checkpoints
    if snapshot is None:
        own = [
            entry
            for entry in snapshots
            if entry["source"]["path"] == path and not (complete and entry.get("incomplete"))
        ]
        snapshot = own[-1] if own else None

    return snapshot_result(snapshot)


def ensure_present(module):
    path = module.params["path"]

    check_connection(module, failed_result={"snapshot": {}})
    # Ansible cannot pass a path that is not valid UTF-8 through a task, failing to log it, or with no_log rejecting
    # the reply after kopia saved the snapshot, which kopia lists by its path with U+FFFD in place of those bytes
    check_utf8(module, [("path", path)], failed_result={"snapshot": {}})
    # run_command cannot pass U+D800 to U+DC7F to kopia
    check_utf8(
        module,
        [(name, module.params[name]) for name in ("description", "tags")],
        errors="surrogateescape",
        failed_result={"snapshot": {}},
    )

    if module.check_mode:
        absolute = absolute_path(path)

        # an earlier task in check mode, such as kopia_repository, may only have predicted the connection
        if reads_as_user_host(absolute) and kopia_available(module):
            status = repository_status(module, password=module.params["password"], failed_result={"snapshot": {}})

            if status is not None:
                client_source(module, absolute, status, OPERATION, failed_result={"snapshot": {}})

        module.exit_json(changed=True, snapshot={})

    # a path that cannot be listed fails before kopia takes the snapshot
    source = snapshot_source(module, path, OPERATION, failed_result={"snapshot": {}})

    # an absolute path keeps a name such as "--all" from being read as an option
    command = ["snapshot", "create", absolute_path(path), "--json"]

    if module.params["description"]:
        command.append(f"--description={module.params['description']}")

    for key, value in sorted((module.params["tags"] or {}).items()):
        command.append(f"--tags={key}:{value}")

    rc, stdout, stderr = kopia_command(module, command, password=module.params["password"])
    manifest = created_manifest(stdout)
    label = text_label(path)
    snapshot_id = manifest.get("id")

    if rc != 0 and snapshot_id:
        # kopia prints the manifest once the snapshot is saved, then can fail on
        # fatal errors found while snapshotting or in automatic maintenance, but
        # also in the final repository flush, which leaves the snapshot unsaved
        snapshots = list_snapshots(module, listed_source(manifest, source))
        if snapshots is None:
            module.fail_json(
                msg=f"kopia snapshot {snapshot_id} of {label} may have been created, but kopia reported errors and could not list it: {stderr.strip()}",
                changed=True,
                snapshot={},
            )

        snapshot = find_snapshot(snapshots, snapshot_id)
        if snapshot:
            module.fail_json(
                msg=f"created kopia snapshot {snapshot_id} of {label}, but kopia reported errors: {stderr.strip()}",
                changed=True,
                snapshot=snapshot_result(snapshot),
            )

    if rc != 0:
        module.fail_json(msg=f"unable to create kopia snapshot of {label}: {stderr.strip()}", snapshot={})

    # kopia prints the new manifest only when it saves a snapshot; nothing is
    # printed when ignore_identical_snapshots skips a source identical to its
    # newest complete snapshot.
    if not stdout.strip():
        module.exit_json(
            changed=False, snapshot=latest_snapshot(module, source, recorded_path(manifest, path), complete=True)
        )

    module.exit_json(
        changed=True,
        snapshot=latest_snapshot(module, listed_source(manifest, source), recorded_path(manifest, path), snapshot_id),
    )


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
