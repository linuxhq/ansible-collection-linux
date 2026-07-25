# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = r"""
---
module: rclone_config_encryption
author:
  - Taylor Kimball (@tkimball83)
version_added: 2.3.0
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
    command line or returned to the controller.
options:
  content:
    description:
      - Configuration body to write, most often rendered with the
        P(ansible.builtin.template#lookup) lookup.
      - When set, the file is created if it does not exist, and an existing file
        that cannot be opened with O(password) is replaced rather than failing,
        which is what makes a password rotation a single run.
      - When omitted, the file must already exist and only its encryption state
        is managed.
    type: str
  password:
    description:
      - Password securing the configuration file.
      - Required when O(state=present), which needs it to encrypt.
      - Optional when O(state=absent), where it is only needed to open a file that
        is currently encrypted. It can be omitted when O(content) is set and the
        file on disk is already plaintext.
      - Whitespace is significant and is not stripped, matching rclone. A password
        that is empty or entirely whitespace is rejected.
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
  - pycryptodome or pycryptodomex
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
    decrypt_config,
    encrypt_config,
    is_encrypted,
)


def read_config(module):
    path = module.params["path"]

    if not os.path.exists(path):
        if module.params["content"] is None:
            module.fail_json(msg=f"configuration file does not exist: {path}")

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


def write_config(module, content):
    path = module.params["path"]
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

        module.atomic_move(tmp, path)
    finally:
        if tmp is not None:
            discard_file(tmp)


def current_config(module, raw, text):
    if text is None:
        return False, None

    try:
        encrypted = is_encrypted(text)
    except ValueError as error:
        module.fail_json(msg=to_native(error))

    if not encrypted:
        return False, raw

    if module.params["password"] is None:
        return True, None

    return True, decrypt_config(text, module.params["password"])


def config_diff(module, before, after):
    if not module._diff:
        return {}

    return {"diff": {"before": to_text(before or b""), "after": to_text(after or b"")}}


def ensure_present(module):
    raw, text = read_config(module)
    encrypted, current = current_config(module, raw, text)
    desired = module.params["content"]

    if desired is None:
        if encrypted and current is None:
            module.fail_json(
                msg="configuration file is already encrypted with a different password"
            )
        desired = current
    else:
        desired = to_bytes(desired)

    changed = not encrypted or current != desired

    if changed and not module.check_mode:
        write_config(module, encrypt_config(desired, module.params["password"]))

    diff = config_diff(module, current, desired)

    changed = module.set_fs_attributes_if_different(
        module.load_file_common_arguments(module.params), changed
    )

    module.exit_json(
        changed=changed, encrypted=True, path=module.params["path"], **diff
    )


def ensure_absent(module):
    raw, text = read_config(module)
    encrypted, current = current_config(module, raw, text)
    desired = module.params["content"]

    if desired is None:
        if encrypted and current is None:
            module.fail_json(
                msg="unable to decrypt configuration file, wrong or missing password"
            )
        desired = current
    else:
        desired = to_bytes(desired)

    changed = encrypted or current != desired

    if changed and not module.check_mode:
        write_config(module, desired)

    diff = config_diff(module, current, desired)

    changed = module.set_fs_attributes_if_different(
        module.load_file_common_arguments(module.params), changed
    )

    module.exit_json(
        changed=changed, encrypted=False, path=module.params["path"], **diff
    )


def main():
    argument_spec = {
        "content": {"type": "str"},
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

    if not HAS_PYCRYPTODOME:
        module.fail_json(msg=missing_required_lib("pycryptodome"))

    password = module.params["password"]

    if password is not None and not password.strip():
        module.fail_json(msg="no characters in password")

    if module.params["state"] == "present":
        ensure_present(module)

    ensure_absent(module)


if __name__ == "__main__":
    main()
