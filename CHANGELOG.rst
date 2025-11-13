===========================
linuxhq.linux Release Notes
===========================

.. contents:: Topics

v2.0.9
======

Release Summary
---------------

This is the beginning of the linuxhq.linux changelog.  Unfortunately all previous release changes will need to be reviewed via git logs.

Minor Changes
-------------

- Removal of empty CHANGELOG.md
- This is the beginning of the linuxhq.linux changelog
- Update galaxy dependency versions

Breaking Changes / Porting Guide
--------------------------------

- Deprecated hostnamectl role in favor of systemd role
- Deprecated localectl role in favor of systemd role
- Deprecated logind role in favor of systemd role
- Deprecated network_manager role in favor of systemd_networkd
- Deprecated timedatectl role in favor of systemd role
- Initial commit of systemd role
- Initial commit of systemd_networkd role
- Initial commit of systemd_resolved role
