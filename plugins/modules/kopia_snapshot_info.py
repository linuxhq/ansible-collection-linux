#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_snapshot_info
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Gather information about kopia snapshots
description:
  - Gather the snapshots held in the connected kopia repository, as reported by
    C(kopia snapshot list).
notes:
  - While another client upgrades the repository format, kopia fails rather
    than waiting for the upgrade to end.
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
      - Restrict the result to snapshots of this local path.
      - C(kopia snapshot list) also includes the snapshots of every parent
        directory of the path, since they contain it, so the result can hold
        more than one source.
      - All sources are listed when unset.
      - Made absolute and cleaned, as kopia does, and listed by that path, to
        which kopia adds the client user and host. kopia reads a bare path in
        which an V(@) comes before any V(:) as C(user@host) or
        C(user@host:path), and rejects one with no V(:) whose only V(@) is its
        last character, so when the absolute path is such a path, such as
        V(/home/alice@example.com) or V(/srv/backup@), it is listed as the
        source C(user@host:/path), with the client user and host reported by
        C(kopia repository status), as kopia records it. A path with a V(:)
        before its first V(@), such as V(/srv/a:b@c), is read as a path.
      - kopia splits C(user@host:/path) at the first V(@) and the first V(:), so
        the module fails when the absolute path is one in which an V(@) comes
        before any V(:) and the client user contains V(@) or V(:), such as
        V(alice@corp.example.com), or the host contains V(:).
      - Ansible expands a leading V(~) and environment variables in it, as for
        any C(path) option, before it is passed to kopia.
      - A path that is not valid UTF-8, with a lone surrogate code point,
        including U+DC80 to U+DCFF, which Ansible uses for bytes that are not
        valid UTF-8, is rejected before kopia runs, also in check mode. Ansible
        cannot run a task with such a path, as it fails while logging the
        arguments, or with C(no_log) rejects the module result.
    type: path
requirements:
  - kopia
attributes:
  check_mode:
    description: This module only retrieves information and does not modify state.
    support: full
    details: Returns empty result data when kopia is unavailable or no repository is connected.
  diff_mode:
    description: Diff mode is not supported.
    support: none
"""

EXAMPLES = r"""
- name: Gather all kopia snapshots
  linuxhq.linux.kopia_snapshot_info:
  register: __kopia_snapshot_query

- name: Gather kopia snapshots for one path
  linuxhq.linux.kopia_snapshot_info:
    path: /home/vagrant
  register: __kopia_snapshot_query
"""

RETURN = r"""
snapshots:
  description:
    - Snapshots reported by C(kopia snapshot list), grouped by source and
      oldest first within each source.
    - With O(path), the snapshots of its parent directories are included as
      well, each under its own C(source).
    - Keys under C(tags) are returned as kopia reports them, such as
      C(tag:role).
    - Empty when the module fails, and when kopia is unavailable or no
      repository is connected in check mode.
      Not returned when Ansible rejects the arguments, such as a missing
      required option, a value of the wrong type or an invalid choice, or fails
      to log them, such as for a lone surrogate code point in an option that is
      not secret, or when the kopia command is not found or cannot be started,
      such as for a NUL character in a value passed to it.
  returned: unless Ansible rejects or cannot log the arguments or start kopia
  type: list
  elements: dict
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
    - description: nightly
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
    check_connection,
    check_utf8,
    kopia_available,
    kopia_command,
    repository_status,
    snapshot_source,
    text_label,
)


def list_snapshots(module):
    failed_result = {"snapshots": []}

    check_connection(module, failed_result=failed_result)
    # Ansible cannot pass a path that is not valid UTF-8 through a task, and kopia lists a source by its path with
    # U+FFFD in place of those bytes
    check_utf8(module, [("path", module.params["path"])], failed_result=failed_result)

    status = None

    # an earlier task in check mode, such as kopia_repository, may only have predicted the connection
    if module.check_mode:
        if kopia_available(module):
            status = repository_status(module, password=module.params["password"], failed_result=failed_result)

        if status is None:
            module.exit_json(changed=False, snapshots=[])

    command = ["snapshot", "list", "--json"]
    source = ""

    if module.params["path"]:
        source = f" of {text_label(module.params['path'])}"
        target = snapshot_source(module, module.params["path"], "list kopia snapshots", failed_result, status)
        command.extend(["--", target])

    rc, stdout, stderr = kopia_command(module, command, password=module.params["password"])

    if rc != 0:
        module.fail_json(msg=f"unable to list kopia snapshots{source}: {stderr.strip()}", **failed_result)

    return [camel_dict_to_snake_dict(snapshot, ignore_list=["tags"]) for snapshot in json.loads(stdout)]


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "password": {"type": "str", "no_log": True},
        "path": {"type": "path"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    module.exit_json(changed=False, snapshots=list_snapshots(module))


if __name__ == "__main__":
    main()
