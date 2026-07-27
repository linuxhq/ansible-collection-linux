# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_timedate_info
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.4.0
short_description: Gather the systemd time and date settings
description:
  - Gather the time zone, hardware clock and network time settings reported by
    C(systemd-timedated), the same data C(timedatectl status) prints, from the
    C(org.freedesktop.timedate1) interface on the system bus.
  - Also gather the known time zones, as C(timedatectl list-timezones) prints.
notes:
  - Requires a running C(systemd-timedated) reachable on the system D-Bus, so the
    module does not work in a container or chroot without systemd.
requirements:
  - dasbus
"""

EXAMPLES = r"""
- name: Ensure the time and date settings are gathered
  linuxhq.linux.systemd_timedate_info:
  register: __systemd_timedate_query
"""

RETURN = r"""
timedate:
  description:
    - Time and date settings reported by C(systemd-timedated).
    - The C(rtc_time_usec) and C(time_usec) fields are microseconds since the
      epoch, as reported by systemd.
  returned: always
  type: dict
  sample:
    can_ntp: true
    local_rtc: false
    ntp: true
    ntp_synchronized: true
    rtc_time_usec: 1784083200000000
    time_usec: 1784083200123456
    timezone: America/Los_Angeles
timezones:
  description: Time zones known to C(systemd-timedated).
  returned: always
  type: list
  elements: str
  sample:
    - Africa/Abidjan
    - America/Los_Angeles
    - UTC
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.linux.plugins.module_utils.systemd import (
    HAS_DASBUS,
    TIMEDATE_PROPERTIES,
    systemd_properties,
    systemd_proxy,
    systemd_result,
)


def info(module):
    if module.check_mode and not HAS_DASBUS:
        module.exit_json(changed=False, timedate={}, timezones=[])

    proxy = systemd_proxy(module, "timedate1")

    timedate = systemd_properties(module, proxy, TIMEDATE_PROPERTIES)
    timezones = systemd_result(module, proxy, "ListTimezones")

    module.exit_json(changed=False, timedate=timedate, timezones=list(timezones))


def main():
    module = AnsibleModule(
        argument_spec={},
        supports_check_mode=True,
    )

    info(module)


if __name__ == "__main__":
    main()
