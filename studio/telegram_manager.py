"""Manage Telegram polling process entirely from the GUI.

The child process gets temporary credentials injected in its private process
environment (not a user-editable .env, command-line arguments or persisted
files). Secrets are read from Windows credential store at launch.
"""
from __future__ import annotations
import os
import subprocess
import sys
import threading
from pathlib import Path
import integration_settings

ROOT=Path(__file__).resolve().parent
BOT=ROOT.parent/"legacy"/"tea_ai_local"/"telegram_listing_bot.py"
LOCK=threading.RLock()
PROCESS=None
START_ERROR=""

def status():
    with LOCK:
        proc=PROCESS
        active=bool(proc is not None and proc.poll() is None)
        return {"running":active,"pid":proc.pid if active else None,
                "message":("Telegram Bot đang chạy trên máy tính." if active else
                           START_ERROR if START_ERROR else "Telegram Bot chưa chạy.")}

def start():
    global PROCESS,START_ERROR
    with LOCK:
        if PROCESS is not None and PROCESS.poll() is None:
            return status()
        if not BOT.is_file():raise ValueError("Không tìm thấy mã nguồn Telegram Bot")
        try:
            import telegram
            if not getattr(telegram, "__version__", None):
                raise ImportError("python-telegram-bot")
        except ImportError:
            raise ValueError("Chưa cài python-telegram-bot. Hãy chạy setup_windows.bat một lần.")
        cfg=integration_settings.telegram_env()
        child_env=dict(os.environ)
        child_env.update(cfg)
        # No Telegram token is placed in argv. Silence legacy script stdout
        # to avoid accidental secret logging from untrusted exceptions.
        flags=getattr(subprocess,"CREATE_NO_WINDOW",0) if os.name=="nt" else 0
        try:
            PROCESS=subprocess.Popen([sys.executable,str(BOT)],
                   cwd=str(BOT.parent),env=child_env,
                   stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                   creationflags=flags)
            START_ERROR=""
        except OSError as ex:
            START_ERROR="Không thể khởi động Telegram Bot: "+type(ex).__name__
            raise ValueError(START_ERROR) from None
        return status()

def stop():
    global PROCESS,START_ERROR
    with LOCK:
        proc=PROCESS
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill()
        PROCESS=None
        START_ERROR=""
        return status()
