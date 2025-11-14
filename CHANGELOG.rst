===========================
linuxhq.linux Release Notes
===========================

.. contents:: Topics

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
