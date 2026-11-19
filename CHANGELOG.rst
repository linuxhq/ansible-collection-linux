===========================
linuxhq.linux Release Notes
===========================

.. contents:: Topics

v2.5.0
======

Minor Changes
-------------

- kopia role - pass ``kopia_repository.storage`` to kopia_repository as given, and skip the repository task when ``kopia_repository`` has no ``storage``, instead of failing with a missing required argument. Leave out ``validate_provider`` when ``kopia_repository.validate_provider`` is not set, so the module's default applies, instead of forcing ``false``.
- kopia_repository - fail when the host is already connected to a different repository, by storage type or identifying storage option, instead of reporting no change. Disconnect first to switch repositories.
- rclone role - default ``rclone_no_log`` to ``true``. In diff mode, the task managing the configuration file showed the previous decrypted configuration, whose secrets Ansible does not mask when they are no longer in the new configuration. Set ``rclone_no_log`` to ``false`` to show the task's output and diff.
- rclone_deobscure - leave a value too short to hold the initialization vector to pycryptodome, which refuses it, so the failure now carries pycryptodome's message about the counter length instead of the filter's own.
- systemd_hostname - accept an empty ``chassis`` to remove it from ``/etc/machine-info``.

Breaking Changes / Porting Guide
--------------------------------

- kopia modules - pass every string argument to kopia exactly as given, without expanding ``~`` or environment variables, so a policy ``target``, snapshot tags and description, and repository ``options`` and ``secrets`` reach kopia literally and ``kopia_policy`` exports, imports and deletes the same target. Expand values in the playbook instead. Options of type ``path``, that is ``config_file`` and the ``path`` of ``kopia_snapshot`` and ``kopia_snapshot_info``, are still expanded by Ansible.
- kopia role - declare only EL 9 and 10 as supported platforms.
- kopia_maintenance_info role - publish ``_kopia_maintenance_info_maintenance``, named after the module's ``maintenance`` return value, in place of ``_kopia_maintenance_info_dict``.
- kopia_policy_info role - name the published facts after the module's return values. Publish ``_kopia_policy_info_defined``, ``_kopia_policy_info_policy`` and ``_kopia_policy_info_effective_policy`` with ``kopia_policy_info_target`` set, in place of ``_kopia_policy_info_dict``, which held the effective policy, and ``_kopia_policy_info_policies`` in place of ``_kopia_policy_info_list``. ``_kopia_policy_info_dict`` and ``_kopia_policy_info_list`` are no longer published. ``_kopia_policy_info_defined`` is null when the module does not report ``defined``, as without ``kopia_policy_info_target`` or when kopia is unavailable in check mode.
- kopia_repository - compare the identifying storage ``options`` with the connected repository literally, without expanding environment variables. A leading ``~`` in a ``filesystem`` ``path`` is still resolved to the home directory, as kopia does.
- kopia_repository_info role - publish ``_kopia_repository_info_connected`` and ``_kopia_repository_info_repository``, named after the module's ``connected`` and ``repository`` return values, in place of ``_kopia_repository_info_dict``. ``_kopia_repository_info_connected`` is null when the module does not report ``connected``, as when kopia is unavailable in check mode.
- kopia_snapshot_info role - publish ``_kopia_snapshot_info_snapshots``, named after the module's ``snapshots`` return value, in place of ``_kopia_snapshot_info_list``.
- linuxhq.linux - require ansible-core 2.19 or later. On ansible-core 2.18, a role fact set to ``null``, such as ``_kopia_policy_info_defined`` or ``_kopia_repository_info_connected``, was an empty string instead.
- rclone role - declare only EL 9 and 10 as supported platforms.
- systemd_hostname, systemd_hostname_info, systemd_locale, systemd_locale_info, systemd_timedate and systemd_timedate_info roles - declare only EL 9 and 10 and Debian 12 (bookworm) and 13 (trixie) as supported platforms.
- systemd_locale - requires systemd 239 or later, the first version whose systemd-localed merges a partial locale request instead of clearing the variables left out.
- systemd_timedate - ``time`` is now parsed by ``systemd-analyze timestamp`` on the managed node, so exactly what ``timedatectl set-time`` accepts on that host is accepted. ``systemd-analyze`` is now required when ``time`` is set, and the module fails before writing any setting when it is not installed. Spellings the module accepted but systemd refuses now fail before any setting is written, such as ``now UTC``, ``UTC`` without a space before it (``14:30UTC``), a comma after the weekday (``Sun, 2026-07-26 14:30``), ``TODAY`` or another case of ``today``, ``yesterday`` and ``tomorrow``, surrounding whitespace, ``12.34.56``, and on systemd 257 a lowercase ``utc`` suffix. ``systemd-analyze timestamp`` exists from systemd 243, so on systemd 239 to 242 setting ``time`` fails with ``unable to parse the time specification`` before any setting is written.

Security Fixes
--------------

- kopia role - fetch the kopia RPM repository over HTTPS instead of HTTP.
- rclone_config_encryption - create a new configuration file with mode ``0600`` from the start, instead of leaving it readable by other users between the move into place and setting its mode.
- rclone_config_encryption - mark ``content`` as ``no_log`` so the configuration body is kept out of logs.

Bugfixes
--------

- kopia modules - document that ``config_file`` and the ``path`` options of ``kopia_snapshot`` and ``kopia_snapshot_info`` are expanded by Ansible.
- kopia role - with ``kopia_snapshot`` enabled, snapshot only the ``kopia_policies`` entries whose ``target`` is a local absolute path and whose ``state`` is ``present``. A ``(global)`` or ``user@host`` target and an entry with ``state=absent`` were snapshotted too, and ``(global)`` made the role fail.
- kopia_maintenance - compare ``owner=me`` with the stored owner as the client user and host of the connection, ``user@hostname``, which kopia stores for ``me``, also in check mode. The task reported a change on every run.
- kopia_maintenance - document that ``0`` for one ``max_retained_log_*`` option means no limit on it, and that all three at ``0`` means kopia's default log retention applies during maintenance.
- kopia_maintenance - document that ``extend_object_locks`` requires kopia 0.14.0 or later.
- kopia_maintenance - fail before running kopia, also in check mode, when ``list_parallelism`` or ``max_retained_log_count`` is outside -9007199254740992 to 9007199254740992. kopia parses these flags as a floating-point number before storing an integer, so it stored a rounded or wrapped value and every run reported a change.
- kopia_maintenance - fail before running kopia, also in check mode, when ``max_retained_log_size_mb`` is below -8796093022208 or exceeds 8796093022207, the sizes in megabytes kopia stores in bytes without overflowing. Such a value was stored wrapped around, such as 1 megabyte for 17592186044417, so log cleanup deleted almost every log and the task reported a change on every run.
- kopia_maintenance - follow kopia when every stored log retention setting is zero, where kopia starts from its default log retention, so the result and check mode match the settings kopia stores. Only the log retention options that differ are sent, the non-zero ones first and, when one command would reset them, in a second ``kopia maintenance set``, so every one set is stored as requested in one run.
- kopia_maintenance - reject ``-1`` for ``list_parallelism``, ``max_retained_log_count`` and ``max_retained_log_size_mb`` before running kopia, since kopia reads it as not given and the setting never converges.
- kopia_maintenance - reject an empty ``owner`` before querying kopia, which ignores an empty ``--owner``, so later runs failed with no changes specified.
- kopia_maintenance, kopia_maintenance_info - document that kopia reports ``maintenance.extend_object_locks`` from kopia 0.14.0 and ``maintenance.list_parallelism`` from kopia 0.18.0.
- kopia_maintenance, kopia_maintenance_info - replace the ``maintenance`` sample, which showed only some of the snapshot garbage collection statistics, with output captured from kopia 0.23.1, with host-specific values replaced.
- kopia_maintenance, kopia_maintenance_info, kopia_policy, kopia_policy_info, kopia_repository, kopia_repository_info, kopia_snapshot, kopia_snapshot_info, systemd_hostname, systemd_hostname_info, systemd_locale, systemd_locale_info, systemd_timedate, systemd_timedate_info - document the fields of nested return values with ``contains``, noting the fields kopia passes through unchanged.
- kopia_maintenance, kopia_maintenance_info, kopia_repository, kopia_repository_info, kopia_snapshot_info - document that they require kopia 0.12.0 or later. Before 0.12.0, kopia ignores ``KOPIA_REPO_UPGRADE_NO_BLOCK``, so the commands these modules run to read the repository, such as ``kopia repository status``, wait without limit while another client upgrades the repository format, instead of failing. ``kopia repository connect`` still waits from 0.12.0, as kopia_repository documents. Before 0.11.0, ``kopia snapshot list --json`` also leaves out the ``stats`` and ``retentionReason`` of each snapshot, before 0.10.7, ``kopia repository status`` has no ``--json``, and before 0.9.0, ``kopia maintenance info --json`` prints only the schedule.
- kopia_maintenance, kopia_policy - document that the returned ``maintenance`` and ``policy`` are the predicted settings in check mode when a change would be made, and empty when kopia is unavailable in check mode.
- kopia_policy - compare an empty action, such as ``actions.before_snapshot_root`` set to ``{}``, as kopia stores it. kopia stores and exports such an action, which blocks the action the target would otherwise inherit, but the module treated it as left out, so a policy with an empty action stored outside the module was reported as unchanged and never converged, and an empty action in ``policy`` was not sent to kopia.
- kopia_policy - compare and send a ``null`` list item as kopia stores it, an empty string in a list of strings such as ``files.ignore``, ``scheduling.cron`` or the ``args`` of an action, and ``0`` for a ``null`` ``scheduling.time_of_day`` entry or for its ``null`` ``hour`` or ``min``. Such a policy was reported as changed on every run, and check mode predicted ``null`` where kopia stores the empty value.
- kopia_policy - document that kopia refuses a ``policy`` key that matches none of its fields when it imports the policy, before it changes it, and that check mode does not predict that refusal. In check mode, such a key that is not valid UTF-8 is returned escaped.
- kopia_policy - document that of two ``policy`` keys that convert to the same key, such as ``keep_latest`` and ``keepLatest``, only the last one given is used.
- kopia_policy - document that policy manifest IDs are not accepted as ``target``.
- kopia_policy - fail before running kopia, also in check mode, when a ``policy`` key matches one of kopia's policy fields only ignoring case, such as ``keeplatest``, ``Retention`` or ``KEEP_LATEST``, naming the field. kopia matched such a key to its field ignoring case and stored the policy, but reported the field in camelCase, so the task reported a change on every run. Write keys in snake_case or in kopia's camelCase. Keys are matched as Go folds them, so the Kelvin sign matches ``k`` and the long s matches ``s``, but the dotless i matches no field.
- kopia_policy - fill a missing ``hour`` or ``min`` of a ``scheduling.time_of_day`` entry with ``0``, as kopia stores it, so such a policy no longer reports a change on every run.
- kopia_policy - treat ``false``, ``0``, empty strings and empty lists for fields kopia does not store, such as ``scheduling.manual`` or ``files.max_file_size``, as left out, so such a policy no longer reports a change on every run.
- kopia_policy - treat ``policy`` set to ``null`` with ``state=present``, as the kopia role passes for a ``kopia_policies`` item written ``policy:``, as the empty policy ``{}``, which replaces the defined policy. The module failed with a traceback, also in check mode.
- kopia_policy, kopia_maintenance - compare Booleans and numbers strictly, so ``true`` no longer matches ``1``.
- kopia_policy, kopia_maintenance, kopia_repository - fail before running kopia, also in check mode, when a ``policy`` value, the ``target`` with ``state=present``, a maintenance ``owner``, or a storage option or secret value is not valid UTF-8, such as text with a lone surrogate code point. kopia recorded such text with U+FFFD in its place, so a policy was imported again on every run, the maintenance owner was set on every run, and the next run failed against the module's own repository connection. Some such values made the module fail with a traceback. A failure names the option or key, never a value. For kopia_repository, kopia saves the storage options and secrets in its configuration and connects again from that copy, so a value such as an sftp ``keyfile`` with such text could create a repository that never connected. Only the file paths kopia reads and never saves pass U+DC80 to U+DCFF to kopia as the bytes Ansible uses them for, and are rejected only for another lone surrogate code point, which cannot be passed to kopia. These are ``file`` and ``token_file`` with ``storage=from-config``, ``root_ca_pem_path`` with ``storage=s3`` and ``embed_rclone_config`` with ``storage=rclone``, whose contents kopia saves instead, and, with ``embed_credentials`` set to the Boolean ``true``, ``credentials_file`` with ``storage=gcs`` or ``storage=gdrive`` and, with ``storage=sftp`` when ``external`` is not given or is ``false``, ``keyfile`` when ``key_data`` is not given or empty and ``known_hosts`` when ``known_hosts_data`` is not given or empty, which kopia replaces with the file contents.
- kopia_policy, kopia_policy_info - document that kopia rejects a ``target`` with no ``:`` whose only ``@`` is its last character, such as ``/srv/backup@``, as an invalid host name before it changes anything, and that such a directory is written as ``user@host:/path``. The documentation said that kopia reads such a target as ``user@host``.
- kopia_policy, kopia_policy_info - document that kopia stores the user, host and path of a ``user@host:/path`` target as given, so they must match the client user and host and an absolute, clean path, that kopia reads a target in which an ``@`` comes before any ``:`` as ``user@host`` or ``user@host:path``, except one that starts with ``@`` and contains ``:``, such as ``@host:/path``, which it reads as a relative directory path, and that no target can name a directory whose path is such a path when the client user contains ``@`` or ``:``, or the host contains ``:``.
- kopia_policy, kopia_policy_info - fail before running kopia, also in check mode, when ``target`` is 32 lowercase hexadecimal digits. ``kopia policy export``, ``show`` and ``delete`` read such a target as a manifest ID, such as that of another policy or of a snapshot, so ``state=absent`` with a snapshot ID deleted the policy of the snapshot's source, ``state=present`` imported a policy for a relative path every run, and ``kopia_policy_info`` returned the policy of another target.
- kopia_policy, kopia_policy_info - name the target in failure messages.
- kopia_policy, kopia_policy_info - pass ``target`` to ``kopia policy export``, ``show`` and ``delete`` after ``--``. These commands read a target starting with ``-`` as a command-line flag, so ``state=absent`` with ``target=--global`` deleted the global policy, and ``state=present`` imported a policy for a relative path while comparing against the global policy, reporting a change on every run. Such a target is now read as ``kopia policy import`` reads it, as a relative path, or as ``user@host`` or ``user@host:/path`` for a client user starting with ``-``.
- kopia_policy, kopia_policy_info - return ``policy`` and ``policies`` as kopia reports them, including the empty sections kopia always writes, such as ``files`` or ``logging.directories``, instead of removing them. In check mode, kopia_policy predicts those sections too.
- kopia_policy, kopia_policy_info, kopia_maintenance - document that ``kopia_policy`` and ``kopia_policy_info`` require kopia 0.18.0 or later, and so does ``list_parallelism`` of ``kopia_maintenance``.
- kopia_policy, kopia_policy_info, kopia_maintenance, kopia_maintenance_info, kopia_snapshot, kopia_snapshot_info - in check mode with kopia installed but no repository connected, such as before kopia_repository connects in the same play, report the result they report without kopia, a change for kopia_policy with ``state=present``, kopia_maintenance and kopia_snapshot, no change and empty results otherwise, instead of failing with ``repository is not connected``.
- kopia_policy, kopia_policy_info, kopia_snapshot - document that an empty ``target`` or ``path``, which Ansible can pass for ``null``, names the working directory of the module, such as the home directory of the remote user.
- kopia_policy_info - document that ``effective_policy`` also holds kopia's built-in policy defaults for the values no policy sets, unless a policy sets ``no_parent``, but not the values kopia only falls back to when it takes a snapshot, such as ``upload.max_parallel_file_reads``.
- kopia_policy_info - document that ``effective_policy`` combines ``compression.never_compress``, ``compression.only_compress`` and ``scheduling.time_of_day`` from the policy and its parent policies.
- kopia_policy_info - document that ``no_parent`` is never returned in ``effective_policy``, that its folder actions come only from the policy of ``target`` itself, and replace its sample with real ``kopia policy show`` output.
- kopia_policy_info - document that each action in ``effective_policy`` is taken whole from the most specific policy that sets it.
- kopia_policy_info - document that kopia makes a bare directory path ``target`` absolute and cleans it, as kopia_policy does.
- kopia_policy_info - document which fields of ``effective_policy`` keep a ``false`` or ``0`` value over a parent policy.
- kopia_policy_info - return an empty ``policies`` in check mode when kopia is unavailable, and always return ``policy`` when ``target`` is set.
- kopia_repository - also compare ``port`` and ``storage_domain``, and for ``storage=sftp`` ``username``, with the connected repository, so a host connected to the same path on another sftp server port or account, or to an azure container in another storage domain, fails instead of reporting no change. A ``storage_domain`` that is not stored is compared as ``blob.core.windows.net``, the domain kopia uses then, and ``port`` as the number kopia reads from it, a decimal or hexadecimal floating-point number read as Go's ``strconv.ParseFloat`` does and truncated, so ``"+22"`` and ``"0x16p0"`` match a stored ``22``, and ``" 22"`` does not.
- kopia_repository - compare a number given for an identifying storage option, such as ``bucket``, with the connected repository as the text passed to kopia, so a host connected to a different repository fails instead of reporting no change.
- kopia_repository - compare the ``path`` of ``filesystem`` storage as a normalized path, so a connection made with ``/srv/kopia/`` or ``//srv/kopia`` matches ``/srv/kopia`` instead of failing as a different repository.
- kopia_repository - compare the options that identify the repository with the connected repository also when they are given in ``secrets``, using the value sent to kopia, where ``secrets`` takes precedence over ``options``. A host connected elsewhere failed to be detected, and an option overridden by a secret made the next run fail against the module's own connection. A mismatch in a secret names only the option, not its value, and failure messages no longer show an option that a secret overrides.
- kopia_repository - create a ``filesystem`` repository whose ``path`` does not exist yet, as ``kopia repository create`` does, instead of failing because connecting cannot access the missing path.
- kopia_repository - document that ``kopia repository connect`` waits for as long as another client holds the repository for a format upgrade, as it has no option to fail instead, and that a connection to a kopia server is not supported.
- kopia_repository - document that flags only ``kopia repository create`` accepts, such as ``encryption``, make the connection fail when the storage already holds a repository, and that ``create_only`` leaves a repository it creates unconnected.
- kopia_repository - document that kopia refuses a Boolean flag given a value, such as ``embed_credentials`` set to the string ``"true"``, before it changes anything.
- kopia_repository - document that numbers in ``options`` and ``secrets`` are passed to kopia as Python formats them, so values that YAML reads as numbers, such as an unquoted ``0755``, ``12:30`` or ``1.10``, should be quoted.
- kopia_repository - document that the ``root_ca_pem_path`` option of ``s3`` storage requires kopia 0.13.0 or later, and the ``token_file`` option of ``from-config`` storage kopia 0.14.0 or later.
- kopia_repository - document that with ``storage=from-config`` an existing connection is not compared and is left untouched.
- kopia_repository - document that with ``storage=sftp`` and ``external`` set, ``ssh`` asks for a password, a passphrase or an unknown host key on the terminal, so the module can still wait for an answer.
- kopia_repository - fail before running kopia when an option that identifies the repository, such as ``bucket`` or ``path``, is given a list, which was passed as one flag per element and not compared with the connected repository. kopia rejects a Boolean for these options, so quote a value such as ``no`` that YAML reads as a Boolean.
- kopia_repository - fail before running kopia, also in check mode, for an empty ``password`` when the host is not connected and the storage is ``sftp``, or ``filesystem`` with a ``path`` that does not exist. kopia reads an empty ``KOPIA_PASSWORD`` as no password, and that storage created the missing path before kopia waited for one. Elsewhere kopia fails to read the password before it changes anything.
- kopia_repository - never try to create a repository for ``from-config`` storage.
- kopia_repository - read the connection status when ``kopia repository connect`` fails, and report ``changed`` when the host is connected, such as when kopia saved the connection and then failed to persist the password, or when the status cannot be read, as kopia may have saved the connection. The module reports no change only when kopia reports that the repository is not connected. It reported no change for every failed connect.
- kopia_repository - read the connection status with ``password``, so a connection made with ``persist_credentials`` set to ``false`` is recognized.
- kopia_repository - report ``changed`` when ``kopia repository create`` fails after creating the missing ``path`` directory of ``filesystem`` storage, or any missing parent directory, such as when writing the ``kopia.blobcfg`` blob fails for lack of space, and say that kopia created a directory. The path is checked as kopia creates it, with only a leading ``~`` resolved, so a ``..`` after a missing directory or a symbolic link is resolved as the kernel resolves it.
- kopia_repository - report ``changed`` when ``kopia repository create`` fails after initializing the storage, when connecting to the new repository or setting its default global policy and maintenance owner fails, and say that this setup is not retried by a later run, which connects to the repository, or finds it connected, without it.
- kopia_repository - report ``changed`` when ``kopia repository create`` fails to write the format blob after writing the ``kopia.blobcfg`` blob, stored as the file ``kopia.blobcfg.f`` with ``filesystem``, ``rclone``, ``sftp`` or ``webdav`` storage, and say that this blob must be removed from the storage before the repository can be created. The module reported no change, and later runs failed with ``found existing data in storage location``, which now also says that the storage holds data but no kopia repository, such as that blob.
- kopia_repository - report a change when ``kopia repository connect`` fails after it wrote the ``.shards`` file of ``filesystem`` storage that holds data but no repository, such as a stray file ending in ``.f``, and correct the documentation, which said the module never connects to storage without a repository.
- kopia_repository - report a change when ``kopia repository create`` fails after it wrote the ``.shards`` file in an existing ``path`` of ``filesystem`` storage, and document that with ``sftp``, ``webdav`` or ``rclone`` storage, a failed create may leave the remote ``path`` or the ``.shards`` file, which the module cannot inspect.
- kopia_repository - report distinct failures for connecting, creating and validating the provider, naming the storage, and say when the repository was created but validating the provider failed.
- kopia_repository - run ``kopia repository create`` first and connect with ``kopia repository connect`` only when kopia reports that the storage already holds data. Connecting first to storage without a repository could write to it, such as the ``.shards`` file of ``filesystem`` storage in an existing empty directory, which then held legacy sharding parameters different from those of a repository kopia creates.
- kopia_repository - say that the host is connected to a kopia repository server, which the module does not manage, instead of reporting an empty storage type, when the connection is to a kopia repository server.
- kopia_repository, kopia_policy, kopia_maintenance - report ``changed`` when kopia fails after the repository was connected or created, the policy imported or the maintenance settings set, such as when validating the provider or reading the result back fails.
- kopia_repository, kopia_policy, kopia_maintenance, kopia_snapshot - return an empty ``repository``, ``policy``, ``maintenance`` or ``snapshot`` when the module fails, also before any change, such as when reading the current state fails, the host is connected to a different repository or an option is refused before kopia runs, instead of leaving the key out, and document it. The key is still left out when Ansible rejects the arguments, such as a missing required option or an invalid choice, or when the kopia command is not found.
- kopia_repository, kopia_repository_info - document that ``repository.volume.capacity`` is returned only when the volume reports a non-zero size, as kopia omits it otherwise.
- kopia_repository, kopia_repository_info - document that for a repository the host reaches through a kopia repository server, kopia reports an empty ``repository.storage.type`` and ``repository.unique_id_hex``, a null ``repository.storage.config``, and no ``repository.content_format.hash``, ``repository.content_format.encryption``, ``repository.content_format.version`` or ``repository.object_format.splitter``.
- kopia_repository, kopia_repository_info - replace the ``repository`` sample, which left out fields kopia always reports, with output captured from kopia 0.23.1, with host-specific values replaced.
- kopia_repository, kopia_repository_info, kopia_maintenance, kopia_maintenance_info, kopia_policy, kopia_policy_info, kopia_snapshot, kopia_snapshot_info - document that kopia looks up a bare ``config_file`` name in its configuration directory, not in the working directory, and that the result keys are not returned when Ansible rejects the arguments, such as a missing required option or an invalid choice, or fails to log them, such as for a lone surrogate code point in an option that is not secret, or when kopia cannot be started, such as for a NUL character in a value passed to it.
- kopia_repository, kopia_repository_info, kopia_maintenance, kopia_maintenance_info, kopia_policy, kopia_policy_info, kopia_snapshot, kopia_snapshot_info - fail before running kopia, also in check mode, when ``config_file`` or another value passed to kopia as an argument contains a lone surrogate code point from U+D800 to U+DC7F. Such a value made the module fail with a traceback. U+DC80 to U+DCFF, which Ansible uses for bytes that are not valid UTF-8, still reach kopia as those bytes, except in the ``path`` of kopia_snapshot and kopia_snapshot_info, which must be valid UTF-8, and failure messages show such characters, also in kopia's own messages, as escapes, so they stay valid UTF-8.
- kopia_repository, kopia_snapshot, kopia_snapshot_info - correct the documented return conditions and snapshot ordering.
- kopia_repository, kopia_snapshot, kopia_snapshot_info - document that kopia removes whitespace around a given password, so a password of only whitespace is used as an empty password, which ``kopia repository create`` accepts, without falling back to the persisted one, and that ``kopia_snapshot`` and ``kopia_snapshot_info`` read the persisted password for an empty one, as when it is not given.
- kopia_repository_info, kopia_maintenance, kopia_maintenance_info, kopia_policy, kopia_policy_info, kopia_snapshot, kopia_snapshot_info - give kopia ``/dev/null`` as its standard input, also when the module runs with its standard input closed. When the repository password was neither given nor persisted next to the configuration file, such as for a connection made with ``persist_credentials`` set to ``false``, kopia asked for it on the standard input it inherited, which is a terminal over SSH without pipelining, so the task waited forever, also in check mode. The module now fails saying that kopia needs the password, which is not given and not persisted next to the configuration file it names.
- kopia_repository_info, kopia_maintenance, kopia_maintenance_info, kopia_policy, kopia_policy_info, kopia_snapshot, kopia_snapshot_info - run kopia with ``KOPIA_REPO_UPGRADE_NO_BLOCK=true``, so kopia fails while another client upgrades the repository format instead of waiting for the upgrade to end, which made the task wait for as long as the upgrade lock was held. kopia 0.12.0 and later read this variable, and earlier versions ignore it. ``kopia repository connect`` ignores it, so kopia_repository still waits when it connects, which its documentation now says.
- kopia_repository_info, kopia_maintenance_info, kopia_policy_info, kopia_snapshot_info - return an empty ``repository``, ``maintenance``, ``policy`` and ``effective_policy``, ``policies`` or ``snapshots`` when the module fails, such as when kopia fails or an option is refused before kopia runs, instead of leaving the key out, and document that ``connected`` and ``defined`` are left out then.
- kopia_repository_info, kopia_policy_info - leave out ``connected`` and ``defined`` in check mode when kopia is unavailable, as when the module fails, since they are unknown. They were returned as ``false``.
- kopia_snapshot - document that a ``tags`` value is recorded as Python writes it, so a value that YAML reads as a number, a Boolean or null whose text differs, such as ``1.10``, ``12:30`` or ``true``, should be quoted to record it as written.
- kopia_snapshot - document that it requires kopia 0.14.0 or later. Before 0.14.0, ``kopia snapshot create --json`` exits successfully after printing the snapshot, without failing on the fatal errors found while snapshotting, so the module would report an incomplete snapshot as created.
- kopia_snapshot - document that kopia splits a ``tags`` key containing ``:`` into a different key and value.
- kopia_snapshot - list the snapshots of a path in which an ``@`` comes before any ``:``, such as ``/home/alice@example.com``, by its source ``user@host:/path``. kopia reads such a bare path as ``user@host`` or ``user@host:path``, or rejects one with no ``:`` whose only ``@`` is its last character, so the module returned an empty ``snapshot``, and when kopia printed the snapshot it saved, then reported errors, the module failed without a change, so a retry took another snapshot. Other paths, including one with a ``:`` before its first ``@`` such as ``/srv/a:b@c``, which kopia reads as a path, are listed without a user and host, so a client user such as ``alice@corp.example.com`` keeps working. When the client user contains ``@`` or ``:``, or the host contains ``:``, which kopia cannot read in ``user@host:/path``, the module fails before taking a snapshot of a path in which an ``@`` comes before any ``:``.
- kopia_snapshot - report a change and return the saved snapshot when kopia printed the snapshot it saved, then exited with an error, for example fatal errors found while snapshotting, such as a file it cannot read, or automatic maintenance failing afterwards. The module failed without a change or snapshot, so a retry took another snapshot. When kopia does not list the printed snapshot, for example because its final repository flush failed, the module still fails without a change, and when the snapshots cannot be listed, it reports a change, as the snapshot may have been saved, with an empty ``snapshot``.
- kopia_snapshot - report no change when kopia skips the snapshot because the policy sets ``retention.ignore_identical_snapshots`` and no files changed since the newest complete snapshot, and return that snapshot, never a newer incomplete one such as a checkpoint, or an empty ``snapshot`` when the path has no complete snapshot. The module reported a change and returned the previous snapshot as if it were new.
- kopia_snapshot - return the newest snapshot of ``path`` only, or an empty ``snapshot`` when it has none, when the snapshot kopia printed is not listed, such as when another client deleted it before the module listed it, or when kopia skipped an identical snapshot. ``kopia snapshot list`` also reports the snapshots of every parent directory, so the module returned the snapshot of a parent directory when the path had none.
- kopia_snapshot - return the snapshot the module created, identified by the ID kopia prints when it saves it. The module returned the newest snapshot listed for the path, which could be one created by a scheduled snapshot or another run in between.
- kopia_snapshot, kopia_snapshot_info - document that ``root_entry`` is a file entry, of type ``f`` with ``size`` and a ``summ`` of that one file, when ``path`` is a file, and that a checkpoint of a file has no ``summ``.
- kopia_snapshot, kopia_snapshot_info - document that ``source.path`` is the path of the snapshotted directory or file.
- kopia_snapshot, kopia_snapshot_info - document that kopia rejects a bare path with no ``:`` whose only ``@`` is its last character, such as ``/srv/backup@``, which the modules list by its source ``user@host:/path``. The documentation said that kopia reads it as ``user@host``.
- kopia_snapshot, kopia_snapshot_info - name the path in failure messages.
- kopia_snapshot, kopia_snapshot_info - pass ``path`` to kopia made absolute, so a relative path such as ``--all`` or ``(global)`` is no longer read as an option or as the global source.
- kopia_snapshot, kopia_snapshot_info - pass the source to ``kopia snapshot list`` after ``--``, so a path listed as ``user@host:/path`` for a client user starting with ``-`` is listed instead of being read as a flag, which made ``kopia_snapshot`` return an empty ``snapshot`` after taking it and ``kopia_snapshot_info`` fail.
- kopia_snapshot, kopia_snapshot_info - refuse a ``path`` that is not valid UTF-8, such as one with a lone surrogate code point, before kopia runs, also in check mode. Ansible cannot run a task with such a path. A lone surrogate from U+D800 to U+DC7F made the module fail with a traceback. U+DC80 to U+DCFF, which Ansible uses for bytes that are not valid UTF-8, were passed to kopia as those bytes. Without ``no_log``, the module fails while Ansible logs its arguments. With ``no_log``, kopia saved the snapshot, and the controller then rejected the module result, which echoes the path, so the task failed without reporting the change.
- kopia_snapshot, kopia_snapshot_info - return snapshot tag keys as kopia reports them instead of converting them to snake_case.
- kopia_snapshot, kopia_snapshot_info, kopia_maintenance, kopia_maintenance_info, kopia_repository, kopia_repository_info - correct the return samples to match kopia's output, with 32-digit snapshot IDs, 64-digit repository IDs, UTC timestamps with nanoseconds, the snapshot ``source`` and the maintenance ``schedule.runs``.
- kopia_snapshot_info - document that an empty ``path`` lists all sources.
- kopia_snapshot_info - document that snapshots of the parent directories of ``path`` are included, as ``kopia snapshot list`` reports them.
- kopia_snapshot_info - document the UTF-8 handling under ``path``, which the module checks, instead of ``config_file``.
- kopia_snapshot_info - list the snapshots of a ``path`` in which an ``@`` comes before any ``:`` by its source ``user@host:/path``, with the client user and host and the path made absolute and cleaned. kopia read such a bare path as ``user@host`` or ``user@host:path`` and returned no snapshots, or those of another source, or rejected it. Other paths, including one with a ``:`` before its first ``@``, are listed without a user and host. When the client user contains ``@`` or ``:``, or the host contains ``:``, the module fails for a path in which an ``@`` comes before any ``:``.
- rclone role - write a floating-point value in ``rclone_config``, such as ``0.5`` for ``pacer_min_sleep``, as given instead of truncating it to an integer.
- rclone_config_encryption - accept an empty or whitespace-only ``password``, which was rejected with ``no characters in password``. It encrypts and decrypts consistently, but rclone itself refuses such a password, so rclone cannot open a file encrypted with one.
- rclone_config_encryption - backslash escape lone surrogate code points, such as U+DC80 to U+DCFF, which stand for bytes that are not valid UTF-8, in the returned ``path`` and in failure messages, including the resolved target of a symbolic link, so the result is valid UTF-8, which ansible-core 2.19 and later require. Document that Ansible fails before the module runs for a ``path`` with a lone surrogate unless the task sets ``no_log``.
- rclone_config_encryption - check the password and that ``path`` exists when ``content`` is unset before checking for pycryptodome or pycryptodomex, so check mode without either library fails where a real run would.
- rclone_config_encryption - create a new configuration file with mode ``0600``, as rclone does, unless ``mode`` is set.
- rclone_config_encryption - document diff mode support, which returns the decrypted configuration in the diff.
- rclone_config_encryption - document that the after side of the diff shows the full new configuration when ``content`` contains U+DC80 to U+DCFF.
- rclone_config_encryption - document that the password is NFKC normalized with the Unicode tables of the managed node's Python, and that rclone cannot open a file encrypted with a password holding a run of more than 30 combining characters, which rclone normalizes differently.
- rclone_config_encryption - document that with ``state=absent`` and ``content`` an encrypted file is replaced without ``password``, which is then only used to read the current configuration.
- rclone_config_encryption - document under ``content`` that a file whose encrypted payload or encryption header is damaged is replaced.
- rclone_config_encryption - fail before any file is read or written when ``path`` contains a NUL character or a lone surrogate code point other than U+DC80 to U+DCFF, which cannot name a file. With ``content`` set, the module failed with a traceback; without it, it failed saying the configuration file does not exist. U+DC80 to U+DCFF, which Ansible uses for bytes that are not valid UTF-8, still stand for those bytes.
- rclone_config_encryption - fail before anything is read or written when ``path`` resolves to something other than a regular file. Reading a FIFO blocked the module, a device such as ``/dev/zero`` never ended, and with ``content`` as root a device such as ``/dev/null`` was replaced by the configuration file.
- rclone_config_encryption - fail before writing anything for an ``owner`` or ``group`` that cannot be looked up, including one with a NUL character or a lone surrogate code point, and for a ``mode`` that is neither octal nor symbolic or is beyond the range of a C int, such as ``040000000000``. Ansible applied them only after the configuration file was written, so the run changed the file and then failed, and check mode reported a change for a new file instead of failing. Document that an SELinux context or ``attributes`` value the system refuses, and an ``owner`` or ``group`` the module may not set, such as another user's when it does not run as root, still fail only after the file is written.
- rclone_config_encryption - fail before writing anything when ``state=absent`` would write plain text that begins with an rclone encryption header such as ``RCLONE_ENCRYPT_V0:``, because rclone would not read it as the plain text written. It reads it as encrypted, or refuses an unsupported or damaged header. The module wrote such text, after which later runs reported a change on every run or failed, except for a file encrypted more than once with the same password, from which each later run removed one more layer of encryption until the runs settled. A ``content`` beginning with such a header is refused in check mode too, even when neither pycryptodome nor pycryptodomex is available.
- rclone_config_encryption - fail before writing, also in check mode, for an ``owner`` or ``group`` ID outside ``0`` to ``4294967294``. A larger or negative ID made the module fail with a traceback after it wrote the file, and check mode reported a change, while ``-1`` and ``4294967295``, which ``chown`` reads as no change, were reported as changed on every run.
- rclone_config_encryption - fail in check mode without pycryptodome when ``path`` is not a regular file, such as a FIFO or a device, as a real run does, instead of reporting a change.
- rclone_config_encryption - follow a symbolic link at ``path`` through every link in its chain and write the final file, instead of replacing the link with a regular file. This matches rclone for a single link; for a chain of links, rclone replaces the second link with a regular file.
- rclone_config_encryption - honor ``unsafe_writes`` when writing the configuration file, including when no temporary file can be created in its directory, where the file is then written in place.
- rclone_config_encryption - include the path in every failure message.
- rclone_config_encryption - name the configuration file in the failure message when neither pycryptodome nor pycryptodomex is installed, and name pycryptodomex there as well, since either library is accepted.
- rclone_config_encryption - name the configuration file when the password is invalid.
- rclone_config_encryption - read the encrypted payload as rclone does, ignoring only carriage returns and line feeds and splitting lines on line feeds only, and treat padding after a complete base64 quantum, such as a stray ``=``, as a damaged payload. Python 3.11 and older accepted it, so the module reported no change for a file rclone cannot load. Padding before the end of the payload is treated as damaged as well, although rclone may accept it where it falls on one of its internal read boundaries.
- rclone_config_encryption - read the lines before the encryption header in pieces of 4096 bytes, as rclone does, so a comment longer than that before ``RCLONE_ENCRYPT_V0:`` no longer makes the module treat a file rclone reads as plain text as already encrypted.
- rclone_config_encryption - reject ``content`` containing a lone surrogate code point, such as U+D800 from a JSON extra variable, with a message naming the configuration file, instead of failing with a traceback.
- rclone_config_encryption - reject a ``password`` containing a lone surrogate code point, such as U+D800 from a JSON extra variable, with a message naming the configuration file. Such a password reported a change in check mode and failed with a traceback in a real run, and rclone refuses it as invalid UTF-8.
- rclone_config_encryption - replace a file whose first line other than blank and comment lines, trimmed of whitespace, starts with ``RCLONE_ENCRYPT_V`` but is not exactly ``RCLONE_ENCRYPT_V0:``, such as an ``RCLONE_ENCRYPT_V1:`` header or a damaged ``RCLONE_ENCRYPT_V0:`` line with the payload on it, when ``content`` is set, as a file encrypted with another password is replaced. Such a file failed even with ``content``. Without ``content`` it still fails. Document that, like rclone, the module trims the Unicode space characters rclone trims and reads lines in pieces of up to 4096 bytes, so a longer line counts as several. The failure message now calls it an unsupported or damaged configuration encryption header instead of asking to update rclone.
- rclone_config_encryption - replace bytes that are not valid UTF-8 in the diff, as when reading the configuration, instead of returning text that cannot be encoded.
- rclone_config_encryption - report an error other than a missing file, such as a permission error on a parent directory, when checking ``path``. Without ``content`` the module failed saying the configuration file does not exist, and in check mode with ``content`` it reported that the file would be created.
- rclone_config_encryption - say in the check mode details that the configuration is not inspected when neither pycryptodome nor pycryptodomex is available.
- rclone_config_encryption - say in the failure for a file that ``state=absent`` cannot decrypt without ``content`` that the encrypted payload may be damaged, besides the password being wrong or missing.
- rclone_config_encryption - treat a damaged encrypted payload as a file that cannot be opened, so ``content`` replaces it and a run without ``content`` fails clearly instead of with a traceback.
- rclone_config_encryption - treat only the whitespace Go trims, as rclone does, as whitespace when reading the encryption header.
- rclone_config_encryption, rclone_obscure, rclone_deobscure - document the minimum pycryptodome or pycryptodomex version, 3.7.0.
- rclone_deobscure - return bytes that are not valid UTF-8, which ``rclone reveal`` returns as they are, as U+DC80 to U+DCFF, which Ansible uses for such bytes, instead of failing with a codec error, so rclone_obscure obscures the revealed value as the same bytes again.
- rclone_obscure - obscure U+DC80 to U+DCFF, which Ansible uses for bytes that are not valid UTF-8, such as from the b64decode filter, as those bytes, as ``rclone obscure`` does, instead of failing with a codec error. Another lone surrogate code point, which stands for no byte, still fails with the codec error.
- rclone_obscure, rclone_deobscure - document that an empty string is returned unchanged.
- rclone_obscure, rclone_deobscure - document when the filter result is returned.
- rclone_obscure, rclone_deobscure - fix the examples to obscure a backend password in an rclone remote rather than the configuration encryption password, which rclone reads in plaintext.
- rclone_obscure, rclone_deobscure - name pycryptodomex as well as pycryptodome in the failure when neither library is installed.
- rclone_obscure, rclone_deobscure - return an empty string for empty bytes input, as for an empty string, instead of empty bytes.
- systemd_hostname - check ``transient_hostname`` as the running systemd does, so systemd 239 accepts ``_`` and a label starting or ending with ``-``.
- systemd_hostname - check a ``deployment``, ``icon_name``, ``location``, ``pretty_hostname`` or ``transient_hostname`` that is written after another setting before writing any setting, so an invalid value fails without leaving earlier settings applied. The first setting written is left to ``systemd-hostnamed``, which refuses an invalid value before anything is changed, and a stored value that is not written, such as an icon name stored before an upgrade to a systemd that refuses it, is not checked.
- systemd_hostname - compare ``chassis``, ``deployment``, ``icon_name``, ``location`` and ``pretty_hostname`` against ``/etc/machine-info`` instead of the computed D-Bus properties, so an empty ``icon_name`` no longer reports a change on every run and a ``chassis`` that matches the detected fallback is written to the file.
- systemd_hostname - compare ``static_hostname`` against ``/etc/hostname`` instead of the reported static hostname, so a hostname with ``?`` wildcards, which systemd 258 and later substitute, no longer reports a change on every run.
- systemd_hostname - document that ``transient_hostname`` cannot be combined with changing ``static_hostname`` to a value containing the ``?`` wildcard or a ``$`` token.
- systemd_hostname - document that an empty ``transient_hostname`` requires systemd 248 or later, which added the ``HostnameSource`` property.
- systemd_hostname - document that on systemd before 246 a setting edited outside ``systemd-hostnamed`` while it runs is reported as changed on every run until it exits when idle.
- systemd_hostname - fail before writing any setting, also in check mode, when ``chassis``, ``deployment``, ``icon_name``, ``location`` or ``pretty_hostname`` would change and ``/etc/machine-info`` contains a setting that is not valid UTF-8, or on systemd 240 and later a NUL byte, which systemd-hostnamed refuses to rewrite. The module wrote ``static_hostname`` first, then failed with ``Invalid argument`` or ``Bad message``, and check mode predicted success.
- systemd_hostname - on systemd 247 and earlier, set ``transient_hostname`` while the static hostname names the local host, such as ``localhost`` or ``localhost.localdomain``, as those versions apply the transient hostname then. The module failed saying that the static hostname takes precedence, which is true from systemd 248 only. Check mode also predicts that setting such a static hostname keeps the hostname in effect on those versions, and no longer predicts ``hostname_source``, which they do not report.
- systemd_hostname - predict the static hostname and ``hostname_source`` in check mode when ``static_hostname`` is set together with an empty ``transient_hostname``.
- systemd_hostname - read ``/etc/hostname`` and ``/etc/machine-info`` as the running systemd version does, read from the ``Version`` property of ``org.freedesktop.systemd1``. Before systemd 262 only one trailing ``-`` or ``.`` is removed from the static hostname, before systemd 258 ``?`` is removed as well, and before systemd 254 a comment ending in ``\`` continues onto the next line of ``/etc/machine-info``, so a stored value is no longer misread on EL 9, EL 10, Debian 12 and Debian 13. Quoted values are read as systemd 239 and 240 read them, dropping a backslash before any character, also in single quotes, and as systemd 241 to 246 read them, keeping a backslash in double quotes except before ``"`` and dropping an escaped carriage return. Document that the version is the one the service manager reports, which after an upgrade without a reboot or ``systemctl daemon-reexec`` can be older than the running ``systemd-hostnamed`` or ``systemd-localed``.
- systemd_hostname - read ``/etc/hostname`` line by line as systemd does, so a line of 1 MiB or more before the hostname, which makes ``systemd-hostnamed`` ignore the file, reads as no static hostname. The module read a later hostname line instead and reported no change where ``systemd-hostnamed`` would write it.
- systemd_hostname - read ``/etc/hostname`` on systemd 239 as it cleans a hostname up, keeping ``_`` and every ``-`` and shortening the line to 64 bytes first, so a stored hostname such as ``my_host`` is no longer read as no static hostname.
- systemd_hostname - read ``/etc/machine-info`` as storing no settings when it contains a NUL byte, or on systemd 239 only up to the NUL byte, and stop reading it at the first setting that is not valid UTF-8, as systemd does. The module replaced such bytes and kept reading, so a setting systemd ignores was compared as stored and reported no change while systemd-hostnamed reported its fallback.
- systemd_hostname - read ``/etc/machine-info`` exactly as systemd does, so values with an apostrophe or quote inside, such as ``Taylor's Laptop``, quoted parts, trailing non-breaking spaces and continuation lines no longer report a change on every run.
- systemd_hostname - read an ``/etc/hostname`` that cannot be read, such as a symbolic link loop or one that fails with an I/O error, as no static hostname, as ``systemd-hostnamed`` 246 and later do, instead of failing. One the module may not access still fails the task, as ``systemd-hostnamed`` runs as root and reads it. Document that systemd 239 to 245 fail to start ``systemd-hostnamed`` on any error reading ``/etc/hostname`` other than a missing file, including a first hostname line left empty once invalid characters are removed, and read the file only when ``systemd-hostnamed`` starts.
- systemd_hostname - refuse ``$``, a backtick and ``\`` in ``icon_name``, ``location`` and ``pretty_hostname`` on systemd 241 to 246 before any setting is written, also in check mode, as those versions read them back from ``/etc/machine-info`` with an added backslash, so the task reported a change on every run.
- systemd_hostname - refuse ``deployment``, ``icon_name``, ``location``, ``pretty_hostname``, ``static_hostname`` and ``transient_hostname`` values holding escaped bytes, such as ``\udcc3\udca9``, or a NUL character before any setting is written, because such a value cannot be sent to ``systemd-hostnamed`` or would be cut at the NUL.
- systemd_hostname - reject ``?`` wildcards and ``$`` tokens in ``transient_hostname``, which ``systemd-hostnamed`` 258 and later replace, so the reported hostname never matched and the task reported a change on every run.
- systemd_hostname - reject an ``icon_name`` that the running systemd refuses before writing any setting when another setting is written before it, which is ``.``, ``..`` or a name containing ``/``, one longer than 255 bytes, or 4096 bytes before systemd 248, and on systemd 262 and later one containing a control character, ``\``, a quote, ``*``, ``?`` or ``[``.
- systemd_hostname - reject an ``icon_name``, ``location`` or ``pretty_hostname`` containing a Unicode noncharacter, such as U+FDD0, which systemd's D-Bus library (sd-bus) refuses, before writing any setting when another setting is written before it. The module wrote ``static_hostname`` first, then failed with ``Bad message``.
- systemd_hostname - with ``transient_hostname`` set to an empty string, no longer call ``SetHostname`` after ``SetStaticHostname`` when the static hostname changes, as ``systemd-hostnamed`` already applies the static hostname, or else the default hostname, in place of the transient one. The reported result is unchanged.
- systemd_hostname - write ``static_hostname`` before the other settings, so a value the running systemd refuses, such as a ``?`` wildcard before systemd 258, fails before anything is changed.
- systemd_hostname, systemd_hostname_info - document that ``vsock_cid`` is ``4294967295`` when the host has no VSOCK context ID, and that ``firmware_date`` and ``operating_system_support_end`` are ``18446744073709551615`` when unknown, as ``systemd-hostnamed`` reports them over D-Bus.
- systemd_hostname, systemd_hostname_info - replace the ``hostname`` sample, which mixed properties of different systemd versions, with output captured from systemd 257, with host-specific values replaced.
- systemd_hostname, systemd_locale - read ``/etc/hostname`` and the language fallback map line by line exactly as the running systemd reads them. systemd 240 and later read ``\r\n``, ``\n\r``, ``\r\0`` and ``\n\r\0`` as one line end. systemd 239 ends a line only at a line feed or a NUL, and ``systemd-localed`` 239 reads the map with ``fgets()``, so a carriage return separates fields there, a NUL ends only the text of a line and a long line is read in pieces of 2047 bytes. The module read every systemd version as 240 and later reads.
- systemd_hostname, systemd_locale, systemd_timedate - report a change, with an empty ``hostname``, ``locale`` or ``timedate``, when the module fails after it has applied a setting, such as when a later request is refused, the network time synchronization change does not settle in time, or the settings cannot be read back, instead of reporting no change.
- systemd_hostname, systemd_locale, systemd_timedate and their info modules - report a D-Bus timeout or another transport error while reading a property or calling a method as a failure naming the property or method instead of a traceback.
- systemd_hostname_info, systemd_locale_info, systemd_timedate_info - document that the returned settings are empty, and ``timezones`` an empty list, when dasbus is unavailable in check mode.
- systemd_hostname_info, systemd_locale_info, systemd_timedate_info, systemd_hostname, systemd_locale, systemd_timedate - fail with a clear message instead of a GLib error when the system bus cannot be reached.
- systemd_locale - check a keyboard value sent after another request for the characters ``systemd-localed`` refuses, a control character, a quote or ``\`` and on systemd 261 and later a glob character, and a console keymap that is not a valid file name or is too long, before any setting is written, also in check mode, so such a value no longer fails after the locale is written.
- systemd_locale - compare the X11 keyboard settings against the values systemd-localed converted from a new ``vconsole_keymap`` before writing them, so X11 options left unset no longer write back the old layout and revert the console keymap, and the task converges in one run.
- systemd_locale - correct the note on converting X11-only changes, which clear the console toggle keymap on systemd 252 when the converted keymap differs from the current one and on systemd 253 and later even when it does not, not only on systemd 257.
- systemd_locale - document that ``systemd-localed`` refuses a list in ``locale.language``, such as ``en_AU:en_GB``, on systemd 256 and later, which refuse ``:`` in locale values, and from systemd 246 wherever it checks that each locale is installed, which systemd 246 and 247 always do and systemd 248 to 255 do unless they generate it with ``locale-gen``, as on EL, where it reports the list as not installed.
- systemd_locale - document that ``systemd-localed`` writes the fallback ``LANGUAGE`` without validating it, so it can be a list such as ``en_AU:en_GB``, which ``locale.language`` cannot set again where ``systemd-localed`` refuses a list, from systemd 256 everywhere and from systemd 246 where it checks that each locale is installed, as on EL, and that the returned ``language`` then cannot be fed back where it differs from the configured one.
- systemd_locale - document that a console keymap or X11 layout refused by systemd-localed is reported after the earlier settings are applied.
- systemd_locale - document that a set ``language`` is kept unless it equals the resulting ``LANG``, that an empty ``language`` counts as not set, and that ``systemd-localed`` drops any variable equal to the resulting ``LANG``, the requested or the configured one.
- systemd_locale - document that in check mode ``locale`` holds the settings predicted from the options, and that it is empty when dasbus is unavailable in check mode.
- systemd_locale - document that systemd 253 and later also keep the X11 keyboard settings in ``/etc/vconsole.conf`` and ignore a failure to write ``/etc/X11/xorg.conf.d/00-keyboard.conf``, which Debian 13 makes read-only for systemd-localed when the directory exists as systemd-localed starts. Clearing all of the X11 keyboard settings there is not kept either, as systemd-localed reports the settings in that file again once it restarts, as it does after exiting when idle, so such a task reports a change again on each run after systemd-localed restarts.
- systemd_locale - document the check-mode limits under ``attributes.check_mode`` and mark its support as partial.
- systemd_locale - document the files ``systemd-localed`` writes on EL and Debian, and that on Debian it generates a missing locale during the request instead of refusing it.
- systemd_locale - fail before any setting is written, also in check mode, when ``lang`` changes without a set ``language`` and the language fallback map lists a fallback for it that is not valid UTF-8 or contains a Unicode noncharacter. ``systemd-localed`` writes such a fallback to the locale configuration and then fails to report the locale, as seen on systemd 252, and check mode returned it as lone surrogates. A real run reads the map for this check, and returns the locale ``systemd-localed`` reports otherwise.
- systemd_locale - fail before any setting is written, also in check mode, when a locale or keyboard value is not valid UTF-8, such as one with a lone surrogate code point, or contains a NUL character, or a keyboard value sent after another request contains a Unicode noncharacter. A keyboard value that was not valid UTF-8 failed with a traceback after the locale was written, and one with a noncharacter failed with a D-Bus error after the locale was written. A value with a NUL character was cut at the NUL, so a different value was written and the task reported a change on every run.
- systemd_locale - fail before writing any setting when ``locale`` would change the locale on systemd older than 239, whose ``systemd-localed`` clears the locale variables a request leaves out.
- systemd_locale - fail before writing any setting, also in check mode, when a keyboard request sent after another request, or converting the settings after writing its own file, would make systemd-localed rewrite ``/etc/vconsole.conf`` or, on Debian 12, ``/etc/default/keyboard`` while it contains a NUL byte or a setting that is not valid UTF-8. systemd-localed refuses to rewrite such a file, so the module applied ``locale`` and then failed, or reported a console keymap or a converted keyboard setting as changed although systemd-localed did not store it.
- systemd_locale - fail when the language fallback map may not be read, as ``systemd-localed`` runs as root and reads it, instead of predicting no fallback.
- systemd_locale - on systemd 253 and later, fail before writing any setting, also in check mode, when a keyboard change would make systemd-localed rewrite ``/etc/vconsole.conf`` while it contains a NUL byte or a setting that is not valid UTF-8, even when that keyboard request is the first one sent. These systemd versions only log the failed rewrite and report the request as applied, so once systemd-localed had cached the unreadable file the module reported a change on every run although nothing was written.
- systemd_locale - predict in check mode the ``LANGUAGE`` that ``systemd-localed`` sets from its language fallback map, ``/usr/share/systemd/language-fallback-map``, when ``lang`` changes without a set ``language``. Check mode reported the configured ``LANGUAGE`` instead. The map is read line by line as ``systemd-localed`` reads it, with quotes removed, backslash escapes, a NUL ending a line, and no fallback after a line it cannot read or split, such as one of 1 MiB or more or one with an unbalanced quote.
- systemd_locale - say that the language fallback map refusal covers a fallback with a Unicode noncharacter, and document that it fails in check mode only when dasbus is available.
- systemd_locale - send ``systemd-localed`` only the requested locale variables that differ from the configured ones, together with a set ``language`` when ``lang`` changes. An unchanged ``lang`` sent with another change made ``systemd-localed`` replace a configured ``LANGUAGE`` with the value from its language fallback map, such as ``en_AU:en_GB`` for ``en_AU``, while check mode reported ``LANGUAGE`` unchanged.
- systemd_locale - send only the requested locale variables to systemd-localed, which merges them into the configured ones, so a configured variable it refuses, such as a ``LANGUAGE`` list like ``en_US:en``, no longer makes every later locale change fail.
- systemd_locale - write the X11 keyboard settings without converting them back into the console keymap when ``vconsole_keymap`` or ``vconsole_keymap_toggle`` is also set, so systemd-localed no longer clears the requested ``vconsole_keymap_toggle``, a ``vconsole_keymap`` and an ``x11_layout`` that do not correspond no longer overwrite each other, and the task converges instead of reporting a change on every run.
- systemd_locale - write the console settings without converting them into the X11 keyboard settings when ``vconsole_keymap`` is unchanged and only the toggle keymap changes. ``systemd-localed`` converted the unchanged keymap and replaced the configured X11 layout, model and options, which check mode did not predict and a second run did not report.
- systemd_timedate - accept the Greek small letter mu (U+03BC) in the microsecond unit of ``time``, such as ``+500μs``, as systemd 254 and later do, in addition to the micro sign (U+00B5), a span after ``@``, such as ``@1h`` or ``@1min 30s``, a span that starts with a decimal point, such as ``+.5s``, and relative times written as ``5min ago`` or ``5min left``, as systemd does, and reject ``@1e9`` or ``@1_000``, which systemd refuses.
- systemd_timedate - accept the ``time`` forms systemd accepts that the module refused, such as a fraction of seconds with more than six digits, ``Jul 26 14:30:00``, ``++5min``, and on systemd 257 a time zone name suffix (``2026-07-26 14:30 Europe/Berlin``).
- systemd_timedate - document that ``time`` requires ``systemd-analyze`` from systemd 243 or later in ``requirements``.
- systemd_timedate - document that in check mode ``timedate`` holds the settings predicted from the options, with ``time_usec`` set to the time ``time`` would set, and that it is empty when dasbus is unavailable in check mode.
- systemd_timedate - document that systemd 258 and later refuse a ``time`` before the systemd build date only after the earlier settings are applied.
- systemd_timedate - fail before any setting is written, also in check mode, when ``timezone`` is not valid UTF-8 or contains a NUL character, or ``time`` contains a lone surrogate code point from U+D800 to U+DC7F, which cannot be passed to ``systemd-analyze``. A value that was not valid UTF-8 failed with a traceback, and a ``timezone`` with a NUL character was cut at the NUL, so a different value was written and the task reported a change on every run.
- systemd_timedate - fail before writing any setting when ``time`` is at or after ``@8277292036``, 2232-04-18 23:47:16 UTC, which the kernel refuses to set, instead of failing after ``timezone`` or another setting written before the clock was applied.
- systemd_timedate - fail before writing any setting when ``time`` is set after another setting while network time synchronization would stay enabled, or when an absolute ``time`` is at or before the epoch, instead of failing after earlier settings were applied. A ``time`` set first, or an ``ntp`` enabled first without a network time service, is refused by ``systemd-timedated`` before anything is changed.
- systemd_timedate - fail when ``ntp=true`` and the network time service, such as ``chronyd``, fails to start, instead of reporting a change with ``ntp`` enabled and changing again on every run. ``systemd-timedated`` reports network time synchronization enabled while the start job runs, so the module now waits until systemd has no job left for the network time services named in the ``ntp-units.d/*.list`` files of ``systemd-timedated`` before it takes the change as reported, and fails when one is still queued after 30 seconds.
- systemd_timedate - fail when a weekday prefix in ``time`` does not match the date, as systemd does, instead of ignoring it.
- systemd_timedate - read the current time for ``time=now`` right before setting the clock, after the settings written before it and after the wait for the ``ntp`` change when ``ntp`` changes, so the clock is no longer set back by the time they took.
- systemd_timedate - reject a relative ``time`` that resolves to a time at or before the epoch, such as ``-60y``, before any setting is written. ``systemd-timedated`` refused it only after the other settings in the same task, such as ``timezone``, were applied.
- systemd_timedate - reject digits other than ASCII ``0`` to ``9`` and whitespace other than ASCII in ``time``, such as ``2026-07-2٦ 14:30`` or ``+٣h``, which systemd refuses but the module turned into a change of the clock.
- systemd_timedate - run ``systemd-analyze timestamp`` with ``SYSTEMD_COLORS=0``. On systemd 257 and later, ``SYSTEMD_COLORS`` set in the task environment coloured its output, so every ``time`` failed with unexpected output.
- systemd_timedate - set ``time=now`` to the current time, as ``timedatectl set-time now`` does, instead of sending a zero relative offset that systemd-timedated ignores.
- systemd_timedate - set a ``time`` with a fractional span to the exact microsecond, such as ``+1.000001s``, which the module rounded down by one microsecond.
- systemd_timedate - set the clock before ``local_rtc`` unless ``ntp`` changes or ``adjust_system_clock`` is set, so a ``time`` ``systemd-timedated`` refuses, such as one before the systemd build date on systemd 258 and later, no longer leaves ``local_rtc`` written. The clock and the hardware clock end up as with the earlier order.
- systemd_timedate - wait up to 30 seconds after changing ``ntp`` until systemd-timedated reports the change, and fail when it does not, before setting ``time``. systemd-timedated replies before the time service has stopped and refuses ``SetTime`` until it has, so ``ntp=false`` with ``time`` failed with "Previous request is not finished, refusing".
- systemd_timedate - with ``ntp=true``, read the lines of an ``ntp-units.d/*.list`` file as ``systemd-timedated`` does, ending a line at a NUL as well as a line feed or carriage return, and removing only spaces, tabs, line feeds and carriage returns around a name. The module did not wait for services listed after a NUL, and waited for names surrounded by other whitespace, such as a vertical tab or U+00A0, which ``systemd-timedated`` ignores.
- systemd_timedate - with ``ntp=true``, skip an ``ntp-units.d/*.list`` file that cannot be opened or read, such as a dangling symlink, a symlink loop or a directory, as ``systemd-timedated`` does, instead of failing after network time synchronization was changed. As in ``systemd-timedated``, a file that cannot be followed does not override a file of the same name in a later directory, and a file linked to any character device names nothing.
- systemd_timedate - with ``ntp=true``, skip the lines of the ``ntp-units.d/*.list`` files that are not valid plain unit names, such as ``chronyd`` or ``foo@.service``, which ``systemd-timedated`` ignores, instead of failing after network time synchronization was changed.
- systemd_timedate - with ``ntp`` changed on systemd 239 to 242, wait for the jobs of ``systemd-timesyncd.service``, which ``systemd-timedated`` manages by default there, instead of the services named in ``ntp-units.d/*.list`` files, which it reads only from systemd 243. On systemd 241 and 242, which report network time synchronization enabled while the service starts, a start that failed was reported as a change with ``ntp`` enabled instead of failing after 30 seconds.
- systemd_timedate, systemd_timedate_info - document that ``rtc_time_usec`` is ``0`` when the host has no real-time clock or it is busy, from systemd 256 also when it holds no valid time, and from systemd 257 also when its time cannot be converted, as ``systemd-timedated`` reports these without an error.
- systemd_timedate, systemd_timedate_info - return ``rtc_time_usec`` as ``null`` when systemd-timedated reports that it failed to read the hardware clock, instead of failing before reading or changing any other setting. Other failures to read the property still fail. Document that systemd-timedated then changes ``local_rtc`` without updating the system clock for ``adjust_system_clock=true``.
- systemd_timedate_info - document that it requires systemd 240 or later for ``ListTimezones``.

v2.4.12
=======

Bugfixes
--------

- post_transaction_actions role - write action files with the ``.action`` extension, which the dnf plugin requires; ``.conf`` files were ignored (https://github.com/linuxhq/ansible-collection-linux/pull/68).

v2.4.11
=======

Security Fixes
--------------

- msmtpd - run the container with ``NoNewPrivileges=true`` and drop all capabilities except ``CHOWN``, ``DAC_OVERRIDE``, ``FOWNER``, ``KILL``, ``SETGID`` and ``SETUID``, which the s6 init needs to set up logging and drop to ``nobody``.

v2.4.10
=======

Minor Changes
-------------

- monit - default ``monit_eventqueue_basedir`` to ``/var/lib/monit/events`` instead of the world-writable ``/tmp``, which ``systemd-tmpfiles`` ages out, and create the directory with mode ``0700`` when it is missing, because monit drops queued events when it cannot create the directory itself.
- msmtpd - align the health check with other quadlets (``HealthInterval=60s``, ``HealthRetries=3``, ``HealthTimeout=10s``) and add a startup health check with ``Notify=healthy`` and ``TimeoutStartSec=600``.

Bugfixes
--------

- msmtpd - probe the daemon with ``msmtp --serverinfo`` instead of ``nc -z``, which logged a ``client did not send initial command`` error on every health check.

v2.4.9
======

Bugfixes
--------

- template - apply the ``attributes`` item option, which a misspelled loop variable caused to be silently ignored.

v2.4.8
======

Minor Changes
-------------

- msmtpd - run the msmtpd daemon as ``nobody`` (``PUID`` and ``PGID`` ``65534``) in the host user namespace.

Removed Features (previously deprecated)
----------------------------------------

- msmtpd - remove the ``msmtpd_uidmap`` and ``msmtpd_gidmap`` variables and the container ``UIDMap`` and ``GIDMap`` settings.

v2.4.7
======

Release Summary
---------------

Runs the msmtpd container without an IPC namespace.

Minor Changes
-------------

- msmtpd - run the container with ``--ipc=none`` so it has no ``/dev/shm`` or IPC namespace access.

v2.4.6
======

Release Summary
---------------

Adds a per-repository become_user to the git role so repositories can be cloned and updated as the user that owns them.

Minor Changes
-------------

- git - add ``become_user`` to ``git_repositories`` entries to run git as that user when ``become`` is set, defaulting to root.

v2.4.5
======

Release Summary
---------------

Narrows the rclone role to installing rclone and managing a per-user configuration. Mounts are no longer handled by the role; use podman quadlet volumes instead.

Breaking Changes / Porting Guide
--------------------------------

- rclone - removed ``rclone_mounts``, ``rclone_image`` and the podman role dependency. Mount remotes with ``podman_quadlet_volumes`` using ``Type=rclone`` instead.

v2.4.4
======

Release Summary
---------------

Runs rclone mounts as rootful podman containers, adds SELinux file context management to the selinux role and quadlet volumes to the podman_quadlet role, and makes the podman, podman_quadlet and msmtpd roles safe to run in check mode. The rclone role drops its host mounts and several variables, so read the porting guide before upgrading.

Minor Changes
-------------

- msmtpd, podman, podman_quadlet, rclone - run Molecule scenarios in check mode before and after converge.
- podman_quadlet - add ``podman_quadlet_volumes`` to manage quadlet ``.volume`` units alongside containers and networks.
- rclone - add ``rclone_image`` to set the container image used for mounts.
- rclone - add ``rclone_user`` to write the configuration to that user's ``~/.config/rclone``.
- rclone - cache each mount in ``/root/.cache/rclone/<name>`` and order it after the filesystems its mountpoint lives on.
- rclone - depend on the podman role and remount every mount when the configuration or its password changes.
- selinux - add ``selinux_fcontexts`` to manage persistent SELinux file context rules and ``selinux_restorecon`` to relabel paths when a rule changes.
- selinux - install ``python3-policycoreutils`` by default, which file context management requires.

Breaking Changes / Porting Guide
--------------------------------

- rclone - mounts now run only as rootful podman quadlets, one container per mount in ``/etc/containers/systemd/<name>.container``. Host ``rclone mount`` services are no longer created.
- rclone - the ``flags`` key of ``rclone_mounts`` was replaced by ``environment``, a mapping of ``RCLONE_*`` variables passed to the mount container.
- rclone - the ``rclone_profile`` and ``rclone_sysconfig`` variables were removed along with ``/etc/profile.d/rclone.sh`` and ``/etc/sysconfig/rclone``. ``RCLONE_CONFIG_PASS`` is now provided by the ``rclone_config_pass`` podman secret.
- rclone - the configuration file moved from ``/etc/rclone/rclone.conf`` to ``~/.config/rclone/rclone.conf`` of ``rclone_user`` (``/root/.config/rclone/rclone.conf`` by default) and the ``rclone_config_path`` variable was removed.

Bugfixes
--------

- msmtpd, podman, podman_quadlet, rclone - do not fail in check mode when starting or restarting units that do not exist yet.

v2.4.3
======

Release Summary
---------------

Adds SELinux boolean management to the selinux role and schedules a filesystem relabel before rebooting a host out of the disabled state.

Minor Changes
-------------

- selinux - add ``selinux_booleans`` to manage persistent SELinux booleans.
- selinux - install ``python3-libsemanage`` by default, which persistent boolean changes require.

Bugfixes
--------

- selinux - create ``/.autorelabel`` before rebooting a host from disabled to permissive or enforcing, so the filesystem is relabeled before policy is enforced.

v2.4.2
======

Release Summary
---------------

Adds podman roles for the container engine, rootless quadlet stacks and a rootful msmtpd relay, along with a new dependency on the containers.podman collection.

Minor Changes
-------------

- collection - add the ``containers.podman`` collection as a dependency.
- msmtpd - new role to run a minimal SMTP relay as a rootful podman quadlet.
- podman - new role to install the podman container engine and enable its system timers.
- podman_quadlet - new role that allows users to manage quadlets.

v2.4.1
======

Release Summary
---------------

Maintenance release aligning agent setup guidance, using relative role dependency links, and forwarding the Cloudflare WARP token to Molecule scenarios.

v2.4.0
======

Release Summary
---------------

Adds D-Bus modules and roles for systemd hostname, locale and timedate management, replacing the shell-based hostnamectl, localectl and timedatectl tasks that were previously part of the systemd role. The new modules talk directly to the system bus via dasbus, support check mode, and report changes accurately. The old variables are removed from the systemd role, so read the porting guide before upgrading.

Minor Changes
-------------

- systemd_hostname - new role to manage the systemd hostname settings.
- systemd_hostname_info - new role to gather the systemd hostname settings.
- systemd_locale - new role to manage the systemd locale and keyboard settings.
- systemd_locale_info - new role to gather the systemd locale and keyboard settings.
- systemd_timedate - new role to manage the systemd time and date settings.
- systemd_timedate_info - new role to gather the systemd time and date settings.

Breaking Changes / Porting Guide
--------------------------------

- systemd - the ``systemd_hostnamectl``, ``systemd_localectl`` and ``systemd_timedatectl`` variables have been removed. The settings they drove now live in the dedicated ``systemd_hostname``, ``systemd_locale`` and ``systemd_timedate`` roles, which call the matching modules over the system bus and report changes accurately, rather than running ``hostnamectl``, ``localectl`` and ``timedatectl`` with ``changed_when`` pinned to false.

New Modules
-----------

- systemd_hostname - Manage the systemd hostname
- systemd_hostname_info - Gather the systemd hostname settings
- systemd_locale - Manage the systemd locale and keyboard settings
- systemd_locale_info - Gather the systemd locale and keyboard settings
- systemd_timedate - Manage the systemd time and date settings
- systemd_timedate_info - Gather the systemd time and date settings

v2.3.0
======

Release Summary
---------------

Adds an rclone configuration encryption module and a set of kopia modules,
and rewrites both roles to use them rather than shelling out to the CLI.
Neither role now places a repository password on a command line, and the
rclone configuration is never written to disk in plaintext before being
encrypted. The kopia role variables change shape as a result, so read the
porting guide before upgrading.

Minor Changes
-------------

- kopia - add ``kopia_snapshot``, a boolean that defaults to V(false), controlling whether a snapshot is taken for each policy target on every run.
- kopia - the repository password is passed to the modules rather than interpolated into a command line, so it no longer appears in the process table.
- rclone - install ``python3-pycryptodomex``, required by ``rclone_config_encryption``.
- rclone - manage the configuration file with a single ``rclone_config_encryption`` task instead of templating it and then shelling out to ``rclone config encryption``. The plaintext no longer lands on disk before being encrypted, and the password is no longer passed on a command line where it was visible in the process table.
- roles - drop the ``{{ ansible_managed }}`` header from every template. The ``DEFAULT_MANAGED_STR`` configuration that populates the variable is deprecated and slated for removal in ansible-core 2.23, after which the variable is no longer provided and the templates would render it undefined. Managed files no longer carry the generated header comment.

Breaking Changes / Porting Guide
--------------------------------

- kopia - ``kopia_server`` is removed and the server is always configured, and the role connects the repository and leaves it connected.
- kopia - the role now manages the repository, maintenance settings, policies and snapshots with the ``kopia_repository``, ``kopia_maintenance``, ``kopia_policy`` and ``kopia_snapshot`` modules instead of shelling out to the kopia CLI, so the variables that fed those commands take structured values rather than command line flags. ``kopia_repository`` becomes a dict of ``storage``, ``options`` and ``secrets`` in place of ``location`` and ``flags``; ``kopia_maintenance`` becomes a dict of settings in place of a list of flags; and each entry in ``kopia_policies`` carries a ``policy`` dict in place of ``flags``.
- kopia_repository - the ``state`` option is removed and the module only connects. Disconnecting left a server running with nothing to serve, so tearing a host down is no longer modelled here.

New Modules
-----------

- kopia_maintenance - Manage kopia repository maintenance settings
- kopia_maintenance_info - Gather kopia repository maintenance settings
- kopia_policy - Manage a kopia snapshot policy
- kopia_policy_info - Gather kopia snapshot policies
- kopia_repository - Manage the kopia repository connection
- kopia_repository_info - Gather kopia repository status
- kopia_snapshot - Create a kopia snapshot
- kopia_snapshot_info - Gather information about kopia snapshots
- rclone_config_encryption - Manage rclone configuration file encryption

v2.2.6
======

Release Summary
---------------

Adds rclone obscure/deobscure filter plugins, drops support for ansible-core older than 2.18, and introduces CI sanity testing and gated releases.

Minor Changes
-------------

- ci - add an ansible-test sanity workflow matching sibling collections.
- ci - gate releases on pre-commit and sanity, and verify the tag matches the galaxy.yml version before publishing.
- dependabot - add weekly updates for github-actions, pip, and pre-commit.
- galaxy - add build_ignore so published artifacts exclude development files and molecule scenarios.
- pre-commit - sync hooks with sibling collections (antsibull-changelog, ruff, black, ansible-lint v26.6.0).
- python - drop unused awscli, boto3, botocore, docker, hvac, and python-gilt requirements.
- python - update ansible to >=14,<15 to match ansible-collection-aws.
- python - update pinned Python to 3.13.
- rclone_deobscure - new filter plugin to reveal obscured rclone configuration values (requires pycryptodome).
- rclone_obscure - new filter plugin to obscure plaintext values for rclone configurations (requires pycryptodome).
- readme - document collection requirements and simplify molecule setup.

Breaking Changes / Porting Guide
--------------------------------

- meta - bump min_ansible_version to 2.18.0 across all roles.
- meta - require ansible-core >=2.18.0; older ansible-core releases are no longer supported.

New Plugins
-----------

Filter
~~~~~~

- rclone_deobscure - Reveal a password from an obscured rclone value
- rclone_obscure - Obscure a password for an rclone configuration

v2.2.5
======

Release Summary
---------------

Fixes the cloudflared_tunnel service loop issue.

Bugfixes
--------

- cloudflared_tunnel - fix service loop / mapping issue.

v2.2.4
======

Release Summary
---------------

Fixes needs_restarting crontab stderr redirection.

Minor Changes
-------------

- ansible-lint - ignore molecule tests.
- pre-commit - multiple updates.

Bugfixes
--------

- needs_restarting - fix stderr crontab output redirection.

v2.2.3
======

Release Summary
---------------

Updates pre-commit configs and fixes linting issues.

Minor Changes
-------------

- pre-commit - update configs and fix linting issues.

v2.2.2
======

Release Summary
---------------

Loosens ansible.posix dependency versioning.

Minor Changes
-------------

- galaxy - loosen ansible.posix dependency versioning.

v2.2.1
======

Release Summary
---------------

Updates the cloudflare_warp role to support modification of log level at the systemd service level.

Minor Changes
-------------

- cloudflare_warp - add support for changing log level.
- cloudflare_warp - use systemd override instead of lineinfile.

v2.2.0
======

Release Summary
---------------

This release provides a toggle for a cloudflare warp systemd addition by defining NO_COLOR=1 in the service files.

Minor Changes
-------------

- cloudflare_warp - add option to toggle no color environment variable.

v2.1.9
======

Release Summary
---------------

This release changes cloudflared role behavior migrating from locally configured tunnels to cloudflare managed tunnels, therefore only overlaying a tunnel token.

Breaking Changes / Porting Guide
--------------------------------

- cloudflared - use managed tunnels and only overlay a single token.

v2.1.8
======

Release Summary
---------------

This release adds support for overlaying custom scripts alongside cloudflare warp.

Minor Changes
-------------

- cloudflare_warp - add support for overlaying custom scripts.

v2.1.7
======

Release Summary
---------------

This release adds support for defining include files in the openssh server configuration file.

Minor Changes
-------------

- openssh_server - add support for defining include files in sshd_config.

v2.1.6
======

Release Summary
---------------

This release includes a minor change to rclone role config pass population.

Minor Changes
-------------

- rclone - only populate rclone_config_pass if mounts are defined.

v2.1.5
======

Release Summary
---------------

This release includes a new role - cloudflare_warp.

Minor Changes
-------------

- cloudflare_warp - initial commit.

v2.1.4
======

Release Summary
---------------

A set of breaking and minor changes to the rclone role.

Minor Changes
-------------

- rclone - add support for encrypting the rclone configuration file.

Breaking Changes / Porting Guide
--------------------------------

- rclone - renamed rclone_conf to rclone_config to align with other defaults.

v2.1.3
======

Release Summary
---------------

A set of minor fixes for the epel and remi roles. Update galaxy requirements.yml versions.

Bugfixes
--------

- epel - fix conditional around ansible_distribution_major_version.
- remi - fix remi-release installation, removal of rpm keys from defaults.

v2.1.2
======

Release Summary
---------------

Addition of the Remi's RPM repository role.

Minor Changes
-------------

- remi - initial commit.

v2.1.1
======

Release Summary
---------------

Updates the systemd_resolved configuration template to correctly handle iterable values.

Breaking Changes / Porting Guide
--------------------------------

- systemd_resolved - iterable values are now handled differently.

v2.1.0
======

Release Summary
---------------

Ensures galaxy dependencies are less strict.

Minor Changes
-------------

- galaxy - ensure dependencies are less strict.

v2.0.9
======

Release Summary
---------------

This is the beginning of the linuxhq.linux collection changelog.

Minor Changes
-------------

- changelog - addition of antsibull-changelog.
- cloudflared - update systemd unit (network-online.target).
- galaxy - update dependency versions.
- rclone - use epel package.
- systemd - initial commit.
- systemd_networkd - initial commit.
- systemd_resolved - initial commit.

Breaking Changes / Porting Guide
--------------------------------

- hostnamectl - deprecated.
- localectl - deprecated.
- logind - deprecated.
- network_manager - deprecated.
- rclone - update rclone_conf from dict to list.
- timedatectl - deprecated.
