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
  - Only the requested locale variables that differ from the configured ones
    are sent to C(systemd-localed), which merges them into the ones already
    configured, so a configured variable it would now refuse, such as a
    C(LANGUAGE) list written by an installer, does not block changes to the
    others.
  - When O(locale.lang) changes and O(locale.language) is not set, or is
    empty, which counts as not set, C(systemd-localed) sets C(LANGUAGE) from
    its language fallback map when the new C(LANG) is listed there exactly,
    such as V(en_AU:en_GB) for V(en_AU), replacing the configured one. The
    module reads that map from C(/usr/share/systemd/language-fallback-map),
    where systemd installs it, to predict C(LANGUAGE) in check mode. When
    the module cannot read that file, or reaches a line that
    C(systemd-localed) cannot read or split into fields, it predicts no
    fallback, as C(systemd-localed) then sets none. The lines are read as the
    running systemd version reads them. systemd 240 and later end a line at a
    line feed, a carriage return or a NUL and cannot read a line of 1 MiB or
    more, while systemd 239 ends a line only at a line feed, reads a long
    line in pieces of up to 2047 bytes and ignores the rest of a piece after
    a NUL.
  - C(systemd-localed) writes that fallback without the validation it applies
    to the requested values, so C(LANGUAGE) can become a list such as
    V(en_AU:en_GB), which O(locale.language) cannot set again where
    C(systemd-localed) refuses such a list, as described there.
  - A fallback in that map that is not valid UTF-8 or contains a Unicode
    noncharacter is written as well, after which C(systemd-localed) fails to
    report the locale. So when O(locale.lang) changes without a set
    O(locale.language) and the map lists such a fallback for it, the module
    fails before any setting is written, also in check mode when dasbus is
    available, and reads the map in a real run for that check too.
  - A set O(locale.language) is sent together with a changed O(locale.lang),
    so it is kept unless it equals the resulting C(LANG).
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
  - A locale or keyboard value that is not valid UTF-8, such as one with a
    lone surrogate code point, or that contains a NUL character, is rejected
    before any setting is written, also in check mode. So is a keyboard value
    that contains a Unicode noncharacter, such as U+FFFE, which systemd's
    D-Bus library refuses, when another request is sent before its own. The
    locale is sent first, and a value with a Unicode noncharacter in the first
    request is left to that refusal, which leaves nothing written.
  - C(systemd-localed) refuses a keyboard value with a control character,
    V("), V(') or V(\\), and on systemd 261 and later also V(*), V(?) or
    V([), and a console keymap that is not a valid file name, or on systemd
    248 and later one of 128 bytes or more. Such a value is rejected before
    any setting is written, also in check mode, when another request is sent
    before its own, and is otherwise left to that refusal, which leaves
    nothing written.
  - Only C(systemd-localed) can tell whether a console keymap is installed or
    an X11 keyboard layout compiles, so one it refuses is reported after the
    earlier settings in the same task, such as O(locale), are applied.
  - C(systemd-localed) refuses to rewrite C(/etc/vconsole.conf) when it
    contains a NUL byte or a setting that is not valid UTF-8, and on Debian 12
    likewise C(/etc/default/keyboard), where it keeps the X11 keyboard
    settings. A keyboard change whose request would rewrite such a file after
    another request is sent, or to convert the settings after writing its own
    file, then fails before any setting is written, also in check mode, as
    C(systemd-localed) only logs a refused conversion. systemd 253 and later,
    as on EL 10 and Debian 13, also only log a refused rewrite of
    C(/etc/vconsole.conf) and report the request as applied, so a keyboard
    change that rewrites that file fails this way even in the first request
    sent. Otherwise, when the first request sent would rewrite such a file as
    its own, C(systemd-localed) refuses it before anything is changed.
  - The console settings rewrite C(/etc/vconsole.conf), and so do the X11
    keyboard settings when they are converted into the console keymap and, on
    systemd 253 and later, always. On Debian 12 the X11 keyboard settings, and
    a console keymap converted into them, rewrite C(/etc/default/keyboard).
  - Reads the running systemd version from the C(Version) property of
    C(org.freedesktop.systemd1), the service manager, when it changes a
    setting. After systemd is upgraded without a reboot or
    C(systemctl daemon-reexec), the service manager still reports the earlier
    version while a restarted C(systemd-localed) runs the new one, so the
    files are then read as the earlier version reads them.
options:
  locale:
    description:
      - Locale variables of the system locale.
      - Variables left unset are not touched. C(systemd-localed) merges a partial
        request into the variables already configured and offers no way to clear
        one, so an empty value is ignored rather than unsetting the variable.
      - C(systemd-localed) also drops any variable whose value matches the
        resulting C(LANG), which is O(locale.lang) or, when that is not set, the
        configured C(LANG), so setting one to that value leaves it unset rather
        than reporting a change on every run.
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
          - C(systemd-localed) refuses a list, such as V(en_AU:en_GB), on
            systemd 256 and later, which refuse V(:) in locale values, and on
            systemd 246 and later wherever it checks that each locale is
            installed, which systemd 246 and 247 always do and systemd 248 to
            255 do unless they generate locales with C(locale-gen), such as on
            EL, where it reports the list as not installed. Only systemd 239 to
            245, and systemd 248 to 255 where C(systemd-localed) generates
            locales with C(locale-gen) instead of checking them, as on Debian
            12, accept a list.
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
    support: partial
    details:
      - When dasbus is unavailable, predicts changes from the supplied options
        without querying current state.
      - Check mode cannot predict the keyboard settings converted between the
        console keymap and the X11 keyboard settings, so the reported
        counterpart fields, including a toggle keymap cleared by that
        conversion, can differ from the ones a real run produces.
      - A different language fallback map set by
        E(SYSTEMD_LANGUAGE_FALLBACK_MAP) in the environment of
        C(systemd-localed) is not read, so the C(language) field check mode
        reports can then differ from the one a real run produces.
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
      O(locale). C(language) can be a list such as V(en_AU:en_GB), which
      C(systemd-localed) sets from its language fallback map but, as
      described for O(locale.language), can refuse through
      O(locale.language), so feeding it back then fails wherever it differs
      from the configured C(LANGUAGE).
    - In check mode, the settings that would change are predicted from the
      options.
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

import re

from ansible.module_utils import distro
from ansible.module_utils.basic import AnsibleModule

from ansible_collections.linuxhq.linux.plugins.module_utils.systemd import (
    ENV_WHITESPACE,
    HAS_DASBUS,
    LOCALE_VARIABLES,
    check_utf8,
    load_env_file,
    locale_present,
    locale_setting,
    locale_simplify,
    locale_status,
    read_bytes,
    read_map_lines,
    systemd_call,
    systemd_proxy,
    systemd_version,
    utf8_text,
)

# the first systemd-localed whose SetLocale keeps the variables a request leaves out
LOCALE_MERGE_VERSION = 239

# the first systemd-localed whose SetX11Keyboard also rewrites /etc/vconsole.conf, which then holds the X11 settings
X11_VCONSOLE_VERSION = 253

# the first systemd-localed that only logs a failure to rewrite /etc/vconsole.conf and reports the request as applied
VCONSOLE_WRITE_IGNORED_VERSION = 253

VCONSOLE_CONF = "/etc/vconsole.conf"

# systemd-localed reads its language fallback map here, a path fixed when systemd is built
LANGUAGE_FALLBACK_MAP = "/usr/share/systemd/language-fallback-map"

# Debian's systemd-localed before 253 keeps the X11 settings in this file instead of the X11 configuration
DEBIAN_KEYBOARD = "/etc/default/keyboard"

# string_is_safe() refuses control characters, quotes and backslashes in keyboard values, and from systemd 261 also
# glob characters
KEYBOARD_UNSAFE = re.compile(r"[\x01-\x1f\x7f\"'\\]")
KEYBOARD_UNSAFE_GLOB = re.compile(r"[\x01-\x1f\x7f\"'\\*?\[]")
KEYBOARD_GLOB_VERSION = 261

# keymap_is_valid() from systemd 248 refuses a console keymap of 128 bytes or more, and filename_is_valid() before it
# one longer than FILENAME_MAX
FILENAME_MAX = 4096
KEYMAP_MAX = 127
KEYMAP_MAX_VERSION = 248

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


def locale_request(requested, configured):
    """Return the requested locale variables to send, the ones that differ from the configured ones."""
    request = {name: value for name, value in requested.items() if value != configured.get(name)}

    # localed derives LANGUAGE from a sent LANG unless LANGUAGE is sent with it
    if "lang" in request and "language" in requested:
        request["language"] = requested["language"]

    return request


def map_fields(line):
    """Split a map line into fields as strv_split_full() with EXTRACT_UNQUOTE does, or return None where it fails.

    Whitespace separates fields, single and double quotes are removed, and a backslash takes the next character as it
    is. An unbalanced quote or a trailing backslash is an error.
    """
    fields = []
    field = None
    quote = None
    chars = iter(line)

    for char in chars:
        if char == "\\":
            char = next(chars, None)
            if char is None:
                return None

            field = (field or "") + char
        elif quote:
            if char == quote:
                quote = None
            else:
                field += char
        elif char in "'\"":
            quote = char
            field = field or ""
        elif char in ENV_WHITESPACE:
            if field is not None:
                fields.append(field)
                field = None
        else:
            field = (field or "") + char

    if quote:
        return None

    if field is not None:
        fields.append(field)

    return fields


def language_fallback(module, lang, version):
    """Return the LANGUAGE systemd-localed's fallback map lists for lang, or None, as find_language_fallback() does.

    systemd reads the map until the first line listing lang with exactly two fields, skipping empty lines, comments
    and lines with another number of fields, and stops without a fallback at a line it cannot read or split. The lines
    are read as the given systemd version reads them. Bytes that are not valid UTF-8 are kept as surrogates.
    """
    try:
        with open(LANGUAGE_FALLBACK_MAP, "rb") as handle:
            for line in read_map_lines(handle, version):
                if line is None:
                    return None

                line = line.strip(ENV_WHITESPACE)
                if not line or line.startswith("#"):
                    continue

                fields = map_fields(line)
                if fields is None:
                    return None

                if len(fields) == 2 and fields[0] == lang:
                    return fields[1]
    except PermissionError as error:
        # systemd-localed runs as root, so it reads a map the module may not
        module.fail_json(msg=f"unable to read {LANGUAGE_FALLBACK_MAP}: {error}")
    except OSError:
        # systemd-localed ignores a map it cannot read
        return None

    return None


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


def check_keyboard(module, settings, version):
    """Fail when systemd-localed of the given version refuses the syntax of a keyboard value it is sent.

    Whether a console keymap is installed or an X11 keyboard layout compiles is left to systemd-localed.
    """
    unsafe = KEYBOARD_UNSAFE_GLOB if version >= KEYBOARD_GLOB_VERSION else KEYBOARD_UNSAFE
    rule = "control characters, quotes, backslashes" + (
        " and glob characters" if unsafe is KEYBOARD_UNSAFE_GLOB else ""
    )

    for name, value in settings:
        if not value:
            continue

        if name in VCONSOLE_SETTINGS:
            if value in (".", "..") or "/" in value:
                module.fail_json(msg=f"invalid {name} {value!r}: it must be a valid file name")

            if len(value.encode("utf-8")) > (KEYMAP_MAX if version >= KEYMAP_MAX_VERSION else FILENAME_MAX):
                module.fail_json(msg=f"invalid {name} {value!r}: it is longer than systemd {version} allows")

        if unsafe.search(value):
            module.fail_json(msg=f"invalid {name} {value!r}: systemd {version} refuses {rule} in it")


def first_requested(module, names):
    return next(name for name in names if module.params[name] is not None)


def debian_family():
    return distro.id() == "debian" or "debian" in distro.like().split()


def keyboard_rewrites(module, version, keymap, convert_keymap, keyboard):
    """Return the environment files systemd-localed rewrites for the keyboard changes.

    Each is returned with the option causing it, the request that rewrites it, once for each such request, and
    whether systemd-localed only logs a refused rewrite and reports the request as applied, even when it is the first
    one sent: for a rewrite converting the settings after its own write, and from systemd 253 for any rewrite of
    /etc/vconsole.conf.
    """
    rewrites = []
    convert_x11 = all(module.params[name] is None for name in VCONSOLE_SETTINGS)

    if keymap is not None:
        ignored = version >= VCONSOLE_WRITE_IGNORED_VERSION
        rewrites.append((VCONSOLE_CONF, first_requested(module, VCONSOLE_SETTINGS), "SetVConsoleKeyboard", ignored))

    if keyboard is not None and (convert_x11 or version >= X11_VCONSOLE_VERSION):
        # SetX11Keyboard stores the converted console keymap there, and from systemd 253 always the X11 settings too,
        # and a refusal is only logged, for the conversion before systemd 253 and for any rewrite from then on
        rewrites.append((VCONSOLE_CONF, first_requested(module, X11_SETTINGS), "SetX11Keyboard", True))

    if (keyboard is not None or convert_keymap) and version < X11_VCONSOLE_VERSION and debian_family():
        # SetVConsoleKeyboard stores the converted X11 settings there too
        if convert_keymap:
            rewrites.append((DEBIAN_KEYBOARD, "vconsole_keymap", "SetVConsoleKeyboard", True))

        if keyboard is not None:
            rewrites.append((DEBIAN_KEYBOARD, first_requested(module, X11_SETTINGS), "SetX11Keyboard", False))

    return rewrites


def ensure_present(module):
    # dasbus cannot send a surrogate and GLib cuts a string at a NUL, which would write a shortened value
    check_utf8(
        module,
        [(f"locale.{name}", value) for name, value in sorted((module.params["locale"] or {}).items())]
        + [(name, module.params[name]) for name in VCONSOLE_SETTINGS + X11_SETTINGS],
        noncharacters=False,
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

    requests = [
        method
        for method, change in (("SetLocale", locale), ("SetVConsoleKeyboard", keymap), ("SetX11Keyboard", keyboard))
        if change is not None
    ]

    # systemd-localed refuses the first request before anything is written, but a later one only after the earlier
    # requests are applied, so a value sd-bus refuses and a file it refuses to rewrite are checked for those first, and
    # so is a file any request rewrites while only logging a refusal
    later = requests[1:]

    if "SetVConsoleKeyboard" in later:
        settings = [(name, keymap[name]) for name in VCONSOLE_SETTINGS]
        check_utf8(module, settings)
        check_keyboard(module, settings, version)

    if "SetX11Keyboard" in later:
        # a console keymap converted first replaces the X11 settings left unset, so only the requested ones are sent
        settings = [
            (name, keyboard[name]) for name in X11_SETTINGS if not convert_keymap or module.params[name] is not None
        ]
        check_utf8(module, settings)
        check_keyboard(module, settings, version)

    checked = set()

    for path, option, method, ignored in keyboard_rewrites(module, version, keymap, convert_keymap, keyboard):
        if not (ignored or method in later) or path in checked:
            continue

        checked.add(path)
        content = read_bytes(module, path)
        error = None if content is None else load_env_file(content, version)[1]

        if error:
            module.fail_json(msg=f"unable to set {option}: {path} {error}, which systemd-localed refuses to rewrite")

    if locale is not None:
        request = locale_request(locale_present(module.params["locale"]), locale_present(current["locale"]))

        # localed sets LANGUAGE from its fallback map when LANG is sent without LANGUAGE, before it merges the rest,
        # and keeps the configured one for an empty fallback; a real run reads the result back instead
        if "lang" in request and "language" not in request:
            language = language_fallback(module, request["lang"], version)

            # localed writes a fallback that is not valid UTF-8 or holds a noncharacter, then cannot report the locale
            if language and utf8_text(language) != language:
                module.fail_json(
                    msg=f"unable to set locale.lang {request['lang']}: {LANGUAGE_FALLBACK_MAP} lists invalid UTF-8 or a noncharacter, set locale.language"
                )

            if module.check_mode and language:
                locale = dict(locale, language=language)

        simplified = locale_simplify(locale)

        predicted["locale"] = {name: simplified.get(name) for name in LOCALE_VARIABLES}

        pending.append(("SetLocale", (locale_setting(request), False)))

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
