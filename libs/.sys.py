import os
import time
#import keyboard
import shutil
import sys as s
import json
from pathlib import Path
from typing import Any

# Time

def format_time(format: str) -> str:
    if format is None:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    return time.strftime(format, time.localtime())


def current_time() -> float:
    return time.time()


def current_timestamp() -> int:
    return int(time.time())


def current_milliseconds() -> int:
    return int(time.time() * 1000)


def hours() -> int:
    return time.localtime().tm_hour


def minutes() -> int:
    return time.localtime().tm_min


def seconds() -> int:
    return time.localtime().tm_sec


def milliseconds() -> int:
    return int((time.time() % 1) * 1000)


def sleep(seconds: float) -> None:
    time.sleep(seconds)


def date() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


def year() -> str:
    return time.strftime("%Y", time.localtime())


def month() -> str:
    return time.strftime("%m", time.localtime())


def day() -> str:
    return time.strftime("%d", time.localtime())

# Files

def cwd() -> str:
    return os.getcwd()


def path_exists(file_path: str) -> bool:
    return os.path.exists(file_path)


def path_parent(file_path: str):
    route = Path(file_path)
    return route.parent()


def cp_path(file_path: str, new_path: str) -> None:
    shutil.copy2(file_path, new_path)


def mv_path(file_path: str, new_path: str) -> None:
    shutil.move(file_path, new_path)


def list_dir(file_path: str = ".") -> list[str]:
    return os.listdir(file_path)


def mk_dir(file_path) -> None:
    os.makedirs(file_path, exist_ok=True)


def rm_dir(file_path: str) -> None:
    shutil.rmtree(file_path)


def file_name(file_path: str, ext: bool) -> str:
    route = Path(file_path)
    if ext:
        return route.name
    else:
        return route.stem


def rm_file(file_path: str) -> None:
    os.remove(file_path)


"""def file_read(file_path: str):
    with open(file_path, 'r', encoding="utf-8") as _file:
        content = _file.read()
    return content"""

def file_suffix(file_path: str) -> str:
    return Path(file_path).suffix


# OS

def platform_name():
    return s.platform


def os_name() -> str:
    return os.name


def cpu_count() -> int:
    return os.cpu_count() or 1


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _exit() -> None:
    s.exit()

# json

def json_dump(entry: dict) -> str:
    return json.dumps(entry, indent=4)


def json_load(files: str):
    return json.load(files)


def json_read(entry: str):
    return json.loads(entry)


"""

def key_write(text: str = "") -> None:
    keyboard.write(text)


def key_press(key: str) -> None:
    keyboard.press_and_release(key)


def key_wait(key: str) -> None:
    keyboard.wait(key)


def key_record(keys):
    return keyboard.record(until="esc")


def key_play(reg):
    keyboard.play(reg)
"""
