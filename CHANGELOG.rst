===========================
linuxhq.linux Release Notes
===========================

.. contents:: Topics

v2.1.4
======

Release Summary
---------------

A set of breaking and minor changes to the rclone role

Minor Changes
-------------

- rclone - added support for encrypting rclone configuration file

Breaking Changes / Porting Guide
--------------------------------

- rclone - renamed rclone_conf to rclone_config to align with other defaults

v2.1.3
======

Release Summary
---------------

A set of minor fixes for the epel and remi roles. Update galaxy requirements.yml versions.

Minor Changes
-------------

- epel - fix conditional around ansible_distribution_major_version
- remi - fix remi-release installation, removal of rpm keys from defaults

v2.1.2
======

Release Summary
---------------

Addition of remis rpm repository role

Minor Changes
-------------

- remi - initial commit

v2.1.1
======

Release Summary
---------------

Updates systemd_resolved configuration template to correctly handle iterable values

Breaking Changes / Porting Guide
--------------------------------

- systemd_resolved - iterable values are now handled differently

v2.1.0
======

Release Summary
---------------

Ensure galaxy dependencies are less strict

Minor Changes
-------------

- galaxy - ensure dependencies are less strict

v2.0.9
======

Release Summary
---------------

This is the beginning of the linuxhq.linux collection changelog.

Minor Changes
-------------

- changelog - addition of antsibull-changelog
- cloudflared - update systemd unit (network-online.target)
- galaxy - update dependency versions
- rclone - use epel package
- systemd - initial commit
- systemd_networkd - initial commit
- systemd_resolved - initial commit

Breaking Changes / Porting Guide
--------------------------------

- hostnamectl - deprecated
- localectl - deprecated
- logind - deprecated
- network_manager - deprecated
- rclone - update rclone_conf from dict->list
- timedatectl - deprecated
