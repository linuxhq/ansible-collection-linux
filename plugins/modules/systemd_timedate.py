# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_timedate
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.4.0
short_description: Manage the systemd time and date settings
description:
  - Manage the time zone, hardware clock and network time settings owned by
    C(systemd-timedated), the same ones C(timedatectl set-*) writes, by calling
    the C(org.freedesktop.timedate1) interface on the system bus directly.
  - Settings are compared against the current properties and only the ones that
    differ are written, options left unset are not touched.
  - With no options set the module reads the current settings and reports no
    change.
notes:
  - Requires a running C(systemd-timedated) reachable on the system D-Bus, so the
    module does not work in a container or chroot without systemd.
options:
  adjust_system_clock:
    description:
      - Update the system clock from the hardware clock when O(local_rtc)
        changes, rather than the other way around.
      - Only used when O(local_rtc) is set.
    type: bool
    default: false
  local_rtc:
    description:
      - Maintain the hardware clock in local time rather than UTC.
      - V(false) is strongly preferred, local time breaks during daylight saving
        transitions and when the machine dual boots.
    type: bool
  ntp:
    description:
      - Enable network time synchronization.
      - Enables and starts the installed network time service, such as
        C(systemd-timesyncd) or C(chronyd).
      - Enabling it fails when no such service is installed, which the C(can_ntp)
        return field reports.
    type: bool
  time:
    description:
      - System time to set, as C(timedatectl set-time) accepts.
      - Understood forms match C(systemd.time(7)), that is V(now), V(today),
        V(yesterday), V(tomorrow), V(@) followed by seconds since the epoch,
        relative spans such as V(+3h30min) or V(-1w), and timestamps such as
        V(2026-07-26 14:30:00.5), V(Sun 2026-07-26 14:30), V(26-07-26),
        V(2026-07-26), V(14:30:00) or V(14:30), each optionally suffixed with
        V(UTC).
      - Timestamps without a zone are read in the time zone the host ends up
        with, so one set by O(timezone) in the same task applies to them.
      - Setting the clock can never be idempotent, so this always reports a
        change. Prefer O(ntp) for keeping the clock correct.
      - C(systemd-timedated) refuses it while network time synchronization is
        enabled, so pair it with O(ntp=false) on a host that has it on.
    type: str
  timezone:
    description:
      - System time zone, as a zone name from the time zone database such as
        V(America/Los_Angeles) or V(UTC).
    type: str
requirements:
  - dasbus
"""

EXAMPLES = r"""
- name: Ensure the time zone is managed
  linuxhq.linux.systemd_timedate:
    timezone: America/Los_Angeles

- name: Ensure the time and date settings are managed
  linuxhq.linux.systemd_timedate:
    local_rtc: false
    ntp: true
    timezone: UTC

- name: Ensure the system clock is set on a host without network time
  linuxhq.linux.systemd_timedate:
    ntp: false
    time: '2026-07-26 14:30:00'
"""

RETURN = r"""
timedate:
  description: Time and date settings reported by C(systemd-timedated).
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
"""

import os
import re
from datetime import datetime, timedelta, timezone
from time import tzset

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.linuxhq.linux.plugins.module_utils.systemd import (
    HAS_DASBUS,
    TIMEDATE_PROPERTIES,
    systemd_call,
    systemd_properties,
    systemd_proxy,
)

MICROSECONDS = 1000000

TIMESTAMPS = [
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%y-%m-%d %H:%M:%S.%f",
    "%y-%m-%d %H:%M:%S",
    "%y-%m-%d %H:%M",
    "%y-%m-%d",
    "%H:%M:%S.%f",
    "%H:%M:%S",
    "%H:%M",
]

WEEKDAYS = [
    "mon",
    "monday",
    "tue",
    "tuesday",
    "wed",
    "wednesday",
    "thu",
    "thursday",
    "fri",
    "friday",
    "sat",
    "saturday",
    "sun",
    "sunday",
]

DAYS = {"today": 0, "tomorrow": 1, "yesterday": -1}

UNITS = [
    ("usec", 1),
    ("us", 1),
    ("\u00b5s", 1),
    ("msec", 1000),
    ("ms", 1000),
    ("seconds", MICROSECONDS),
    ("second", MICROSECONDS),
    ("sec", MICROSECONDS),
    ("s", MICROSECONDS),
    ("minutes", 60 * MICROSECONDS),
    ("minute", 60 * MICROSECONDS),
    ("min", 60 * MICROSECONDS),
    ("m", 60 * MICROSECONDS),
    ("hours", 3600 * MICROSECONDS),
    ("hour", 3600 * MICROSECONDS),
    ("hr", 3600 * MICROSECONDS),
    ("h", 3600 * MICROSECONDS),
    ("days", 86400 * MICROSECONDS),
    ("day", 86400 * MICROSECONDS),
    ("d", 86400 * MICROSECONDS),
    ("weeks", 604800 * MICROSECONDS),
    ("week", 604800 * MICROSECONDS),
    ("w", 604800 * MICROSECONDS),
    ("months", 2629800 * MICROSECONDS),
    ("month", 2629800 * MICROSECONDS),
    ("M", 2629800 * MICROSECONDS),
    ("years", 31557600 * MICROSECONDS),
    ("year", 31557600 * MICROSECONDS),
    ("y", 31557600 * MICROSECONDS),
]

SPAN = re.compile(r"\s*(\d+(?:\.\d+)?)\s*([^\W\d_]*)", re.UNICODE)

SETTINGS = ["local_rtc", "ntp", "time", "timezone"]


def current_time(utc=False):
    now = datetime.now(timezone.utc)

    return now if utc else now.astimezone()


def parse_span(value):
    total = 0.0
    position = 0

    while position < len(value):
        match = SPAN.match(value, position)
        if not match:
            return None

        amount, unit = match.group(1), match.group(2)
        factor = MICROSECONDS

        if unit:
            factor = next((scale for name, scale in UNITS if name == unit), None)
            if factor is None:
                return None

        total += float(amount) * factor
        position = match.end()

    return int(total) if position else None


def parse_stamp(value, utc):
    for stamp in TIMESTAMPS:
        layout, full = stamp, value

        if stamp.startswith("%H"):
            today = current_time(utc)
            layout, full = f"%Y-%m-%d {stamp}", f"{today:%Y-%m-%d} {value}"

        try:
            if utc:
                parsed = datetime.strptime(full, layout).replace(tzinfo=timezone.utc)
            else:
                parsed = datetime.strptime(full, layout).astimezone()
        except ValueError:
            continue

        return int(parsed.timestamp() * MICROSECONDS)

    return None


def parse_value(module, value):
    if value.startswith("@"):
        try:
            return int(float(value[1:]) * MICROSECONDS), False
        except ValueError:
            module.fail_json(msg=f"unable to parse the time specification: {value}")

    if value.startswith(("+", "-")):
        span = parse_span(value[1:])
        if span is None:
            module.fail_json(msg=f"unable to parse the time specification: {value}")

        sign = -1 if value.startswith("-") else 1

        return sign * span, True

    utc = False
    if value.upper().endswith("UTC"):
        value, utc = value[:-3].strip(), True

    if value == "now":
        return 0, True

    if value.lower() in DAYS:
        date = current_time(utc).date() + timedelta(days=DAYS[value.lower()])

        return parse_stamp(f"{date:%Y-%m-%d}", utc), False

    weekday, _dummy, remainder = value.partition(" ")
    if weekday.rstrip(",").lower() in WEEKDAYS and remainder:
        value = remainder.strip()

    usec = parse_stamp(value, utc)
    if usec is None:
        module.fail_json(msg=f"unable to parse the time specification: {value}")

    return usec, False


def parse_time(module, value, zone):
    origin = os.environ.get("TZ")

    if zone:
        os.environ["TZ"] = zone
        tzset()

    try:
        return parse_value(module, value.strip())
    finally:
        if zone:
            if origin is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = origin
            tzset()


def ensure_present(module):
    if module.check_mode and not HAS_DASBUS:
        module.exit_json(
            changed=any(module.params[param] is not None for param in SETTINGS),
            timedate={},
        )

    proxy = systemd_proxy(module, "timedate1")

    current = systemd_properties(module, proxy, TIMEDATE_PROPERTIES)
    predicted = dict(current)
    pending = []

    timezone = module.params["timezone"]
    if timezone is not None and current["timezone"] != timezone:
        predicted["timezone"] = timezone
        pending.append(("SetTimezone", (timezone, False)))

    local_rtc = module.params["local_rtc"]
    if local_rtc is not None and current["local_rtc"] != local_rtc:
        predicted["local_rtc"] = local_rtc
        pending.append(
            (
                "SetLocalRTC",
                (local_rtc, module.params["adjust_system_clock"], False),
            )
        )

    ntp = module.params["ntp"]
    if ntp is not None and current["ntp"] != ntp:
        if ntp and not current["can_ntp"]:
            module.fail_json(
                msg="unable to enable network time synchronization: "
                "no network time service is installed"
            )

        predicted["ntp"] = ntp
        pending.append(("SetNTP", (ntp, False)))

    value = module.params["time"]
    if value is not None:
        usec, relative = parse_time(module, value, predicted["timezone"])

        now = int(current_time().timestamp() * MICROSECONDS)
        predicted["time_usec"] = now + usec if relative else usec
        pending.append(("SetTime", (usec, relative, False)))

    if not pending:
        module.exit_json(changed=False, timedate=current)

    if module.check_mode:
        module.exit_json(changed=True, timedate=predicted)

    for method, args in pending:
        systemd_call(module, proxy, method, *args)

    current = systemd_properties(module, proxy, TIMEDATE_PROPERTIES)

    module.exit_json(changed=True, timedate=current)


def main():
    argument_spec = {
        "adjust_system_clock": {"type": "bool", "default": False},
        "local_rtc": {"type": "bool"},
        "ntp": {"type": "bool"},
        "time": {"type": "str"},
        "timezone": {"type": "str"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    ensure_present(module)


if __name__ == "__main__":
    main()
