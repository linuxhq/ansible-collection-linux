#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: systemd_locale
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.4.0"
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
  - Only the requested locale variables are sent to C(systemd-localed), which
    merges them into the ones already configured, so a configured variable it
    would now refuse, such as a C(LANGUAGE) list written by an installer, does
    not block changes to the others.
  - When O(locale.lang) is written without O(locale.language),
    C(systemd-localed) may derive C(LANGUAGE) from its own language fallback
    map. Check mode cannot predict that value, so the reported C(language)
    field can differ from the one a real run produces.
  - On EL, C(systemd-localed) rejects a locale that is not installed on the
    machine, so install it first. On Debian, it enables a missing locale in
    C(/etc/locale.gen) and runs C(locale-gen) before it returns, which can take
    a while when many locales are enabled.
  - C(systemd-localed) chooses the files it writes. On EL 9 and 10 and Debian
    13 it writes O(locale) to C(/etc/locale.conf), O(vconsole_keymap) to
    C(/etc/vconsole.conf) and the X11 keyboard settings to
    C(/etc/X11/xorg.conf.d/00-keyboard.conf). Debian 12 writes O(locale) to
    C(/etc/default/locale) unless C(/etc/locale.conf) exists, and the X11
    keyboard settings to C(/etc/default/keyboard).
  - systemd 253 and later, as on EL 10 and Debian 13, also store the X11
    keyboard settings in C(/etc/vconsole.conf) and report them from there,
    and C(systemd-localed) ignores a failure to write
    C(/etc/X11/xorg.conf.d/00-keyboard.conf). Debian 13 makes that directory
    read-only for C(systemd-localed) when it exists as C(systemd-localed)
    starts, so the file keeps the earlier settings while the new ones are
    reported as applied. Clearing all of the X11 keyboard settings is not kept
    either, as C(systemd-localed) reports the settings in that file again once
    it restarts, as it does after exiting when idle, so such a task reports a
    change again on each run after C(systemd-localed) restarts. On
    Debian 13, C(/etc/vconsole.conf) is at first a link to
    C(/etc/default/keyboard), which C(systemd-localed) replaces with a file of
    its own, leaving C(/etc/default/keyboard) unchanged.
  - A console keymap that changes is converted into the X11 keyboard settings,
    as C(localectl set-keymap) does by default, and the C(x11_*) options that
    are set are then applied over the converted values without converting them
    back, so O(vconsole_keymap) and O(x11_layout) can be managed together with
    values that do not correspond. When only the toggle keymap changes, the
    console settings are written without that conversion, so the X11 keyboard
    settings are left as they are.
  - When only C(x11_*) options are set, the X11 keyboard settings are converted
    into the console keymap, as C(localectl set-x11-keymap) does by default.
    That conversion also clears the console toggle keymap, as
    C(localectl set-x11-keymap) does. On systemd 252, as on EL 9 and Debian 12,
    it clears the toggle keymap only when the converted console keymap differs
    from the current one. On systemd 253 and later, as on EL 10 and Debian 13,
    it clears the toggle keymap even when the console keymap stays the same.
  - Check mode cannot predict the converted values, so the reported counterpart
    fields, including a toggle keymap cleared by that conversion, can differ
    from the ones a real run produces.
  - A locale or keyboard value that is not valid UTF-8, such as one with a
    lone surrogate code point, or that contains a NUL character or a Unicode
    noncharacter, such as U+FFFE, is rejected before any setting is written,
    also in check mode.
  - Only C(systemd-localed) can tell whether a console keymap or an X11 layout
    exists, so one it refuses is reported after the earlier settings in the
    same task, such as O(locale), are applied.
  - C(systemd-localed) refuses to rewrite C(/etc/vconsole.conf) when it
    contains a NUL byte or a setting that is not valid UTF-8, and on Debian 12
    likewise C(/etc/default/keyboard), where it keeps the X11 keyboard
    settings. A keyboard change that would rewrite such a file then fails
    before any setting is written, also in check mode.
  - The console settings rewrite C(/etc/vconsole.conf), and so do the X11
    keyboard settings when they are converted into the console keymap and, on
    systemd 253 and later, always. On Debian 12 the X11 keyboard settings, and
    a console keymap converted into them, rewrite C(/etc/default/keyboard).
  - Reads the running systemd version from the C(Version) property of
    C(org.freedesktop.systemd1) when it changes a setting.
options:
  locale:
    description:
      - Locale variables of the system locale.
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
        description:
          - Colon separated list of message translation fallbacks.
          - systemd 256 and later refuse V(:) in locale values, so only a single
            locale is accepted there.
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
      - Virtual console keymap, such as V(us), the first argument of
        C(localectl set-keymap).
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
      - X11 keyboard layout, such as V(us) or a comma separated list such as
        V(us,de).
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
  - systemd >= 239, the first version whose C(systemd-localed) merges a partial
    locale request into the configured variables instead of clearing the rest;
    the module fails before writing any setting when O(locale) would change
    the locale on an older systemd
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
    - In check mode, the settings that would change are predicted from the
      options.
    - Empty when dasbus is unavailable in check mode.
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

from ansible.module_utils import distro
from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.linux.plugins.module_utils.systemd import (
    HAS_DASBUS,
    LOCALE_VARIABLES,
    check_utf8,
    load_env_file,
    locale_present,
    locale_setting,
    locale_simplify,
    locale_status,
    read_bytes,
    systemd_call,
    systemd_proxy,
    systemd_version,
)

# the first systemd-localed whose SetLocale keeps the variables a request leaves out
LOCALE_MERGE_VERSION = 239

# the first systemd-localed whose SetX11Keyboard also rewrites /etc/vconsole.conf, which then holds the X11 settings
X11_VCONSOLE_VERSION = 253

VCONSOLE_CONF = "/etc/vconsole.conf"

# Debian's systemd-localed before 253 keeps the X11 settings in this file instead of the X11 configuration
DEBIAN_KEYBOARD = "/etc/default/keyboard"

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
        "vconsole_keymap": (current["vconsole_keymap"] or "" if keymap is None else keymap),
        "vconsole_keymap_toggle": toggle or "",
    }

    if all(desired[name] == (current[name] or "") for name in VCONSOLE_SETTINGS):
        return None

    return desired


def keyboard_change(module, current, names):
    values = {name: module.params[name] for name in names}

    if all(value is None for value in values.values()):
        return None

    desired = {name: (current[name] or "") if value is None else value for name, value in values.items()}

    if all(desired[name] == (current[name] or "") for name in names):
        return None

    return desired


def first_requested(module, names):
    return next(name for name in names if module.params[name] is not None)


def debian_family():
    return distro.id() == "debian" or "debian" in distro.like().split()


def keyboard_rewrites(module, version, keymap, convert_keymap, keyboard):
    """Return the environment files systemd-localed rewrites for the keyboard changes, with the option causing it."""
    rewrites = []
    convert_x11 = all(module.params[name] is None for name in VCONSOLE_SETTINGS)

    if keymap is not None:
        rewrites.append((VCONSOLE_CONF, first_requested(module, VCONSOLE_SETTINGS)))
    elif keyboard is not None and (convert_x11 or version >= X11_VCONSOLE_VERSION):
        # SetX11Keyboard stores the converted console keymap there, and from systemd 253 always the X11 settings too
        rewrites.append((VCONSOLE_CONF, first_requested(module, X11_SETTINGS)))

    if (keyboard is not None or convert_keymap) and version < X11_VCONSOLE_VERSION and debian_family():
        # SetVConsoleKeyboard stores the converted X11 settings there too
        option = first_requested(module, X11_SETTINGS) if keyboard is not None else "vconsole_keymap"
        rewrites.append((DEBIAN_KEYBOARD, option))

    return rewrites


def ensure_present(module):
    # a value that cannot be sent would otherwise fail only after the earlier settings are written
    check_utf8(
        module,
        [(f"locale.{name}", value) for name, value in sorted((module.params["locale"] or {}).items())]
        + [(name, module.params[name]) for name in VCONSOLE_SETTINGS + X11_SETTINGS],
    )

    if module.check_mode and not HAS_DASBUS:
        keyboard = VCONSOLE_SETTINGS + X11_SETTINGS
        requested = locale_present(module.params["locale"] or {})

        module.exit_json(
            changed=bool(requested) or any(module.params[param] is not None for param in keyboard),
            locale={},
        )

    proxy = systemd_proxy(module, "locale1")

    current = locale_status(module, proxy)
    predicted = dict(current)
    pending = []

    locale = locale_change(module, current)
    keymap = vconsole_change(module, current)
    keyboard = keyboard_change(module, current, X11_SETTINGS)

    # localed converts even an unchanged keymap, which would replace X11 settings a toggle change leaves alone
    convert_keymap = keymap is not None and keymap["vconsole_keymap"] != (current["vconsole_keymap"] or "")

    version = None
    if locale is not None or keymap is not None or keyboard is not None:
        version = systemd_version(module)

    if locale is not None and version < LOCALE_MERGE_VERSION:
        module.fail_json(msg=f"unable to set locale: systemd >= {LOCALE_MERGE_VERSION} is required, found {version}")

    # localed refuses to rewrite such a file only after the earlier settings are written, so check it first
    for path, option in keyboard_rewrites(module, version, keymap, convert_keymap, keyboard):
        content = read_bytes(module, path)
        error = None if content is None else load_env_file(content, version)[1]

        if error:
            module.fail_json(msg=f"unable to set {option}: {path} {error}, which systemd-localed refuses to rewrite")

    if locale is not None:
        simplified = locale_simplify(locale)

        predicted["locale"] = {name: simplified.get(name) for name in LOCALE_VARIABLES}
        pending.append(("SetLocale", (locale_setting(locale_present(module.params["locale"])), False)))

    if keymap is not None:
        predicted.update(keymap)
        pending.append(
            (
                "SetVConsoleKeyboard",
                tuple(keymap[name] for name in VCONSOLE_SETTINGS) + (convert_keymap, False),
            )
        )

    if keyboard is not None:
        predicted.update(keyboard)

    if not pending and keyboard is None:
        module.exit_json(changed=False, locale=current)

    if module.check_mode:
        module.exit_json(changed=True, locale=predicted)

    for method, args in pending:
        systemd_call(module, proxy, method, *args)

    if convert_keymap and any(module.params[name] is not None for name in X11_SETTINGS):
        # SetVConsoleKeyboard converts the keymap into the X11 settings, so compare against those
        keyboard = keyboard_change(module, locale_status(module, proxy), X11_SETTINGS)

    if keyboard is not None:
        # Converting back would replace the requested console settings and can drop the toggle keymap
        convert = all(module.params[name] is None for name in VCONSOLE_SETTINGS)

        systemd_call(module, proxy, "SetX11Keyboard", *(keyboard[name] for name in X11_SETTINGS), convert, False)

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
