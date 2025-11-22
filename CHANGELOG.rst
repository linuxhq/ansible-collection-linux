===========================
linuxhq.linux Release Notes
===========================

.. contents:: Topics

v2.1.3
======

Release Summary
---------------

A set of minor fixes for the epel and remi roles. Update galaxy requirements.yml versions.

Minor Changes
-------------

- epel - Fix conditional around ansible_distribution_major_version
- remi - Fix remi-release installation, removal of rpm keys from defaults

v2.1.2
======

Release Summary
---------------

Addition of remis rpm repository role

Minor Changes
-------------

- Initial commit of remi role

v2.1.1
======

Release Summary
---------------

Updates systemd_resolved configuration template to correctly handle iterable values

Breaking Changes / Porting Guide
--------------------------------

- Iterable values in systemd_resolved config are now handled differently

v2.1.0
======

Release Summary
---------------

Ensure galaxy dependencies are less strict

Minor Changes
-------------

- Ensure galaxy dependencies are less strict

v2.0.9
======

Release Summary
---------------

This is the beginning of the linuxhq.linux collection changelog.

Minor Changes
-------------

- Added antsibull-changelog support
- Initial commit of systemd role
- Initial commit of systemd_networkd role
- Initial commit of systemd_resolved role
- Update cloudflared systemd unit (network-online.target)
- Update galaxy dependency versions
- Update rclone role to use epel release

Breaking Changes / Porting Guide
--------------------------------

- Deprecated hostnamectl role in favor of systemd role
- Deprecated localectl role in favor of systemd role
- Deprecated logind role in favor of systemd role
- Deprecated network_manager role in favor of systemd_networkd
- Deprecated timedatectl role in favor of systemd role
- Update rclone_conf default from dict->list
