# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_locale_info
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.4.0
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
  returned: always
  type: dict
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
