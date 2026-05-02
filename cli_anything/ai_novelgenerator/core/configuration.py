"""Config.json CRUD helpers for LLM and embedding profiles."""

import json
import os
from copy import deepcopy


LLM_SLOTS = [
    "architecture_llm",
    "chapter_outline_llm",
    "prompt_draft_llm",
    "final_chapter_llm",
    "consistency_review_llm",
]
EMBEDDING_SLOT = "embedding"
DEFAULT_CHOOSE_KEYS = LLM_SLOTS + [EMBEDDING_SLOT]

LLM_DEFAULTS = {
    "api_key": "",
    "base_url": "",
    "model_name": "",
    "temperature": 0.7,
    "max_tokens": 4096,
    "timeout": 600,
    "interface_format": "OpenAI",
}

EMBEDDING_DEFAULTS = {
    "api_key": "",
    "base_url": "",
    "model_name": "",
    "retrieval_k": 4,
    "interface_format": "OpenAI",
}

REDACTED = "[redacted]"


def load_config_file(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise RuntimeError(f"Config file must contain a JSON object: {config_path}")
    data.setdefault("llm_configs", {})
    data.setdefault("embedding_configs", {})
    data.setdefault("choose_configs", {})
    return data


def save_config_file(config_data: dict, config_path: str) -> dict:
    os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(config_data, handle, ensure_ascii=False, indent=2, sort_keys=True)
    return {"config_path": os.path.abspath(config_path), "saved": True}


def config_summary(config_path: str) -> dict:
    config = load_config_file(config_path)
    return {
        "config_path": _safe_path_label(config_path),
        "llm_profiles": sorted(config["llm_configs"].keys()),
        "embedding_profiles": sorted(config["embedding_configs"].keys()),
        "choose_configs": _normalized_choose_configs(config),
    }


def list_profiles(config_path: str, profile_type: str) -> dict:
    config = load_config_file(config_path)
    section_name = _section_name(profile_type)
    profiles = config[section_name]
    return {
        "config_path": _safe_path_label(config_path),
        "profile_type": profile_type,
        "profile_count": len(profiles),
        "profiles": [
            {
                "name": name,
                "config": redact_profile(deepcopy(value)),
                "is_selected": _profile_is_selected(config, profile_type, name),
                "selected_slots": _selected_slots(config, profile_type, name),
            }
            for name, value in sorted(profiles.items())
        ],
    }


def get_profile(config_path: str, profile_type: str, name: str) -> dict:
    config = load_config_file(config_path)
    section = _profiles_section(config, profile_type)
    profile_name = _require_profile(section, name, profile_type)
    return {
        "config_path": _safe_path_label(config_path),
        "profile_type": profile_type,
        "name": profile_name,
        "config": redact_profile(deepcopy(section[profile_name])),
        "is_selected": _profile_is_selected(config, profile_type, profile_name),
        "selected_slots": _selected_slots(config, profile_type, profile_name),
    }


def create_profile(config_path: str, profile_type: str, name: str, values: dict) -> dict:
    config = load_config_file(config_path)
    section = _profiles_section(config, profile_type)
    profile_name = _normalize_name(name)
    if profile_name in section:
        raise RuntimeError(f"{profile_type} profile already exists: {profile_name}")
    section[profile_name] = _build_profile(profile_type, values)
    save_config_file(config, config_path)
    return get_profile(config_path, profile_type, profile_name)


def update_profile(config_path: str, profile_type: str, name: str, values: dict) -> dict:
    config = load_config_file(config_path)
    section = _profiles_section(config, profile_type)
    profile_name = _require_profile(section, name, profile_type)
    updated = deepcopy(section[profile_name])
    changed = False
    for key, value in values.items():
        if value is None:
            continue
        updated[key] = _coerce_value(profile_type, key, value)
        changed = True
    if not changed:
        raise RuntimeError("No profile fields were provided for update.")
    section[profile_name] = updated
    save_config_file(config, config_path)
    return get_profile(config_path, profile_type, profile_name)


def import_profile(config_path: str, profile_type: str, name: str, profile_data: dict, overwrite: bool = False) -> dict:
    config = load_config_file(config_path)
    section = _profiles_section(config, profile_type)
    profile_name = _normalize_name(name)
    imported = _build_imported_profile(profile_type, profile_data)
    if profile_name in section and not overwrite:
        raise RuntimeError(f"{profile_type} profile already exists: {profile_name}")
    section[profile_name] = imported
    save_config_file(config, config_path)
    result = get_profile(config_path, profile_type, profile_name)
    result["imported"] = True
    result["overwrote_existing"] = bool(overwrite)
    return result


def rename_profile(config_path: str, profile_type: str, old_name: str, new_name: str) -> dict:
    config = load_config_file(config_path)
    section = _profiles_section(config, profile_type)
    source_name = _require_profile(section, old_name, profile_type)
    target_name = _normalize_name(new_name)
    if source_name == target_name:
        return get_profile(config_path, profile_type, source_name)
    if target_name in section:
        raise RuntimeError(f"{profile_type} profile already exists: {target_name}")
    section[target_name] = section.pop(source_name)
    choose = config.setdefault("choose_configs", {})
    for slot in _slots_for_type(profile_type):
        if choose.get(slot) == source_name:
            choose[slot] = target_name
    save_config_file(config, config_path)
    return get_profile(config_path, profile_type, target_name)


def delete_profile(config_path: str, profile_type: str, name: str) -> dict:
    config = load_config_file(config_path)
    section = _profiles_section(config, profile_type)
    profile_name = _require_profile(section, name, profile_type)
    selected_slots = _selected_slots(config, profile_type, profile_name)
    if selected_slots:
        joined = ", ".join(selected_slots)
        raise RuntimeError(f"Cannot delete selected {profile_type} profile '{profile_name}' while used by: {joined}")
    removed = deepcopy(section.pop(profile_name))
    save_config_file(config, config_path)
    return {
        "config_path": _safe_path_label(config_path),
        "profile_type": profile_type,
        "name": profile_name,
        "config": redact_profile(removed),
        "deleted": True,
    }


def show_choose_configs(config_path: str) -> dict:
    config = load_config_file(config_path)
    choose = _normalized_choose_configs(config)
    return {
        "config_path": _safe_path_label(config_path),
        "choose_configs": choose,
    }


def redact_profile(profile: dict) -> dict:
    redacted = deepcopy(profile)
    if "api_key" in redacted:
        redacted["api_key"] = _mask_secret(redacted.get("api_key"))
    return redacted


def redact_runtime_config(runtime: dict) -> dict:
    payload = deepcopy(runtime)
    for key, value in payload.items():
        if isinstance(value, dict):
            payload[key] = redact_profile(value)
    return payload


def safe_config_reference(config_path: str) -> dict:
    absolute = os.path.abspath(config_path)
    return {
        "config_file": os.path.basename(absolute),
        "config_dir": os.path.dirname(absolute),
        "config_path": _safe_path_label(absolute),
    }


def set_choose_configs(config_path: str, values: dict) -> dict:
    config = load_config_file(config_path)
    llm_profiles = config["llm_configs"]
    embedding_profiles = config["embedding_configs"]
    choose = config.setdefault("choose_configs", {})
    changed = False
    for slot, value in values.items():
        if value is None:
            continue
        if slot in LLM_SLOTS:
            profile_name = _require_profile(llm_profiles, value, "llm")
        elif slot == EMBEDDING_SLOT:
            profile_name = _require_profile(embedding_profiles, value, "embedding")
        else:
            raise RuntimeError(f"Unsupported choose-config slot: {slot}")
        choose[slot] = profile_name
        changed = True
    if not changed:
        raise RuntimeError("No choose-config fields were provided.")
    save_config_file(config, config_path)
    return show_choose_configs(config_path)


def _profiles_section(config: dict, profile_type: str) -> dict:
    return config[_section_name(profile_type)]


def _section_name(profile_type: str) -> str:
    if profile_type == "llm":
        return "llm_configs"
    if profile_type == "embedding":
        return "embedding_configs"
    raise RuntimeError(f"Unsupported profile type: {profile_type}")


def _slots_for_type(profile_type: str) -> list[str]:
    if profile_type == "llm":
        return list(LLM_SLOTS)
    if profile_type == "embedding":
        return [EMBEDDING_SLOT]
    raise RuntimeError(f"Unsupported profile type: {profile_type}")


def _normalized_choose_configs(config: dict) -> dict:
    choose = config.get("choose_configs", {})
    return {key: choose.get(key) for key in DEFAULT_CHOOSE_KEYS}


def _profile_is_selected(config: dict, profile_type: str, name: str) -> bool:
    return bool(_selected_slots(config, profile_type, name))


def _selected_slots(config: dict, profile_type: str, name: str) -> list[str]:
    choose = config.get("choose_configs", {})
    return [slot for slot in _slots_for_type(profile_type) if choose.get(slot) == name]


def _build_profile(profile_type: str, values: dict) -> dict:
    defaults = deepcopy(LLM_DEFAULTS if profile_type == "llm" else EMBEDDING_DEFAULTS)
    for key, value in values.items():
        if value is None:
            continue
        defaults[key] = _coerce_value(profile_type, key, value)
    return defaults


def _build_imported_profile(profile_type: str, values: dict) -> dict:
    if not isinstance(values, dict):
        raise RuntimeError(f"Imported {profile_type} profile must be a JSON object.")
    profile = deepcopy(values)
    defaults = LLM_DEFAULTS if profile_type == "llm" else EMBEDDING_DEFAULTS
    for key, default_value in defaults.items():
        profile[key] = _coerce_value(profile_type, key, profile.get(key, default_value))
    return profile


def _coerce_value(profile_type: str, key: str, value):
    if key in {"temperature"}:
        return float(value)
    if key in {"max_tokens", "timeout", "retrieval_k"}:
        return int(value)
    if key in {"api_key", "base_url", "model_name", "interface_format"}:
        return str(value)
    raise RuntimeError(f"Unsupported field for {profile_type} profile: {key}")


def _normalize_name(name: str) -> str:
    normalized = str(name).strip()
    if not normalized:
        raise RuntimeError("Profile name cannot be empty.")
    return normalized


def _require_profile(section: dict, name: str, profile_type: str) -> str:
    profile_name = _normalize_name(name)
    if profile_name not in section:
        raise RuntimeError(f"{profile_type} profile not found: {profile_name}")
    return profile_name


def _safe_path_label(path: str) -> str:
    absolute = os.path.abspath(path)
    return os.path.join("...", os.path.basename(os.path.dirname(absolute)), os.path.basename(absolute))


def _mask_secret(value) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= 4:
        return REDACTED
    return f"{text[:2]}***{text[-2:]}"
