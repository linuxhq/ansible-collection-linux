# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_locale
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.4.0
short_description: Manage the systemd locale and keyboard settings
description:
  - Manage the system locale, virtual console keymap and X11 keyboard layout
    owned by C(systemd-localed), the same ones C(localectl set-*) writes, by
    calling the C(org.freedesktop.locale1) interface on the system bus directly.
  - Settings are compared against the current properties and only the ones that
    differ are written, options left unset are not touched.
  - With no options set the module reads the current settings and reports no
    change.
notes:
  - Requires a running C(systemd-localed) reachable on the system D-Bus, so the
    module does not work in a container or chroot without systemd.
  - When O(locale.lang) is written and O(locale.language) is not already
    configured, C(systemd-localed) may derive C(LANGUAGE) from its own language
    fallback map. Check mode cannot predict that value, so the reported
    C(language) field can differ from the one a real run produces.
  - C(systemd-localed) rejects a locale that is not generated on the machine, so
    generate it first with M(community.general.locale_gen).
  - The console keymap and the X11 layout are converted into each other, as
    C(localectl) does by default, so managing both O(vconsole_keymap) and the
    O(x11_layout) options with values that do not correspond leaves each run
    overwriting the other.
  - Check mode cannot predict the converted values, so the reported counterpart
    fields can differ from the ones a real run produces.
options:
  locale:
    description:
      - Locale variables written to C(/etc/locale.conf).
      - Variables left unset are not touched. C(systemd-localed) merges a partial
        request into the variables already configured and offers no way to clear
        one, so an empty value is ignored rather than unsetting the variable.
      - C(systemd-localed) also drops any variable whose value matches
        O(locale.lang), so setting one to the same value as O(locale.lang) leaves
        it unset rather than reporting a change on every run.
      - Every value must be a locale that exists on the machine, such as
        V(en_US.UTF-8) or V(C.UTF-8).
    type: dict
    suboptions:
      lang:
        description: Default locale, used for any category left unset.
        type: str
      language:
        description: Colon separated list of message translation fallbacks.
        type: str
      lc_address:
        description: Locale for postal address formatting.
        type: str
      lc_collate:
        description: Locale for string collation order.
        type: str
      lc_ctype:
        description: Locale for character classification and case conversion.
        type: str
      lc_identification:
        description: Locale for the metadata describing the locale itself.
        type: str
      lc_measurement:
        description: Locale for units of measurement.
        type: str
      lc_messages:
        description: Locale for messages and affirmative or negative answers.
        type: str
      lc_monetary:
        description: Locale for currency formatting.
        type: str
      lc_name:
        description: Locale for personal name formatting.
        type: str
      lc_numeric:
        description: Locale for number formatting.
        type: str
      lc_paper:
        description: Locale for paper size.
        type: str
      lc_telephone:
        description: Locale for telephone number formatting.
        type: str
      lc_time:
        description: Locale for date and time formatting.
        type: str
  vconsole_keymap:
    description:
      - Virtual console keymap written to C(/etc/vconsole.conf), such as V(us),
        the first argument of C(localectl set-keymap).
      - An empty string clears it.
    type: str
  vconsole_keymap_toggle:
    description:
      - Keymap toggled into by the toggle key, the optional second argument of
        C(localectl set-keymap).
      - Left unset it is cleared whenever O(vconsole_keymap) is written, which is
        what the single argument form of C(localectl set-keymap) does.
    type: str
  x11_layout:
    description:
      - X11 keyboard layout written to C(/etc/X11/xorg.conf.d), such as V(us) or
        a comma separated list such as V(us,de).
      - An empty string clears it.
    type: str
  x11_model:
    description:
      - X11 keyboard model, such as V(pc105).
      - An empty string clears it.
    type: str
  x11_options:
    description:
      - Comma separated X11 keyboard options, such as V(grp:alt_shift_toggle).
      - An empty string clears them.
    type: str
  x11_variant:
    description:
      - X11 keyboard variant, such as V(dvorak).
      - An empty string clears it.
    type: str
requirements:
  - dasbus
"""

EXAMPLES = r"""
- name: Ensure the system locale is managed
  linuxhq.linux.systemd_locale:
    locale:
      lang: en_US.UTF-8

- name: Ensure the system locale categories are managed
  linuxhq.linux.systemd_locale:
    locale:
      lang: en_US.UTF-8
      lc_time: en_DK.UTF-8

- name: Ensure the console and X11 keyboards are managed
  linuxhq.linux.systemd_locale:
    x11_layout: us
    x11_model: pc105
"""

RETURN = r"""
locale:
  description:
    - Locale and keyboard settings reported by C(systemd-localed).
    - The C(locale) field holds the locale variables, and variables that are not
      configured are returned as V(none), so it can be fed straight back into
      O(locale).
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
    LOCALE_VARIABLES,
    locale_present,
    locale_setting,
    locale_simplify,
    locale_status,
    systemd_call,
    systemd_proxy,
)

VCONSOLE_SETTINGS = ["vconsole_keymap", "vconsole_keymap_toggle"]
X11_SETTINGS = ["x11_layout", "x11_model", "x11_variant", "x11_options"]


def locale_change(module, current):
    desired = module.params["locale"]
    if desired is None:
        return None

    configured = locale_present(current["locale"])
    merged = {**configured, **locale_present(desired)}

    if locale_simplify(merged) == configured:
        return None

    return merged


def vconsole_change(module, current):
    keymap = module.params["vconsole_keymap"]
    toggle = module.params["vconsole_keymap_toggle"]

    if keymap is None and toggle is None:
        return None

    desired = {
        "vconsole_keymap": (
            current["vconsole_keymap"] or "" if keymap is None else keymap
        ),
        "vconsole_keymap_toggle": toggle or "",
    }

    if all(desired[name] == (current[name] or "") for name in VCONSOLE_SETTINGS):
        return None

    return desired


def keyboard_change(module, current, names):
    values = {name: module.params[name] for name in names}

    if all(value is None for value in values.values()):
        return None

    desired = {
        name: (current[name] or "") if value is None else value
        for name, value in values.items()
    }

    if all(desired[name] == (current[name] or "") for name in names):
        return None

    return desired


def ensure_present(module):
    if module.check_mode and not HAS_DASBUS:
        keyboard = VCONSOLE_SETTINGS + X11_SETTINGS
        requested = locale_present(module.params["locale"] or {})

        module.exit_json(
            changed=bool(requested)
            or any(module.params[param] is not None for param in keyboard),
            locale={},
        )

    proxy = systemd_proxy(module, "locale1")

    current = locale_status(module, proxy)
    predicted = dict(current)
    pending = []

    locale = locale_change(module, current)
    if locale is not None:
        simplified = locale_simplify(locale)

        predicted["locale"] = {name: simplified.get(name) for name in LOCALE_VARIABLES}
        pending.append(("SetLocale", (locale_setting(locale), False)))

    keymap = vconsole_change(module, current)
    if keymap is not None:
        predicted.update(keymap)
        pending.append(
            (
                "SetVConsoleKeyboard",
                tuple(keymap[name] for name in VCONSOLE_SETTINGS) + (True, False),
            )
        )

    keyboard = keyboard_change(module, current, X11_SETTINGS)
    if keyboard is not None:
        predicted.update(keyboard)
        pending.append(
            (
                "SetX11Keyboard",
                tuple(keyboard[name] for name in X11_SETTINGS) + (True, False),
            )
        )

    if not pending:
        module.exit_json(changed=False, locale=current)

    if module.check_mode:
        module.exit_json(changed=True, locale=predicted)

    for method, args in pending:
        systemd_call(module, proxy, method, *args)

    current = locale_status(module, proxy)

    module.exit_json(changed=True, locale=current)


def main():
    argument_spec = {
        "locale": {
            "type": "dict",
            "options": {name: {"type": "str"} for name in LOCALE_VARIABLES},
        },
        "vconsole_keymap": {"type": "str", "no_log": False},
        "vconsole_keymap_toggle": {"type": "str", "no_log": False},
        "x11_layout": {"type": "str"},
        "x11_model": {"type": "str"},
        "x11_options": {"type": "str"},
        "x11_variant": {"type": "str"},
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    ensure_present(module)


if __name__ == "__main__":
    main()
