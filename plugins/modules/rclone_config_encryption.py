#!/usr/bin/python
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: rclone_config_encryption
author:
  - Taylor Kimball (@tkimball83)
version_added: "2.3.0"
short_description: Manage rclone configuration file encryption
description:
  - Write an rclone configuration file, encrypted or decrypted, using the same
    C(RCLONE_ENCRYPT_V0) envelope that C(rclone config encryption set) writes.
  - The configuration key is the SHA256 digest of the NFKC normalized password,
    and the body is sealed with XSalsa20-Poly1305, so rclone reads back what this
    module writes and the module reads back what rclone writes.
  - An encrypted payload with base64 padding before its end is treated as
    damaged, although rclone may accept it where the padding falls on one of
    its internal read boundaries.
  - Supply O(content) to manage the configuration body as well as its encryption,
    which keeps the plaintext off disk entirely. Omit it to encrypt or decrypt a
    file that is already in place.
  - The module is idempotent. It compares the decrypted configuration against the
    desired one and rewrites nothing when they match, so the ciphertext does not
    churn on repeated runs.
  - Neither the password nor the decrypted configuration is ever placed on a
    command line, and the password is never returned. The decrypted
    configuration is returned only in the diff, when diff mode is enabled.
  - A symbolic link at O(path) is followed and its target is written, as rclone
    does.
  - A file the module creates is given mode C(0600), as rclone does, unless
    O(mode) is set. It is created with that mode, so it is never readable by
    other users, even before O(mode) is applied. An existing file keeps its
    mode.
  - An O(owner) or O(group) that cannot be looked up and an O(mode) that is
    neither octal nor symbolic fail before anything is written. An SELinux
    context or O(attributes) value the system refuses fails only after the
    file is written.
options:
  content:
    description:
      - Configuration body to write, most often rendered with the
        P(ansible.builtin.template#lookup) lookup.
      - When set, the file is created if it does not exist, and an existing file
        that cannot be opened with O(password), because the password differs or
        the encrypted payload is damaged, is replaced rather than failing, which
        is what makes a password rotation a single run. A file with an
        unsupported or damaged encryption header line fails instead, as
        described below.
      - Treated as a secret and kept out of logs, like O(password).
      - Content containing a lone surrogate code point, such as U+D800, which a
        JSON value can carry, is rejected before anything is read or written
        because it is not valid UTF-8. U+DC80 to U+DCFF, which Ansible uses for
        bytes that are not valid UTF-8, are written as those bytes.
      - When omitted, the file must already exist and only its encryption state
        is managed, and a file that cannot be opened with O(password) fails.
      - A file whose first line other than blank and comment lines, trimmed
        of whitespace, starts with C(RCLONE_ENCRYPT_V) fails before anything is
        written, even when O(content) is set, unless that line, trimmed of
        whitespace, is exactly C(RCLONE_ENCRYPT_V0:). Whitespace here is the
        set of Unicode space characters rclone trims, as for O(password). This
        covers a version this module does not support, such as
        C(RCLONE_ENCRYPT_V1:), and a damaged C(RCLONE_ENCRYPT_V0:) line with
        the payload on it, which rclone refuses as well. Like rclone, the
        module reads lines in pieces of up to 4096 bytes, so a longer line
        counts as several.
    type: str
  password:
    description:
      - Password securing the configuration file.
      - Required when O(state=present), which needs it to encrypt.
      - Optional when O(state=absent). Without O(content), it is needed to open
        a file that is currently encrypted. With O(content), an encrypted file is
        replaced by O(content) even without it, and it is only used to read the
        current configuration for the comparison and the diff.
      - Whitespace is significant and is not stripped, matching rclone. A password
        that is empty or entirely whitespace is rejected, where whitespace is the
        set of Unicode space characters rclone trims.
      - A password containing a lone surrogate code point, such as U+D800,
        which a JSON value can carry, is rejected because it is not valid UTF-8,
        as rclone requires.
      - The password is NFKC normalized with the Unicode tables of the Python
        on the managed node, which can be older than the ones rclone is built
        with. A password containing a character that is unassigned in those
        tables is rejected, because rclone may normalize it differently.
        Unicode noncharacters, such as U+FFFF, are permanently unassigned and
        are accepted. A character that this Python normalizes but an older
        rclone build does not cannot be detected.
      - A password whose compatibility decomposition has a run of more than 30
        consecutive combining characters, marks or Hangul jamo is rejected,
        because rclone inserts U+034F into such a run while normalizing and
        this Python does not. Every mark, every Hangul jamo and every other
        character that combines with the one before it, such as U+16D67, is
        counted, including marks that rclone may not count, so some such
        passwords that rclone could open are rejected as well.
    type: str
  path:
    description:
      - Path to the rclone configuration file to manage.
      - Must already exist unless O(content) is set.
      - A path with a NUL character or a lone surrogate code point other than
        U+DC80 to U+DCFF is rejected before any file is read or written,
        because it cannot name a file. U+DC80 to U+DCFF, which Ansible uses
        for bytes that are not valid UTF-8, stand for those bytes.
      - Unless the task sets C(no_log), Ansible fails before the module runs
        for a path with any lone surrogate code point, because it logs the
        arguments as UTF-8. ansible-core 2.18 also returns the arguments with
        the result, which then fails as not valid UTF-8 after the module has
        run. Lone surrogates in the returned RV(path) and in failure messages
        are backslash escaped, such as C(\udcff).
    type: path
    required: true
  state:
    description:
      - V(present) writes the configuration encrypted.
      - V(absent) writes the configuration decrypted. When the plain text to
        be written, O(content) or the decrypted configuration, begins with an
        rclone encryption header such as C(RCLONE_ENCRYPT_V0:), after any blank
        or comment lines, the module fails before writing anything, because
        rclone would not read it as the plain text written. It reads it as
        encrypted, or refuses an unsupported or damaged header. The lines are
        read as described for O(content), trimmed of whitespace and in pieces
        of up to 4096 bytes.
    type: str
    choices:
      - absent
      - present
    default: present
extends_documentation_fragment:
  - ansible.builtin.files
requirements:
  - pycryptodome >= 3.7.0 or pycryptodomex >= 3.7.0
attributes:
  check_mode:
    description: Predicts changes without modifying the target.
    support: full
    details: >-
      Reports a potential change without inspecting the configuration when
      neither pycryptodome nor pycryptodomex is available.
  diff_mode:
    description: Returns the decrypted configuration before and after the change.
    support: full
    details:
      - The diff holds the decrypted configuration, so use C(no_log) or disable
        diff mode on the task when it must stay out of logs.
      - Because O(content) is kept out of logs, Ansible replaces it with a
        placeholder wherever it appears in the result, so when O(content) is
        set the after side of the diff shows that placeholder rather than the
        new configuration.
      - The exception is O(content) containing U+DC80 to U+DCFF, which Ansible
        uses for bytes that are not valid UTF-8. The diff shows those bytes as
        U+FFFD, so it no longer matches O(content), and the after side shows
        the full new configuration.
"""

EXAMPLES = r"""
- name: Ensure rclone configuration is managed and encrypted
  linuxhq.linux.rclone_config_encryption:
    content: "{{ lookup('ansible.builtin.template', 'rclone.conf.j2') }}"
    password: "{{ rclone_config_pass }}"
    path: /root/.config/rclone/rclone.conf
    state: present
    group: root
    mode: '0600'
    owner: root

- name: Ensure an existing rclone configuration is encrypted
  linuxhq.linux.rclone_config_encryption:
    password: "{{ rclone_config_pass }}"
    path: /root/.config/rclone/rclone.conf
    state: present

- name: Ensure rclone configuration is decrypted
  linuxhq.linux.rclone_config_encryption:
    password: "{{ rclone_config_pass }}"
    path: /root/.config/rclone/rclone.conf
    state: absent
"""

RETURN = r"""
encrypted:
  description: Whether the configuration file is encrypted after the run.
  returned: always
  type: bool
  sample: true
path:
  description:
    - Path to the managed configuration file.
    - Lone surrogate code points, such as U+DC80 to U+DCFF, which stand for
      bytes that are not valid UTF-8, are backslash escaped, such as
      C(\udcff), so the result is valid UTF-8.
  returned: always
  type: str
  sample: /root/.config/rclone/rclone.conf
"""

import grp
import os
import pwd
import stat
import tempfile

from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from ansible.module_utils.common.text.converters import to_bytes, to_native, to_text

from ansible_collections.linuxhq.linux.plugins.module_utils.rclone import (
    HAS_PYCRYPTODOME,
    check_config_password,
    decrypt_config,
    encrypt_config,
    is_encrypted,
)

CONFIG_UMASK = 0o077

# a regular file of mode 0600, against which a symbolic mode is checked before the configuration file is written
SAMPLE_STAT = os.stat_result((stat.S_IFREG | 0o600, 0, 0, 0, 0, 0, 0, 0, 0, 0))


def label(text):
    """Return text with lone surrogates and NUL backslash escaped, for messages and results that must be UTF-8."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8").replace("\x00", "\\x00")


def read_config(module, path):
    if not os.path.exists(path):
        return None

    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as error:
        module.fail_json(msg=f"unable to read {label(path)}: {label(to_native(error))}")

    return raw


def discard_file(path):
    if not os.path.exists(path):
        return

    if hasattr(os, "chflags"):
        try:
            os.chflags(path, 0)
        except OSError:
            pass

    try:
        os.remove(path)
    except OSError:
        pass


def write_config(module, path, content):
    creating = not os.path.exists(path)
    tmp = None

    try:
        try:
            try:
                handle, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".")
            except OSError:
                if not module.params["unsafe_writes"]:
                    raise

                # atomic_move falls back to writing the file in place when it cannot create a file beside it
                handle, tmp = tempfile.mkstemp(dir=module.tmpdir)

            with os.fdopen(handle, "wb") as stream:
                stream.write(to_bytes(content))
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            module.fail_json(msg=f"unable to write {label(path)}: {label(to_native(error))}")

        umask = os.umask(CONFIG_UMASK) if creating else None
        try:
            module.atomic_move(tmp, path, unsafe_writes=module.params["unsafe_writes"])
        finally:
            if umask is not None:
                os.umask(umask)
    finally:
        if tmp is not None:
            discard_file(tmp)


def current_config(module, path, raw):
    if raw is None:
        return False, None

    try:
        encrypted = is_encrypted(raw)
    except ValueError as error:
        module.fail_json(msg=f"unable to read configuration file {label(path)}: {to_native(error)}")

    if not encrypted:
        return False, raw

    if module.params["password"] is None:
        return True, None

    try:
        return True, decrypt_config(raw, module.params["password"])
    except ValueError:
        return True, None


def config_diff(module, before, after):
    if not module._diff:
        return {}

    return {
        "diff": {"before": to_text(before or b"", errors="replace"), "after": to_text(after or b"", errors="replace")}
    }


def check_plain_text(module, path, plain):
    try:
        readable = not is_encrypted(plain)
    except ValueError:
        readable = False

    if not readable:
        module.fail_json(
            msg=f"plain text for configuration file {label(path)} begins with an rclone encryption header, so rclone would not read it as plain text"
        )


def check_path(module, path):
    """Fail before any file access for a path that cannot name a file, which os functions refuse with a traceback."""
    if "\x00" in path:
        module.fail_json(
            msg=f"invalid path {label(path)}: it contains a NUL character, which a file path cannot contain"
        )

    # U+DC80 to U+DCFF stand for the bytes that are not valid UTF-8, but another lone surrogate stands for none
    try:
        path.encode("utf-8", "surrogateescape")
    except UnicodeEncodeError as error:
        module.fail_json(
            msg=f"invalid path {label(path)}: U+{ord(path[error.start]):04X} is a lone surrogate that stands for no byte, unlike U+DC80 to U+DCFF"
        )


def check_file_attributes(module, path):
    """Fail before writing for an owner, group or mode that Ansible refuses only after the file is written."""
    owner = module.params["owner"]
    group = module.params["group"]
    mode = module.params["mode"]

    # Ansible takes a value that int() accepts as an ID and looks up any other as a name, as checked here
    if owner is not None:
        try:
            int(owner)
        except ValueError:
            try:
                pwd.getpwnam(owner)
            except (KeyError, ValueError):
                module.fail_json(
                    msg=f"unable to manage configuration file {label(path)}: failed to look up user {label(owner)}"
                )

    if group is not None:
        try:
            int(group)
        except ValueError:
            try:
                grp.getgrnam(group)
            except (KeyError, ValueError):
                module.fail_json(
                    msg=f"unable to manage configuration file {label(path)}: failed to look up group {label(group)}"
                )

    if mode is None or isinstance(mode, int):
        return

    try:
        int(mode, 8)
    except (TypeError, ValueError):
        try:
            module._symbolic_mode_to_octal(SAMPLE_STAT, mode)
        except (AttributeError, TypeError, ValueError):
            module.fail_json(
                msg=f"unable to manage configuration file {label(path)}: mode {label(str(mode))} must be in octal or symbolic form"
            )


def ensure_present(module, path):
    raw = read_config(module, path)
    encrypted, current = current_config(module, path, raw)
    desired = module.params["content"]

    if desired is None:
        if encrypted and current is None:
            module.fail_json(
                msg=f"configuration file {label(path)} is already encrypted with a different password or its encrypted payload is damaged"
            )

        desired = current
    else:
        desired = to_bytes(desired)

    changed = not encrypted or current != desired

    if changed and not module.check_mode:
        write_config(module, path, encrypt_config(desired, module.params["password"]))

    diff = config_diff(module, current, desired)

    changed = module.set_fs_attributes_if_different(module.load_file_common_arguments(module.params, path), changed)

    module.exit_json(changed=changed, encrypted=True, path=label(module.params["path"]), **diff)


def ensure_absent(module, path):
    raw = read_config(module, path)
    encrypted, current = current_config(module, path, raw)
    desired = module.params["content"]

    if desired is None:
        if encrypted and current is None:
            module.fail_json(
                msg=f"unable to decrypt configuration file {label(path)}, wrong or missing password or damaged encrypted payload"
            )

        desired = current

        check_plain_text(module, path, desired)
    else:
        desired = to_bytes(desired)

    changed = encrypted or current != desired

    if changed and not module.check_mode:
        write_config(module, path, desired)

    diff = config_diff(module, current, desired)

    changed = module.set_fs_attributes_if_different(module.load_file_common_arguments(module.params, path), changed)

    module.exit_json(changed=changed, encrypted=False, path=label(module.params["path"]), **diff)


def main():
    argument_spec = {
        "content": {"type": "str", "no_log": True},
        "password": {"type": "str", "no_log": True},
        "path": {"type": "path", "required": True},
        "state": {
            "type": "str",
            "choices": ["absent", "present"],
            "default": "present",
        },
    }

    module = AnsibleModule(
        argument_spec=argument_spec,
        add_file_common_args=True,
        required_if=[("state", "present", ("password",))],
        supports_check_mode=True,
    )

    password = module.params["password"]
    check_path(module, module.params["path"])
    path = os.path.realpath(module.params["path"])
    check_file_attributes(module, path)

    if password is not None:
        try:
            check_config_password(password)
        except ValueError as error:
            module.fail_json(msg=f"invalid password for configuration file {label(path)}: {to_native(error)}")

    if module.params["content"] is not None:
        # a lone surrogate, which a JSON value can carry, cannot be written; U+DC80 to U+DCFF stand for raw bytes
        try:
            to_bytes(module.params["content"], errors="surrogate_or_strict")
        except UnicodeEncodeError as error:
            code = ord(error.object[error.start])
            module.fail_json(
                msg=f"invalid content for configuration file {label(path)}: character U+{code:04X} is a surrogate, which is not valid UTF-8"
            )

        if module.params["state"] == "absent":
            check_plain_text(module, path, module.params["content"])

    if module.params["content"] is None and not os.path.exists(path):
        module.fail_json(msg=f"configuration file does not exist: {label(path)}")

    if not HAS_PYCRYPTODOME:
        if module.check_mode:
            module.exit_json(
                changed=True,
                encrypted=module.params["state"] == "present",
                path=label(module.params["path"]),
            )

        library = missing_required_lib("pycryptodome or pycryptodomex")
        module.fail_json(msg=f"unable to manage configuration file {label(path)}: {library}")

    if module.params["state"] == "present":
        ensure_present(module, path)

    ensure_absent(module, path)


if __name__ == "__main__":
    main()
