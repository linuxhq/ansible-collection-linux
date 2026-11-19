#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: kopia_policy_info
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Gather kopia snapshot policies
description:
  - List the policies defined in the kopia repository, or look up a single
    target's defined and effective policy.
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
        policy target. An empty target names the working directory of the
        module, such as the home directory of the remote user, as kopia reads
        it.
      - When set, RV(policy) and RV(effective_policy) are returned for the
        single target instead of RV(policies).
      - A target of 32 lowercase hexadecimal digits is rejected before kopia
        runs, also in check mode, because C(kopia policy export) and
        C(kopia policy show) read it as a manifest ID, such as that of another
        policy or of a snapshot, and would report the policy of that source
        instead. Write a relative directory with such a name as V(./name).
      - A target that starts with V(-) is passed to kopia as a target, never as
        a command-line flag, so V(--global) is a relative directory path, and
        V(-svc@host:/path) names the client user V(-svc). The global policy is
        V((global)).
      - Passed to kopia as given, so V(~) and environment variables are not
        expanded.
      - A target with a lone surrogate code point from U+D800 to U+DC7F, which
        cannot be passed to kopia, is rejected before kopia runs, also in check
        mode. U+DC80 to U+DCFF, which Ansible uses for bytes that are not valid
        UTF-8, are passed as those bytes.
    type: str
requirements:
  - kopia >= 0.18.0
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
- name: Ensure kopia policies are gathered
  linuxhq.linux.kopia_policy_info:
  register: __kopia_policy_query

- name: Ensure kopia policy for a target is gathered
  linuxhq.linux.kopia_policy_info:
    target: /home/vagrant
  register: __kopia_policy_query
"""

RETURN = r"""
defined:
  description:
    - Whether a policy is defined for O(target).
    - Not returned when the module fails, as it is then unknown, nor when
      kopia is unavailable or no repository is connected in check mode.
  returned: >-
    when O(target) is set and the module succeeds, unless kopia is unavailable
    or no repository is connected in check mode
  type: bool
  sample: true
effective_policy:
  description:
    - Effective policy for O(target) reported by C(kopia policy show).
    - Each value comes from the most specific policy that sets it, from the
      policy of O(target) up through its parent policies to the global policy,
      and otherwise from the built-in defaults kopia merges into the policy.
      Each field below states whether those defaults fill it. A value kopia
      only falls back to when it takes a snapshot, such as the CPU count for
      C(upload.max_parallel_file_reads), is not returned unless a policy sets
      it.
    - V(false), V(0) and empty values count as set, and so override parent
      policies, only in C(error_handling), C(logging), C(retention), C(upload),
      C(files.ignore_cache_dirs), C(files.one_file_system),
      C(os_snapshots.volume_shadow_copy.enable) and C(scheduling.run_missed).
      kopia does not store them in other fields, such as C(scheduling.manual)
      or C(compression.max_size), so there a parent value applies.
    - C(compression.never_compress), C(compression.only_compress) and
      C(scheduling.time_of_day) instead combine the entries of each policy up
      to the first that sets C(compression.no_parent_never_compress),
      C(compression.no_parent_only_compress) or
      C(scheduling.no_parent_time_of_day) respectively.
    - When a policy sets C(no_parent), the policies above it and kopia's
      defaults are ignored, so only the values set from O(target) up to that
      policy are returned. C(no_parent) itself is never returned.
    - Empty when the module fails, and when kopia is unavailable or no
      repository is connected in check mode.
      Not returned when Ansible rejects the arguments, such as a missing
      required option, a value of the wrong type or an invalid choice, or fails
      to log them, such as for a lone surrogate code point in an option that is
      not secret, or when the kopia command is not found or cannot be started,
      such as for a NUL character in a value passed to it.
  returned: when O(target) is set
  type: dict
  contains:
    actions:
      description:
        - Actions run before and after snapshots. Always returned, empty when
          no action is set.
        - Each action is taken whole from the most specific policy that sets
          it, even as an empty dictionary, without filling its missing fields
          from parent policies.
      returned: always
      type: dict
      contains:
        after_folder:
          description:
            - Action run after the directory of the policy is snapshotted. An
              empty dictionary is an action defined without a command.
          returned: >-
            when set in the policy of O(target) itself, unless a policy sets
            C(no_parent)
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
          returned: when set in the policy or a parent policy
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
          returned: >-
            when set in the policy of O(target) itself, unless a policy sets
            C(no_parent)
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
          returned: when set in the policy or a parent policy
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
        - Compression of file contents. Always returned, empty only when a
          policy sets C(no_parent) and no policy sets a value in it.
      returned: always
      type: dict
      contains:
        compressor_name:
          description:
            - Compressor kopia uses, such as C(zstd) or C(none).
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: str
        max_size:
          description:
            - Size in bytes above which files are not compressed.
          returned: when set in the policy or a parent policy
          type: int
        min_size:
          description:
            - Size in bytes below which files are not compressed.
          returned: when set in the policy or a parent policy
          type: int
        never_compress:
          description:
            - File name patterns that are never compressed.
          returned: when set in the policy or a parent policy
          type: list
          elements: str
        no_parent_never_compress:
          description:
            - Whether C(never_compress) of parent policies is ignored.
          returned: when set in the policy or a parent policy
          type: bool
        no_parent_only_compress:
          description:
            - Whether C(only_compress) of parent policies is ignored.
          returned: when set in the policy or a parent policy
          type: bool
        only_compress:
          description:
            - File name patterns that are the only ones compressed.
          returned: when set in the policy or a parent policy
          type: list
          elements: str
    error_handling:
      description:
        - Errors a snapshot ignores. Always returned, empty only when a policy
          sets C(no_parent) and no policy sets a value in it.
      returned: always
      type: dict
      contains:
        ignore_directory_errors:
          description:
            - Whether errors reading directories are ignored.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: bool
        ignore_file_errors:
          description:
            - Whether errors reading files are ignored.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: bool
        ignore_unknown_types:
          description:
            - Whether entries of unknown types are ignored.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: bool
    files:
      description:
        - Files a snapshot ignores. Always returned, empty only when a policy
          sets C(no_parent) and no policy sets a value in it.
      returned: always
      type: dict
      contains:
        ignore:
          description:
            - Ignore rules, in C(.gitignore) syntax.
          returned: when set in the policy or a parent policy
          type: list
          elements: str
        ignore_cache_dirs:
          description:
            - Whether directories holding a C(CACHEDIR.TAG) file are ignored.
          returned: when set in the policy or a parent policy
          type: bool
        ignore_dot_files:
          description:
            - Names of files in each directory holding further ignore rules.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: list
          elements: str
        max_file_size:
          description:
            - Size in bytes above which files are ignored.
          returned: when set in the policy or a parent policy
          type: int
        no_parent_dot_files:
          description:
            - Whether C(ignore_dot_files) of parent policies is ignored.
          returned: when set in the policy or a parent policy
          type: bool
        no_parent_ignore:
          description:
            - Whether C(ignore) of parent policies is ignored.
          returned: when set in the policy or a parent policy
          type: bool
        one_file_system:
          description:
            - Whether a snapshot stays on the file system of its root.
          returned: when set in the policy or a parent policy
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
            - Log detail for directories. Always returned, empty only when a
              policy sets C(no_parent) and no policy sets a value in it.
          returned: always
          type: dict
          contains:
            ignored:
              description:
                - Log detail for ignored directories.
              returned: >-
                when set in the policy or a parent policy, or by kopia's
                defaults unless a policy sets C(no_parent)
              type: int
            snapshotted:
              description:
                - Log detail for snapshotted directories.
              returned: >-
                when set in the policy or a parent policy, or by kopia's
                defaults unless a policy sets C(no_parent)
              type: int
        entries:
          description:
            - Log detail for entries. Always returned, empty only when a policy
              sets C(no_parent) and no policy sets a value in it.
          returned: always
          type: dict
          contains:
            cache_hit:
              description:
                - Log detail for entries found in the cache.
              returned: >-
                when set in the policy or a parent policy, or by kopia's
                defaults unless a policy sets C(no_parent)
              type: int
            cache_miss:
              description:
                - Log detail for entries not found in the cache.
              returned: >-
                when set in the policy or a parent policy, or by kopia's
                defaults unless a policy sets C(no_parent)
              type: int
            ignored:
              description:
                - Log detail for ignored entries.
              returned: >-
                when set in the policy or a parent policy, or by kopia's
                defaults unless a policy sets C(no_parent)
              type: int
            snapshotted:
              description:
                - Log detail for snapshotted entries.
              returned: >-
                when set in the policy or a parent policy, or by kopia's
                defaults unless a policy sets C(no_parent)
              type: int
    metadata_compression:
      description:
        - Compression of directory metadata. Always returned, empty only when a
          policy sets C(no_parent) and no policy sets a value in it.
      returned: always
      type: dict
      contains:
        compressor_name:
          description:
            - Compressor kopia uses for metadata.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: str
    os_snapshots:
      description:
        - Operating system snapshots taken before a snapshot.
      returned: always
      type: dict
      contains:
        volume_shadow_copy:
          description:
            - Windows Volume Shadow Copy. Always returned, empty only when a
              policy sets C(no_parent) and no policy sets a value in it.
          returned: always
          type: dict
          contains:
            enable:
              description:
                - Whether a snapshot is taken, C(0) never, C(1) always, failing
                  without one, or C(2) when available.
              returned: >-
                when set in the policy or a parent policy, or by kopia's
                defaults unless a policy sets C(no_parent)
              type: int
    retention:
      description:
        - Snapshots kept. Always returned, empty only when a policy sets
          C(no_parent) and no policy sets a value in it.
      returned: always
      type: dict
      contains:
        ignore_identical_snapshots:
          description:
            - Whether a snapshot identical to the previous one is not saved.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: bool
        keep_annual:
          description:
            - Number of annual snapshots kept.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: int
        keep_daily:
          description:
            - Number of daily snapshots kept.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: int
        keep_hourly:
          description:
            - Number of hourly snapshots kept.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: int
        keep_latest:
          description:
            - Number of latest snapshots kept.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: int
        keep_monthly:
          description:
            - Number of monthly snapshots kept.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: int
        keep_weekly:
          description:
            - Number of weekly snapshots kept.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: int
    scheduling:
      description:
        - When kopia takes snapshots. Always returned, empty only when a policy
          sets C(no_parent) and no policy sets a value in it.
      returned: always
      type: dict
      contains:
        cron:
          description:
            - Cron expressions.
          returned: when set in the policy or a parent policy
          type: list
          elements: str
        interval_seconds:
          description:
            - Seconds between snapshots.
          returned: when set in the policy or a parent policy
          type: int
        manual:
          description:
            - Whether snapshots are only taken manually.
          returned: when set in the policy or a parent policy
          type: bool
        no_parent_time_of_day:
          description:
            - Whether C(time_of_day) of parent policies is ignored.
          returned: when set in the policy or a parent policy
          type: bool
        run_missed:
          description:
            - Whether a missed snapshot is taken at once.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: bool
        time_of_day:
          description:
            - Times of day snapshots are taken.
          returned: when set in the policy or a parent policy
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
          returned: when set in the policy or a parent policy
          type: str
    upload:
      description:
        - Upload parallelism. Always returned, empty only when a policy sets
          C(no_parent) and no policy sets a value in it.
      returned: always
      type: dict
      contains:
        max_parallel_file_reads:
          description:
            - Number of files read at the same time.
          returned: when set in the policy or a parent policy
          type: int
        max_parallel_snapshots:
          description:
            - Number of snapshots taken at the same time.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: int
        parallel_upload_above_size:
          description:
            - Size in bytes above which a file is uploaded in parallel parts.
          returned: >-
            when set in the policy or a parent policy, or by kopia's defaults
            unless a policy sets C(no_parent)
          type: int
  sample:
    actions: {}
    compression:
      compressor_name: none
    error_handling:
      ignore_directory_errors: false
      ignore_file_errors: false
      ignore_unknown_types: true
    files:
      ignore_dot_files:
        - .kopiaignore
    logging:
      directories:
        ignored: 5
        snapshotted: 5
      entries:
        cache_hit: 0
        cache_miss: 0
        ignored: 5
        snapshotted: 0
    metadata_compression:
      compressor_name: zstd-fastest
    os_snapshots:
      volume_shadow_copy:
        enable: 0
    retention:
      ignore_identical_snapshots: false
      keep_annual: 3
      keep_daily: 7
      keep_hourly: 48
      keep_latest: 2
      keep_monthly: 24
      keep_weekly: 4
    scheduling:
      run_missed: true
    splitter: {}
    upload:
      max_parallel_snapshots: 1
      parallel_upload_above_size: 2147483648
policies:
  description:
    - Policies defined in the repository from C(kopia policy list), as kopia
      reports them, each with its C(id), its C(target) and the sections of the
      policy, including the empty ones kopia always writes.
    - Empty when the module fails, and when kopia is unavailable or no
      repository is connected in check mode.
      Not returned when Ansible rejects the arguments, such as a missing
      required option, a value of the wrong type or an invalid choice, or fails
      to log them, such as for a lone surrogate code point in an option that is
      not secret, or when the kopia command is not found or cannot be started,
      such as for a NUL character in a value passed to it.
  returned: when O(target) is not set
  type: list
  elements: dict
  contains:
    id:
      description:
        - Manifest ID of the policy, 32 lowercase hexadecimal digits.
      returned: always
      type: str
    target:
      description:
        - Target of the policy.
      returned: always
      type: dict
      contains:
        host:
          description:
            - Host name of the target, empty for the global policy.
          returned: always
          type: str
        path:
          description:
            - Path of the target, empty for the global policy and for a
              C(user@host) or C(@host) target.
          returned: always
          type: str
        user_name:
          description:
            - User name of the target, empty for the global policy and for a
              C(@host) target.
          returned: always
          type: str
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
    - id: 5051ad95ebe43a87733f69615eb4ee9c
      target:
        host: ''
        path: ''
        user_name: ''
      actions: {}
      compression: {}
      error_handling: {}
      files: {}
      logging:
        directories: {}
        entries: {}
      metadata_compression: {}
      os_snapshots:
        volume_shadow_copy: {}
      retention:
        keep_latest: 10
      scheduling: {}
      splitter: {}
      upload: {}
policy:
  description:
    - Defined policy for O(target) reported by C(kopia policy export), as
      kopia reports it, including the empty sections it always writes.
    - Empty when no policy is defined for the target.
    - Empty when the module fails, and when kopia is unavailable or no
      repository is connected in check mode.
      Not returned when Ansible rejects the arguments, such as a missing
      required option, a value of the wrong type or an invalid choice, or fails
      to log them, such as for a lone surrogate code point in an option that is
      not secret, or when the kopia command is not found or cannot be started,
      such as for a NUL character in a value passed to it.
  returned: when O(target) is set
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
    compression: {}
    error_handling: {}
    files: {}
    logging:
      directories: {}
      entries: {}
    metadata_compression: {}
    os_snapshots:
      volume_shadow_copy: {}
    retention:
      keep_latest: 2
    scheduling: {}
    splitter: {}
    upload: {}
"""

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict

from ansible_collections.linuxhq.linux.plugins.module_utils.kopia import (
    check_connection,
    check_policy_target,
    check_utf8,
    kopia_available,
    kopia_command,
    policy_export,
    repository_connected,
    text_label,
)


def info(module):
    # whether a policy is defined is unknown on failure, so it is left out
    failed_result = {"effective_policy": {}, "policy": {}}

    check_connection(module, failed_result=failed_result)
    # run_command cannot pass U+D800 to U+DC7F to kopia
    check_utf8(module, [("target", module.params["target"])], errors="surrogateescape", failed_result=failed_result)
    check_policy_target(module, module.params["target"], failed_result=failed_result)

    # an earlier task in check mode, such as kopia_repository, may only have predicted the connection
    if module.check_mode and not (
        kopia_available(module) and repository_connected(module, failed_result=failed_result)
    ):
        module.exit_json(changed=False, **failed_result)

    target = module.params["target"]
    defined = policy_export(module, target, failed_result=failed_result)

    rc, stdout, stderr = kopia_command(module, ["policy", "show", "--json", "--", target])

    if rc != 0:
        module.fail_json(msg=f"unable to show kopia policy {text_label(target)}: {stderr.strip()}", **failed_result)

    module.exit_json(
        changed=False,
        defined=defined is not None,
        effective_policy=camel_dict_to_snake_dict(json.loads(stdout)),
        policy=camel_dict_to_snake_dict(defined or {}),
    )


def list_policies(module):
    check_connection(module, failed_result={"policies": []})

    if module.check_mode and not (
        kopia_available(module) and repository_connected(module, failed_result={"policies": []})
    ):
        module.exit_json(changed=False, policies=[])

    rc, stdout, stderr = kopia_command(module, ["policy", "list", "--json"])

    if rc != 0:
        module.fail_json(msg=f"unable to list kopia policies: {stderr.strip()}", policies=[])

    module.exit_json(
        changed=False,
        policies=[camel_dict_to_snake_dict(policy) for policy in json.loads(stdout)],
    )


def main():
    argument_spec = {
        "config_file": {"type": "path"},
        "target": {"type": "str"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    if module.params["target"] is not None:
        info(module)

    list_policies(module)


if __name__ == "__main__":
    main()
