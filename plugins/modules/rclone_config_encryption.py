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
options:
  content:
    description:
      - Configuration body to write, most often rendered with the
        P(ansible.builtin.template#lookup) lookup.
      - When set, the file is created if it does not exist, and an existing file
        that cannot be opened with O(password), because the password differs or
        the encrypted content is damaged, is replaced rather than failing, which
        is what makes a password rotation a single run.
      - Treated as a secret and kept out of logs, like O(password).
      - When omitted, the file must already exist and only its encryption state
        is managed, and a file that cannot be opened with O(password) fails.
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
    type: str
  path:
    description:
      - Path to the rclone configuration file to manage.
      - Must already exist unless O(content) is set.
    type: path
    required: true
  state:
    description:
      - V(present) writes the configuration encrypted.
      - V(absent) writes the configuration decrypted.
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
    details: Reports a potential change without inspecting the configuration when pycryptodome is unavailable.
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
  description: Path to the managed configuration file.
  returned: always
  type: str
  sample: /root/.config/rclone/rclone.conf
"""

import os
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


def read_config(module, path):
    if not os.path.exists(path):
        return None, None

    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except OSError as error:
        module.fail_json(msg=f"unable to read {path}: {to_native(error)}")

    return raw, to_text(raw, errors="replace")


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
            handle, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".")

            with os.fdopen(handle, "wb") as stream:
                stream.write(to_bytes(content))
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as error:
            module.fail_json(msg=f"unable to write {path}: {to_native(error)}")

        umask = os.umask(CONFIG_UMASK) if creating else None
        try:
            module.atomic_move(tmp, path, unsafe_writes=module.params["unsafe_writes"])
        finally:
            if umask is not None:
                os.umask(umask)
    finally:
        if tmp is not None:
            discard_file(tmp)


def current_config(module, path, raw, text):
    if text is None:
        return False, None

    try:
        encrypted = is_encrypted(text)
    except ValueError as error:
        module.fail_json(msg=f"unable to read configuration file {path}: {to_native(error)}")

    if not encrypted:
        return False, raw

    if module.params["password"] is None:
        return True, None

    try:
        return True, decrypt_config(text, module.params["password"])
    except ValueError:
        return True, None


def config_diff(module, before, after):
    if not module._diff:
        return {}

    return {
        "diff": {"before": to_text(before or b"", errors="replace"), "after": to_text(after or b"", errors="replace")}
    }


def ensure_present(module, path):
    raw, text = read_config(module, path)
    encrypted, current = current_config(module, path, raw, text)
    desired = module.params["content"]

    if desired is None:
        if encrypted and current is None:
            module.fail_json(
                msg=f"configuration file {path} is already encrypted with a different password or is damaged"
            )

        desired = current
    else:
        desired = to_bytes(desired)

    changed = not encrypted or current != desired

    if changed and not module.check_mode:
        write_config(module, path, encrypt_config(desired, module.params["password"]))

    diff = config_diff(module, current, desired)

    changed = module.set_fs_attributes_if_different(module.load_file_common_arguments(module.params, path), changed)

    module.exit_json(changed=changed, encrypted=True, path=module.params["path"], **diff)


def ensure_absent(module, path):
    raw, text = read_config(module, path)
    encrypted, current = current_config(module, path, raw, text)
    desired = module.params["content"]

    if desired is None:
        if encrypted and current is None:
            module.fail_json(
                msg=f"unable to decrypt configuration file {path}, wrong or missing password or damaged content"
            )

        desired = current
    else:
        desired = to_bytes(desired)

    changed = encrypted or current != desired

    if changed and not module.check_mode:
        write_config(module, path, desired)

    diff = config_diff(module, current, desired)

    changed = module.set_fs_attributes_if_different(module.load_file_common_arguments(module.params, path), changed)

    module.exit_json(changed=changed, encrypted=False, path=module.params["path"], **diff)


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
    path = os.path.realpath(module.params["path"])

    if password is not None:
        try:
            check_config_password(password)
        except ValueError as error:
            module.fail_json(msg=f"invalid password for configuration file {path}: {to_native(error)}")

    if module.params["content"] is None and not os.path.exists(path):
        module.fail_json(msg=f"configuration file does not exist: {path}")

    if not HAS_PYCRYPTODOME:
        if module.check_mode:
            module.exit_json(
                changed=True,
                encrypted=module.params["state"] == "present",
                path=module.params["path"],
            )

        module.fail_json(msg=missing_required_lib("pycryptodome"))

    if module.params["state"] == "present":
        ensure_present(module, path)

    ensure_absent(module, path)


if __name__ == "__main__":
    main()
