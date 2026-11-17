#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_timedate
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.4.0"
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
  - A O(timezone) value that is not valid UTF-8, such as one with a lone
    surrogate code point, or that contains a NUL character, is rejected
    before any setting is written, also in check mode, and so is a O(time)
    value with a lone surrogate code point in the range U+D800 to U+DC7F,
    which cannot be passed to C(systemd-analyze). A Unicode noncharacter,
    such as U+FFFE, is refused by C(systemd-analyze) in O(time), which runs
    before any setting is written, and by systemd's D-Bus library in
    O(timezone), which is sent first, so either refusal leaves nothing
    written.
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
      - C(systemd-timedated) starts or stops the service in the background, so
        after changing it the module waits up to 30 seconds for the change to
        be reported before applying O(time), and fails when it is not.
      - C(systemd-timedated) reports network time synchronization enabled
        while it starts the service, even when the service then fails to
        start, so the module waits until systemd has no job left before it
        takes the change as reported. When other jobs keep systemd busy for
        the 30 seconds, it takes the change as reported then.
    type: bool
  time:
    description:
      - System time to set, as C(timedatectl set-time) accepts.
      - The value is parsed by C(systemd-analyze timestamp) on the managed node,
        so exactly the forms that C(timedatectl set-time) accepts on that host
        are accepted, as described in
        L(systemd.time(7),https://www.freedesktop.org/software/systemd/man/latest/systemd.time.html).
      - Examples are V(now), V(today), V(@1784083200), V(+3h30min), V(-1w),
        V(5min ago), V(2026-07-26 14:30), V(Sun 2026-07-26 14:30) and
        V(2026-07-26 14:30 UTC). Newer systemd releases also accept a time
        zone name suffix, such as V(2026-07-26 14:30 Europe/Berlin), which
        systemd 252 refuses.
      - C(systemd-analyze timestamp) requires systemd 243 or later. On
        systemd 239 to 242 setting it fails with
        C(unable to parse the time specification) before any setting is
        written.
      - V(now) and relative times are resolved right before the module sets
        the clock, as C(timedatectl set-time now) does.
      - The clock is set after O(timezone) is applied. It is also set after
        O(local_rtc) and O(ntp) are applied when O(ntp) changes, or when
        O(local_rtc) changes with O(adjust_system_clock=true), which would
        otherwise reset the clock from the hardware clock, and before them
        otherwise.
      - Timestamps without a zone are read in the time zone the host ends up
        with, so one set by O(timezone) in the same task applies to them.
      - Setting the clock can never be idempotent, so this always reports a
        change. Prefer O(ntp) for keeping the clock correct.
      - C(systemd-timedated) refuses it while network time synchronization is
        enabled, so pair it with O(ntp=false) on a host that has it on. When
        another setting is written before the clock, the module fails before
        writing any setting when network time synchronization would still be
        enabled.
      - A value C(systemd-analyze) cannot parse, a time at or before the
        epoch, or a time the kernel refuses to set, at or after
        V(@8277292036), 2232-04-18 23:47:16 UTC, is rejected before any
        setting is written.
      - systemd 258 and later also refuse a time before the date systemd was
        built. Only C(systemd-timedated) knows that date, so the refusal is
        reported after the settings written before the clock are applied.
    type: str
  timezone:
    description:
      - System time zone, as a zone name from the time zone database such as
        V(America/Los_Angeles) or V(UTC).
    type: str
requirements:
  - dasbus
  - systemd-analyze from systemd >= 243, when O(time) is set
attributes:
  check_mode:
    description: Predicts changes without modifying the target.
    support: full
    details: When dasbus is unavailable, predicts changes from the supplied options without querying current state.
  diff_mode:
    description: Diff mode is not supported.
    support: none
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
  description:
    - Time and date settings reported by C(systemd-timedated).
    - In check mode, the settings that would change are predicted from the
      options, and when O(time) is set, C(time_usec) is the time it would
      set.
    - Empty when dasbus is unavailable in check mode.
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

import re
from time import monotonic, sleep

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.linux.plugins.module_utils.systemd import (
    HAS_DASBUS,
    TIMEDATE_PROPERTIES,
    check_utf8,
    systemd_call,
    systemd_properties,
    systemd_proxy,
)

MICROSECONDS = 1000000

# the kernel refuses to set the clock at or after TIME_SETTOD_SEC_MAX, KTIME_SEC_MAX less 30 years of uptime, in 2232
SETTOD_SEC_MAX = (2**63 - 1) // 1000000000 - 30 * 365 * 24 * 3600

NTP_TIMEOUT = 30

SECONDS = re.compile(r"^[ \t]*UNIX seconds: @([0-9]+)(?:\.([0-9]{6}))?[ \t]*$", re.MULTILINE)

SETTINGS = ["local_rtc", "ntp", "time", "timezone"]


def parse_time(module, analyze, value, zone):
    # parse as timedatectl set-time does, in the time zone the host ends up with;
    # SYSTEMD_COLORS from the task environment would colour the output even on a pipe
    environ = {"LC_ALL": "C", "SYSTEMD_COLORS": "0"}
    if zone:
        environ["TZ"] = f":{zone}"

    rc, stdout, stderr = module.run_command(
        [analyze, "timestamp", "--", value],
        environ_update=environ,
        expand_user_and_vars=False,
    )
    if rc != 0:
        module.fail_json(msg=f"unable to parse the time specification {value}: {stderr.strip()}")

    # the last match, as the original form echoed before it is caller input
    seconds, fraction = SECONDS.findall(stdout)[-1]
    usec = int(seconds) * MICROSECONDS + int(fraction or 0)

    if usec <= 0 or usec // MICROSECONDS >= SETTOD_SEC_MAX:
        module.fail_json(msg=f"unable to set time: invalid time {value}")

    return usec


def wait_for_ntp(module, proxy, ntp):
    # SetNTP returns once the time service job is queued, and systemd-timedated
    # refuses other requests until that job finishes and NTP reports the change.
    # While the job runs, it reports NTP enabled, whatever the job's result, so
    # NTP is read again once systemd has no job left, or at the deadline.
    deadline = monotonic() + NTP_TIMEOUT
    manager = systemd_proxy(module, "systemd1")

    while True:
        idle = systemd_properties(module, manager, [("jobs", "NJobs")])["jobs"] == 0
        reported = systemd_properties(module, proxy, [("ntp", "NTP")])["ntp"]

        if reported == ntp and (idle or monotonic() >= deadline):
            return

        if monotonic() >= deadline:
            module.fail_json(
                msg=f"unable to set ntp to {ntp}: network time synchronization did not change within {NTP_TIMEOUT} seconds"
            )

        sleep(0.5)


def check_request(module, method, current, predicted):
    """Fail when systemd-timedated would refuse the request, which matters only after an earlier request is applied."""
    if method == "SetNTP" and predicted["ntp"] and not current["can_ntp"]:
        module.fail_json(msg="unable to enable network time synchronization: no network time service is installed")

    if method == "SetTime" and predicted["ntp"]:
        module.fail_json(msg="unable to set time: network time synchronization is enabled, set ntp to false")


def ensure_present(module):
    # dasbus cannot send a surrogate and GLib cuts a string at a NUL, which would set another time zone, and
    # run_command cannot pass a surrogate that does not stand for a byte to systemd-analyze
    check_utf8(module, [("timezone", module.params["timezone"])], noncharacters=False)

    if any(0xD800 <= ord(char) <= 0xDC7F for char in module.params["time"] or ""):
        module.fail_json(msg="invalid time: it must be valid UTF-8")

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
    adjust_system_clock = module.params["adjust_system_clock"]
    if local_rtc is not None and current["local_rtc"] != local_rtc:
        predicted["local_rtc"] = local_rtc
        pending.append(("SetLocalRTC", (local_rtc, adjust_system_clock, False)))

    ntp = module.params["ntp"]
    if ntp is not None and current["ntp"] != ntp:
        predicted["ntp"] = ntp
        pending.append(("SetNTP", (ntp, False)))

    value = module.params["time"]
    if value is not None:
        analyze = module.get_bin_path("systemd-analyze", required=True)
        predicted["time_usec"] = parse_time(module, analyze, value, predicted["timezone"])

        # setting the clock before the hardware clock mode leaves that mode unwritten when systemd-timedated refuses
        # the time, and gives the same result unless SetLocalRTC adjusts the system clock from the hardware clock,
        # which would undo it; the time zone stays first, as only systemd-timedated can tell whether it is valid,
        # and NTP has to be turned off before the clock is set
        methods = [method for method, _args in pending]
        if "SetNTP" in methods or ("SetLocalRTC" in methods and adjust_system_clock):
            pending.append(("SetTime", ()))
        else:
            pending.insert(int("SetTimezone" in methods), ("SetTime", ()))

    # systemd-timedated refuses the first request before anything is written, a later one only after the earlier
    # requests are applied
    for method, _args in pending[1:]:
        check_request(module, method, current, predicted)

    if not pending:
        module.exit_json(changed=False, timedate=current)

    if module.check_mode:
        module.exit_json(changed=True, timedate=predicted)

    for method, args in pending:
        if method == "SetTime":
            # parse again so a time relative to now does not lag behind the earlier changes and the NTP wait
            args = (parse_time(module, analyze, value, predicted["timezone"]), False, False)

        systemd_call(module, proxy, method, *args)

        if method == "SetNTP":
            wait_for_ntp(module, proxy, args[0])

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
