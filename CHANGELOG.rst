===========================
linuxhq.linux Release Notes
===========================

.. contents:: Topics

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
