#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_locale_info
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.4.0"
short_description: Gather the systemd locale and keyboard settings
description:
  - Gather the system locale, virtual console keymap and X11 keyboard layout
    reported by C(systemd-localed), the same data C(localectl status) prints,
    from the C(org.freedesktop.locale1) interface on the system bus.
notes:
  - Requires a running C(systemd-localed) reachable on the system D-Bus, so the
    module does not work in a container or chroot without systemd.
requirements:
  - dasbus
attributes:
  check_mode:
    description: This module only retrieves information and does not modify state.
    support: full
    details: Returns empty result data when dasbus is unavailable.
  diff_mode:
    description: Diff mode is not supported.
    support: none
"""

EXAMPLES = r"""
- name: Ensure the locale and keyboard settings are gathered
  linuxhq.linux.systemd_locale_info:
  register: __systemd_locale_query
"""

RETURN = r"""
locale:
  description:
    - Locale and keyboard settings reported by C(systemd-localed).
    - The C(locale) field holds the locale variables, and variables that are not
      configured are returned as V(none).
    - Empty when dasbus is unavailable in check mode.
  returned: always
  type: dict
  contains:
    locale:
      description:
        - Locale variables, each named after its variable in lowercase.
      returned: always
      type: dict
      contains:
        lang:
          description:
            - Value of C(LANG).
          returned: always, as V(none) when it is not configured
          type: str
        language:
          description:
            - Value of C(LANGUAGE).
          returned: always, as V(none) when it is not configured
          type: str
        lc_address:
          description:
            - Value of C(LC_ADDRESS).
          returned: always, as V(none) when it is not configured
          type: str
        lc_collate:
          description:
            - Value of C(LC_COLLATE).
          returned: always, as V(none) when it is not configured
          type: str
        lc_ctype:
          description:
            - Value of C(LC_CTYPE).
          returned: always, as V(none) when it is not configured
          type: str
        lc_identification:
          description:
            - Value of C(LC_IDENTIFICATION).
          returned: always, as V(none) when it is not configured
          type: str
        lc_measurement:
          description:
            - Value of C(LC_MEASUREMENT).
          returned: always, as V(none) when it is not configured
          type: str
        lc_messages:
          description:
            - Value of C(LC_MESSAGES).
          returned: always, as V(none) when it is not configured
          type: str
        lc_monetary:
          description:
            - Value of C(LC_MONETARY).
          returned: always, as V(none) when it is not configured
          type: str
        lc_name:
          description:
            - Value of C(LC_NAME).
          returned: always, as V(none) when it is not configured
          type: str
        lc_numeric:
          description:
            - Value of C(LC_NUMERIC).
          returned: always, as V(none) when it is not configured
          type: str
        lc_paper:
          description:
            - Value of C(LC_PAPER).
          returned: always, as V(none) when it is not configured
          type: str
        lc_telephone:
          description:
            - Value of C(LC_TELEPHONE).
          returned: always, as V(none) when it is not configured
          type: str
        lc_time:
          description:
            - Value of C(LC_TIME).
          returned: always, as V(none) when it is not configured
          type: str
    vconsole_keymap:
      description:
        - Virtual console keymap.
      returned: always
      type: str
    vconsole_keymap_toggle:
      description:
        - Virtual console toggle keymap.
      returned: always
      type: str
    x11_layout:
      description:
        - X11 keyboard layout.
      returned: always
      type: str
    x11_model:
      description:
        - X11 keyboard model.
      returned: always
      type: str
    x11_options:
      description:
        - X11 keyboard options.
      returned: always
      type: str
    x11_variant:
      description:
        - X11 keyboard variant.
      returned: always
      type: str
  sample:
    locale:
      lang: en_US.UTF-8
      language: null
      lc_address: null
      lc_collate: null
      lc_ctype: null
      lc_identification: null
      lc_measurement: null
      lc_messages: null
      lc_monetary: null
      lc_name: null
      lc_numeric: null
      lc_paper: null
      lc_telephone: null
      lc_time: en_DK.UTF-8
    vconsole_keymap: us
    vconsole_keymap_toggle: ''
    x11_layout: us
    x11_model: pc105
    x11_options: ''
    x11_variant: ''
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.linux.plugins.module_utils.systemd import (
    HAS_DASBUS,
    locale_status,
    systemd_proxy,
)


def info(module):
    if module.check_mode and not HAS_DASBUS:
        module.exit_json(changed=False, locale={})

    proxy = systemd_proxy(module, "locale1")

    locale = locale_status(module, proxy)

    module.exit_json(changed=False, locale=locale)


def main():
    module = AnsibleModule(
        argument_spec={},
        supports_check_mode=True,
    )

    info(module)


if __name__ == "__main__":
    main()
