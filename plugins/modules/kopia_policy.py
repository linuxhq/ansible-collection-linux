#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_policy
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Manage a kopia snapshot policy
description:
  - Define, replace, or delete the snapshot policy for a kopia target.
  - The desired policy is compared against C(kopia policy export) and applied
    with C(kopia policy import), which replaces the defined policy for the
    target, so O(policy) always describes the complete desired policy.
notes:
  - kopia reads the repository password persisted next to the configuration
    file, in a file named after it with C(.kopia-password) added. When there
    is none, such as for a connection made with C(persist_credentials) set to
    V(false), the module fails rather than kopia waiting for the password on
    its standard input.
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
  policy:
    description:
      - Complete desired policy for the target, given as snake_case keys
        mirroring the JSON structure of C(kopia policy export), for example
        V(retention.keep_latest) or V(compression.compressor_name).
      - Keys are converted to kopia's camelCase, so V(keep_latest) becomes
        C(keepLatest). Write keys in snake_case, such as V(keep_latest), or in
        kopia's camelCase, such as V(keepLatest).
      - kopia matches keys to its fields ignoring case, but reports them in
        camelCase, so a key that converts to other capitalization would never
        match. A key that matches one of kopia's policy fields only ignoring
        case once converted, such as V(keeplatest), V(Retention) or
        V(KEEP_LATEST), is rejected before kopia runs, also in check mode,
        naming the field.
      - Of two keys that convert to the same key, such as V(keep_latest) and
        V(keepLatest), only the last one given is used.
      - kopia rejects a key that matches none of its policy fields when it
        imports the policy, before it changes the policy. Check mode does not
        predict that refusal.
      - A value that is not valid UTF-8, such as one with a lone surrogate code
        point, is rejected before kopia runs, also in check mode, because kopia
        records it with U+FFFD in its place.
      - Fields left out are removed from the defined policy and fall back to
        inherited values.
      - kopia does not store V(false), V(0), an empty string or an empty list
        for fields such as C(scheduling.manual), C(scheduling.interval_seconds),
        C(files.max_file_size), C(files.ignore), C(compression.compressor_name)
        or C(no_parent), so these values are treated as left out, the same as
        kopia treats them. Fields kopia stores as optional values, such as the
        C(retention) counts, keep V(0) and V(false).
      - kopia stores an action under C(actions), such as
        C(actions.before_snapshot_root), even when it is empty, such as V({}),
        and the target then no longer inherits that action, so an empty action
        is not treated as left out. A V(null) action is left out.
      - kopia stores V(null) in a list as the empty value of its items, so a
        V(null) item of a list of strings, such as C(files.ignore), is treated
        as an empty string, and a V(null) C(scheduling.time_of_day) entry, or a
        V(null) C(hour) or C(min) of one, as V(0).
      - Required when O(state=present). V(null) is treated as V({}), the empty
        policy, which replaces the defined policy.
    type: dict
  state:
    description:
      - V(present) ensures the defined policy matches O(policy) exactly.
      - V(absent) deletes the defined policy so the target only inherits.
    type: str
    choices:
      - absent
      - present
    default: present
  target:
    description:
      - Policy target, a directory path, C(user@host), C(user@host:/path), or
        V((global)) for the global policy.
      - kopia reads a target in which an V(@) comes before any V(:) as
        C(user@host) or C(user@host:path), so a directory whose path is such a
        path, such as V(/home/alice@example.com), must be written as
        C(user@host:/path). kopia rejects a target with no V(:) whose only V(@)
        is its last character, such as V(/srv/backup@), as an invalid host name
        before it changes anything, so such a directory must be written as
        C(user@host:/path) too. A path with a V(:) before its first
        V(@), such as V(/srv/a:b@c), is read as a directory path. A target that
        starts with V(@) and contains V(:), such as V(@host:/path), is read as
        a relative directory path.
      - kopia stores the user, host and path of C(user@host) and
        C(user@host:/path) as given. To match the snapshots of the client, the
        user and host must be the C(clientOptions.username) and
        C(clientOptions.hostname) reported by C(kopia repository status), where
        the host defaults to the short, lowercased hostname, and the path must
        be absolute and clean, without V(.) or V(..) components or a trailing
        V(/).
      - kopia splits C(user@host:/path) at the first V(@) and the first V(:), so
        when the client user contains V(@) or V(:), or the host contains V(:),
        no target can name a directory whose path is one in which an V(@) comes
        before any V(:), as kopia would store a different source.
      - kopia makes a bare directory path absolute and cleans it into the
        policy target. An empty target, which Ansible can pass for V(null),
        names the working directory of the module, such as the home directory
        of the remote user, as kopia reads it.
      - A target of 32 lowercase hexadecimal digits is rejected before kopia
        runs, also in check mode, because C(kopia policy export),
        C(kopia policy show) and C(kopia policy delete) read it as a manifest
        ID, such as that of another policy or of a snapshot, whose source they
        use instead, while C(kopia policy import) reads it as a path. Write a
        relative directory with such a name as V(./name).
      - A target that starts with V(-) is passed to kopia as a target, never as
        a command-line flag, so V(--global) is a relative directory path, and
        V(-svc@host:/path) names the client user V(-svc). The global policy is
        V((global)).
      - Passed to kopia as given, so V(~) and environment variables are not
        expanded.
      - With O(state=present), a target that is not valid UTF-8, such as one
        with a lone surrogate code point, is rejected before kopia runs, also
        in check mode, because kopia records it with U+FFFD in its place. With
        O(state=absent), only a lone surrogate code point from U+D800 to
        U+DC7F, which cannot be passed to kopia, is rejected, and U+DC80 to
        U+DCFF, which Ansible uses for bytes that are not valid UTF-8, are
        passed as those bytes.
    type: str
    required: true
requirements:
  - kopia >= 0.18.0
attributes:
  check_mode:
    description: Predicts changes without modifying the target.
    support: full
    details:
      - When kopia is unavailable or no repository is connected, reports
        changed for present policies and unchanged for absent policies, as a
        real run after earlier tasks install kopia and connect the repository.
  diff_mode:
    description: Diff mode is not supported.
    support: none
"""

EXAMPLES = r"""
- name: Ensure kopia snapshot policy is present
  linuxhq.linux.kopia_policy:
    state: present
    target: /home/vagrant
    policy:
      compression:
        compressor_name: gzip
      retention:
        keep_annual: 0
        keep_hourly: 24
        keep_latest: 2
        keep_monthly: 3
        keep_weekly: 4
      scheduling:
        interval_seconds: 3600

- name: Ensure kopia global policy is managed
  linuxhq.linux.kopia_policy:
    state: present
    target: (global)
    policy:
      retention:
        keep_latest: 10

- name: Ensure kopia snapshot policy is absent
  linuxhq.linux.kopia_policy:
    state: absent
    target: /home/vagrant
"""

RETURN = r"""
policy:
  description:
    - Defined policy reported by C(kopia policy export), as kopia reports it,
      including the empty sections it always writes, such as C(files).
    - In check mode, when a change would be made, the desired policy from
      O(policy), without the values kopia does not store, and with the empty
      sections kopia always writes. A key that is not valid UTF-8, which kopia
      would refuse, is returned with escapes, such as C(\udc80), in place of
      the characters it cannot encode.
    - Empty when kopia is unavailable or no repository is connected in check
      mode.
    - Empty when the module fails, also for an option value the module rejects
      before kopia runs. Not returned when Ansible rejects the arguments, such
      as a missing required option, a value of the wrong type or an invalid
      choice, or fails to log them, such as for a lone surrogate code point in
      an option that is not secret, or when the kopia command is not found or
      cannot be started, such as for a NUL character in a value passed to it.
  returned: when O(state=present)
  type: dict
  contains:
    actions:
      description:
        - Actions run before and after snapshots. Always returned, empty when
          no action is set.
      returned: always
      type: dict
      contains:
        after_folder:
          description:
            - Action run after the directory of the policy is snapshotted. An
              empty dictionary is an action defined without a command.
          returned: when set in the policy
          type: dict
          contains:
            path:
              description:
                - Command the action runs.
              returned: when set in the action
              type: str
            args:
              description:
                - Arguments passed to the command.
              returned: when set in the action
              type: list
              elements: str
            script:
              description:
                - Inline script the action runs in place of a command.
              returned: when set in the action
              type: str
            timeout:
              description:
                - Seconds kopia waits for the action to finish.
              returned: when set in the action
              type: int
            mode:
              description:
                - How kopia treats the action, such as C(essential),
                  C(optional) or C(async).
              returned: when set in the action
              type: str
        after_snapshot_root:
          description:
            - Action run after each snapshot root. An empty dictionary is an
              action defined without a command.
          returned: when set in the policy
          type: dict
          contains:
            path:
              description:
                - Command the action runs.
              returned: when set in the action
              type: str
            args:
              description:
                - Arguments passed to the command.
              returned: when set in the action
              type: list
              elements: str
            script:
              description:
                - Inline script the action runs in place of a command.
              returned: when set in the action
              type: str
            timeout:
              description:
                - Seconds kopia waits for the action to finish.
              returned: when set in the action
              type: int
            mode:
              description:
                - How kopia treats the action, such as C(essential),
                  C(optional) or C(async).
              returned: when set in the action
              type: str
        before_folder:
          description:
            - Action run before the directory of the policy is snapshotted. An
              empty dictionary is an action defined without a command.
          returned: when set in the policy
          type: dict
          contains:
            path:
              description:
                - Command the action runs.
              returned: when set in the action
              type: str
            args:
              description:
                - Arguments passed to the command.
              returned: when set in the action
              type: list
              elements: str
            script:
              description:
                - Inline script the action runs in place of a command.
              returned: when set in the action
              type: str
            timeout:
              description:
                - Seconds kopia waits for the action to finish.
              returned: when set in the action
              type: int
            mode:
              description:
                - How kopia treats the action, such as C(essential),
                  C(optional) or C(async).
              returned: when set in the action
              type: str
        before_snapshot_root:
          description:
            - Action run before each snapshot root. An empty dictionary is an
              action defined without a command.
          returned: when set in the policy
          type: dict
          contains:
            path:
              description:
                - Command the action runs.
              returned: when set in the action
              type: str
            args:
              description:
                - Arguments passed to the command.
              returned: when set in the action
              type: list
              elements: str
            script:
              description:
                - Inline script the action runs in place of a command.
              returned: when set in the action
              type: str
            timeout:
              description:
                - Seconds kopia waits for the action to finish.
              returned: when set in the action
              type: int
            mode:
              description:
                - How kopia treats the action, such as C(essential),
                  C(optional) or C(async).
              returned: when set in the action
              type: str
    compression:
      description:
        - Compression of file contents. Always returned, empty when nothing is
          set.
      returned: always
      type: dict
      contains:
        compressor_name:
          description:
            - Compressor kopia uses, such as C(zstd) or C(none).
          returned: when set in the policy
          type: str
        max_size:
          description:
            - Size in bytes above which files are not compressed.
          returned: when set in the policy
          type: int
        min_size:
          description:
            - Size in bytes below which files are not compressed.
          returned: when set in the policy
          type: int
        never_compress:
          description:
            - File name patterns that are never compressed.
          returned: when set in the policy
          type: list
          elements: str
        no_parent_never_compress:
          description:
            - Whether C(never_compress) of parent policies is ignored.
          returned: when set in the policy
          type: bool
        no_parent_only_compress:
          description:
            - Whether C(only_compress) of parent policies is ignored.
          returned: when set in the policy
          type: bool
        only_compress:
          description:
            - File name patterns that are the only ones compressed.
          returned: when set in the policy
          type: list
          elements: str
    error_handling:
      description:
        - Errors a snapshot ignores. Always returned, empty when nothing is
          set.
      returned: always
      type: dict
      contains:
        ignore_directory_errors:
          description:
            - Whether errors reading directories are ignored.
          returned: when set in the policy
          type: bool
        ignore_file_errors:
          description:
            - Whether errors reading files are ignored.
          returned: when set in the policy
          type: bool
        ignore_unknown_types:
          description:
            - Whether entries of unknown types are ignored.
          returned: when set in the policy
          type: bool
    files:
      description:
        - Files a snapshot ignores. Always returned, empty when nothing is set.
      returned: always
      type: dict
      contains:
        ignore:
          description:
            - Ignore rules, in C(.gitignore) syntax.
          returned: when set in the policy
          type: list
          elements: str
        ignore_cache_dirs:
          description:
            - Whether directories holding a C(CACHEDIR.TAG) file are ignored.
          returned: when set in the policy
          type: bool
        ignore_dot_files:
          description:
            - Names of files in each directory holding further ignore rules.
          returned: when set in the policy
          type: list
          elements: str
        max_file_size:
          description:
            - Size in bytes above which files are ignored.
          returned: when set in the policy
          type: int
        no_parent_dot_files:
          description:
            - Whether C(ignore_dot_files) of parent policies is ignored.
          returned: when set in the policy
          type: bool
        no_parent_ignore:
          description:
            - Whether C(ignore) of parent policies is ignored.
          returned: when set in the policy
          type: bool
        one_file_system:
          description:
            - Whether a snapshot stays on the file system of its root.
          returned: when set in the policy
          type: bool
    logging:
      description:
        - Detail of the log kopia writes for snapshots, from C(0) for none
          through C(5) for normal to C(10) for most.
      returned: always
      type: dict
      contains:
        directories:
          description:
            - Log detail for directories. Always returned, empty when nothing
              is set.
          returned: always
          type: dict
          contains:
            ignored:
              description:
                - Log detail for ignored directories.
              returned: when set in the policy
              type: int
            snapshotted:
              description:
                - Log detail for snapshotted directories.
              returned: when set in the policy
              type: int
        entries:
          description:
            - Log detail for entries. Always returned, empty when nothing is
              set.
          returned: always
          type: dict
          contains:
            cache_hit:
              description:
                - Log detail for entries found in the cache.
              returned: when set in the policy
              type: int
            cache_miss:
              description:
                - Log detail for entries not found in the cache.
              returned: when set in the policy
              type: int
            ignored:
              description:
                - Log detail for ignored entries.
              returned: when set in the policy
              type: int
            snapshotted:
              description:
                - Log detail for snapshotted entries.
              returned: when set in the policy
              type: int
    metadata_compression:
      description:
        - Compression of directory metadata. Always returned, empty when
          nothing is set.
      returned: always
      type: dict
      contains:
        compressor_name:
          description:
            - Compressor kopia uses for metadata.
          returned: when set in the policy
          type: str
    no_parent:
      description:
        - Whether the policy inherits nothing from parent policies.
      returned: when set in the policy
      type: bool
    os_snapshots:
      description:
        - Operating system snapshots taken before a snapshot.
      returned: always
      type: dict
      contains:
        volume_shadow_copy:
          description:
            - Windows Volume Shadow Copy. Always returned, empty when nothing
              is set.
          returned: always
          type: dict
          contains:
            enable:
              description:
                - Whether a snapshot is taken, C(0) never, C(1) always, failing
                  without one, or C(2) when available.
              returned: when set in the policy
              type: int
    retention:
      description:
        - Snapshots kept. Always returned, empty when nothing is set.
      returned: always
      type: dict
      contains:
        ignore_identical_snapshots:
          description:
            - Whether a snapshot identical to the previous one is not saved.
          returned: when set in the policy
          type: bool
        keep_annual:
          description:
            - Number of annual snapshots kept.
          returned: when set in the policy
          type: int
        keep_daily:
          description:
            - Number of daily snapshots kept.
          returned: when set in the policy
          type: int
        keep_hourly:
          description:
            - Number of hourly snapshots kept.
          returned: when set in the policy
          type: int
        keep_latest:
          description:
            - Number of latest snapshots kept.
          returned: when set in the policy
          type: int
        keep_monthly:
          description:
            - Number of monthly snapshots kept.
          returned: when set in the policy
          type: int
        keep_weekly:
          description:
            - Number of weekly snapshots kept.
          returned: when set in the policy
          type: int
    scheduling:
      description:
        - When kopia takes snapshots. Always returned, empty when nothing is
          set.
      returned: always
      type: dict
      contains:
        cron:
          description:
            - Cron expressions.
          returned: when set in the policy
          type: list
          elements: str
        interval_seconds:
          description:
            - Seconds between snapshots.
          returned: when set in the policy
          type: int
        manual:
          description:
            - Whether snapshots are only taken manually.
          returned: when set in the policy
          type: bool
        no_parent_time_of_day:
          description:
            - Whether C(time_of_day) of parent policies is ignored.
          returned: when set in the policy
          type: bool
        run_missed:
          description:
            - Whether a missed snapshot is taken at once.
          returned: when set in the policy
          type: bool
        time_of_day:
          description:
            - Times of day snapshots are taken.
          returned: when set in the policy
          type: list
          elements: dict
          contains:
            hour:
              description:
                - Hour, from C(0) to C(23).
              returned: always
              type: int
            min:
              description:
                - Minute, from C(0) to C(59).
              returned: always
              type: int
    splitter:
      description:
        - How files are split into content. Always returned, empty when nothing
          is set.
      returned: always
      type: dict
      contains:
        algorithm:
          description:
            - Splitter algorithm.
          returned: when set in the policy
          type: str
    upload:
      description:
        - Upload parallelism. Always returned, empty when nothing is set.
      returned: always
      type: dict
      contains:
        max_parallel_file_reads:
          description:
            - Number of files read at the same time.
          returned: when set in the policy
          type: int
        max_parallel_snapshots:
          description:
            - Number of snapshots taken at the same time.
          returned: when set in the policy
          type: int
        parallel_upload_above_size:
          description:
            - Size in bytes above which a file is uploaded in parallel parts.
          returned: when set in the policy
          type: int
  sample:
    actions: {}
    compression:
      compressor_name: gzip
    error_handling: {}
    files: {}
    logging:
      directories: {}
      entries: {}
    metadata_compression: {}
    os_snapshots:
      volume_shadow_copy: {}
    retention:
      keep_hourly: 24
      keep_latest: 2
    scheduling:
      interval_seconds: 3600
    splitter: {}
    upload: {}
"""

import json
import os

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import (
    camel_dict_to_snake_dict,
    dict_merge,
    snake_dict_to_camel_dict,
)

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    POLICY_EXPORT_SECTIONS,
    POLICY_FIELDS,
    check_connection,
    check_policy_target,
    check_utf8,
    kopia_available,
    kopia_command,
    policy_export,
    policy_field_mismatch,
    policy_normalize,
    repository_connected,
    same_value,
    text_label,
    text_labels,
)


def camel_key(key):
    return next(iter(snake_dict_to_camel_dict({key: None})))


def snake_key(key):
    return next(iter(camel_dict_to_snake_dict({key: None})))


def policy_values(value, name):
    """Yield (name, item) for each value in value that is neither a dictionary nor a list, named by its keys."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield from policy_values(item, f"{name}.{text_label(key)}")

    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from policy_values(item, f"{name}[{index}]")

    else:
        yield name, value


def check_policy_keys(module, value, name, fields=None):
    """Fail naming the first key that kopia would read differently than it reports it.

    fields holds kopia's field names for value, see POLICY_FIELDS, or None when they are unknown.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{name}.{text_label(key)}"
            camel = camel_key(key)

            # kopia matches field names ignoring case, so it accepts such a key, then reports the field in camelCase
            field = policy_field_mismatch(camel, fields)
            if field:
                spelling = field if snake_key(field) == field else f"{snake_key(field)} or {field}"
                module.fail_json(
                    msg=f"invalid policy key {child}: kopia matches it to its field {field} ignoring case, so it would never match; write {spelling}",
                    policy={},
                )

            check_policy_keys(module, item, child, fields.get(camel) if isinstance(fields, dict) else None)

    elif isinstance(value, list):
        for index, item in enumerate(value):
            check_policy_keys(module, item, f"{name}[{index}]", fields[0] if isinstance(fields, list) else None)


def ensure_present(module):
    target = module.params["target"]
    # required_if accepts a null policy, which defines the empty policy, the same as {}
    policy = module.params["policy"] or {}

    check_connection(module, failed_result={"policy": {}})
    # kopia policy export reads the target as an argument, and kopia policy import as JSON, with U+FFFD in place of a
    # lone surrogate, as it reads a value, so such a target or value would never match
    check_utf8(
        module,
        [("target", target)] + list(policy_values(policy, "policy")),
        failed_result={"policy": {}},
    )
    check_policy_target(module, target, failed_result={"policy": {}})
    check_policy_keys(module, policy, "policy", POLICY_FIELDS)

    # an earlier task in check mode, such as kopia_repository, may only have predicted the connection
    if module.check_mode and not (
        kopia_available(module) and repository_connected(module, failed_result={"policy": {}})
    ):
        module.exit_json(changed=True, policy={})

    desired = policy_normalize(snake_dict_to_camel_dict(policy))
    current = policy_export(module, target, failed_result={"policy": {}})

    if current is not None and same_value(policy_normalize(current), desired):
        module.exit_json(changed=False, policy=camel_dict_to_snake_dict(current))

    # kopia exports the sections it always writes, and a key that is not valid UTF-8, which kopia refuses as an
    # unknown field when it imports the policy, is escaped
    if module.check_mode:
        predicted = dict_merge(POLICY_EXPORT_SECTIONS, desired)
        module.exit_json(changed=True, policy=text_labels(camel_dict_to_snake_dict(predicted)))

    source = os.path.join(module.tmpdir, "policy.json")
    with open(source, "w") as handle:
        json.dump({target: desired}, handle)

    rc, _dummy, stderr = kopia_command(module, ["policy", "import", "--from-file", source])

    if rc != 0:
        module.fail_json(msg=f"unable to import kopia policy {text_label(target)}: {stderr.strip()}", policy={})

    current = policy_export(module, target, failed_result={"changed": True, "policy": {}})

    module.exit_json(changed=True, policy=camel_dict_to_snake_dict(current or {}))


def ensure_absent(module):
    target = module.params["target"]

    check_connection(module)
    # run_command cannot pass U+D800 to U+DC7F to kopia
    check_utf8(module, [("target", target)], errors="surrogateescape")
    check_policy_target(module, target)

    if module.check_mode and not (kopia_available(module) and repository_connected(module)):
        module.exit_json(changed=False)

    current = policy_export(module, target)

    if current is None:
        module.exit_json(changed=False)

    if module.check_mode:
        module.exit_json(changed=True)

    rc, _dummy, stderr = kopia_command(module, ["policy", "delete", "--", target])

    if rc != 0:
        module.fail_json(msg=f"unable to delete kopia policy {text_label(target)}: {stderr.strip()}")

    module.exit_json(changed=True)


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "policy": {"type": "dict"},
        "state": {
            "type": "str",
            "choices": ["absent", "present"],
            "default": "present",
        },
        "target": {"type": "str", "required": True},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[("state", "present", ("policy",))],
        supports_check_mode=True,
    )

    if module.params["state"] == "present":
        ensure_present(module)

    ensure_absent(module)


if __name__ == "__main__":
    main()
