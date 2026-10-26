"""Encrypted SQLite vault for Mars Studio integration secrets.

The encrypted records are kept in a private SQLite file; the master encryption
key lives in the OS credential store, not beside the database. No plaintext
secret is written to disk, logs, application JSON or HTTP status endpoints.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

MASTER_KEY_NAME="encrypted-sqlite-master-v1"


def _db_path(settings_path):
    return Path(settings_path).with_name("integrations.secrets.sqlite3")


def _master(keyring, service):
    # A legacy Windows keyring is still used *only* for the encryption key.
    key=keyring.get_password(service,MASTER_KEY_NAME)
    if not key:
        key=Fernet.generate_key().decode("ascii")
        keyring.set_password(service,MASTER_KEY_NAME,key)
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError,TypeError) as error:
        raise RuntimeError("Khóa mã hóa database không hợp lệ hoặc bị mất. Không tạo khóa mới khi đã có dữ liệu.") from None


def _connect(path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(path,timeout=12)
    try:
        if os.name!="nt":
            os.chmod(path,0o600)
        con.execute("PRAGMA busy_timeout=12000")
        con.execute("""CREATE TABLE IF NOT EXISTS integration_secrets(
            name TEXT PRIMARY KEY NOT NULL,
            ciphertext BLOB NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        return con
    except BaseException:
        con.close()
        raise


def read_secret(settings_path,keyring,service,name):
    """Return None when absent; raise when a ciphertext cannot be decrypted."""
    with _connect(_db_path(settings_path)) as con:
        row=con.execute("SELECT ciphertext FROM integration_secrets WHERE name=?",(name,)).fetchone()
    if row is None:return None
    try:
        return _master(keyring,service).decrypt(row[0]).decode("utf-8")
    except (InvalidToken,UnicodeDecodeError):
        raise RuntimeError("Không giải mã được API key từ database. Kiểm tra tài khoản Windows hoặc bản sao lưu.") from None


def save_secret(settings_path,keyring,service,name,secret):
    ciphertext=_master(keyring,service).encrypt(secret.encode("utf-8"))
    with _connect(_db_path(settings_path)) as con:
        con.execute("""INSERT INTO integration_secrets(name,ciphertext)
            VALUES(?,?) ON CONFLICT(name) DO UPDATE SET
            ciphertext=excluded.ciphertext,updated_at=CURRENT_TIMESTAMP""",(name,ciphertext))


def delete_secret(settings_path,name):
    with _connect(_db_path(settings_path)) as con:
        con.execute("DELETE FROM integration_secrets WHERE name=?",(name,))


def migrate_one(settings_path,keyring,service,name):
    """Copy+verify a legacy key to encrypted SQLite before deleting legacy key."""
    present=read_secret(settings_path,keyring,service,name)
    if present is not None:return present
    legacy=keyring.get_password(service,name)
    if not legacy:return None
    save_secret(settings_path,keyring,service,name,legacy)
    if read_secret(settings_path,keyring,service,name)!=legacy:
        raise RuntimeError("Không xác minh được bản mã trong database; chưa xóa khóa cũ.")
    try:keyring.delete_password(service,name)
    except Exception:
        # Keep duplicate key in OS store if its removal fails; never lose a key.
        pass
    return legacy
