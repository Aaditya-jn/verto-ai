# utils/language_store.py
import json
import os

LANG_FILE = os.getenv("USER_LANG_FILE", "user_languages.json")


def _load() -> dict:
    if not os.path.exists(LANG_FILE):
        return {}
    with open(LANG_FILE) as f:
        return json.load(f)


def get_user_language(phone: str) -> str:
    return _load().get(phone, "English")


def set_user_language(phone: str, language: str):
    store = _load()
    store[phone] = language
    with open(LANG_FILE, "w") as f:
        json.dump(store, f, indent=2)
