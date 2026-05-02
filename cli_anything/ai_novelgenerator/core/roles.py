"""Role-library management for workspace-backed character records."""

import contextlib
import io
import os
import re
import shutil
import importlib

from cli_anything.ai_novelgenerator.utils.ai_novelgenerator_backend import get_runtime_config, patched_adapters, source_modules


ATTRIBUTE_ORDER = ["物品", "能力", "状态", "主要角色间关系网", "触发或加深的事件"]
TEMP_LIBRARY_NAME = "临时角色库"
ALL_CATEGORY_NAME = "全部"


def roles_root(project: dict) -> str:
    return os.path.join(project["workspace_dir"], "角色库")


def ensure_library(project: dict) -> dict:
    root = roles_root(project)
    os.makedirs(os.path.join(root, ALL_CATEGORY_NAME), exist_ok=True)
    return {"roles_root": root, "default_category": ALL_CATEGORY_NAME}


def list_categories(project: dict) -> dict:
    root_info = ensure_library(project)
    root = root_info["roles_root"]
    categories = [ALL_CATEGORY_NAME]
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if os.path.isdir(path) and name != ALL_CATEGORY_NAME:
            categories.append(name)
    return {"roles_root": root, "categories": categories, "category_count": len(categories)}


def create_category(project: dict, category: str) -> dict:
    normalized = _normalize_category(category)
    ensure_library(project)
    path = os.path.join(roles_root(project), normalized)
    os.makedirs(path, exist_ok=True)
    return {"category": normalized, "path": path, "created": True}


def list_roles(project: dict, category: str = ALL_CATEGORY_NAME) -> dict:
    root = ensure_library(project)["roles_root"]
    selected = _normalize_category(category)
    categories = list_categories(project)["categories"]
    roles = []
    if selected == ALL_CATEGORY_NAME:
        seen = set()
        for current in categories:
            for entry in _iter_role_files(os.path.join(root, current)):
                name = entry[:-4]
                if name in seen:
                    continue
                seen.add(name)
                actual_category = _find_role_category(project, name)
                roles.append(_role_summary(project, name, actual_category))
    else:
        path = os.path.join(root, selected)
        if not os.path.isdir(path):
            raise RuntimeError(f"Role category not found: {selected}")
        for entry in _iter_role_files(path):
            roles.append(_role_summary(project, entry[:-4], selected))
    return {
        "roles_root": root,
        "category": selected,
        "role_count": len(roles),
        "roles": sorted(roles, key=lambda item: item["name"]),
    }


def get_role(project: dict, name: str) -> dict:
    normalized_name = _normalize_role_name(name)
    path, category = _resolve_role_path(project, normalized_name)
    text = _read_text(path)
    attributes = parse_role_text(text)
    return {
        "name": normalized_name,
        "category": category,
        "path": path,
        "text": text,
        "attributes": attributes,
    }


def create_role(project: dict, name: str, category: str = ALL_CATEGORY_NAME, attributes: dict | None = None, text: str | None = None) -> dict:
    normalized_name = _normalize_role_name(name)
    normalized_category = _normalize_category(category)
    if role_exists(project, normalized_name):
        raise RuntimeError(f"Role already exists: {normalized_name}")
    create_category(project, normalized_category)
    role_text = _coerce_role_text(normalized_name, text=text, attributes=attributes)
    path = os.path.join(roles_root(project), normalized_category, f"{normalized_name}.txt")
    _write_text(path, role_text)
    return get_role(project, normalized_name)


def rename_role(project: dict, old_name: str, new_name: str) -> dict:
    source_name = _normalize_role_name(old_name)
    target_name = _normalize_role_name(new_name)
    if source_name == target_name:
        return get_role(project, source_name)
    if role_exists(project, target_name):
        raise RuntimeError(f"Role already exists: {target_name}")
    source_path, category = _resolve_role_path(project, source_name)
    text = _read_text(source_path)
    updated = _replace_role_heading(text, target_name)
    target_path = os.path.join(roles_root(project), category, f"{target_name}.txt")
    _write_text(target_path, updated)
    os.remove(source_path)
    return get_role(project, target_name)


def delete_role(project: dict, name: str) -> dict:
    normalized_name = _normalize_role_name(name)
    path, category = _resolve_role_path(project, normalized_name)
    os.remove(path)
    return {"name": normalized_name, "category": category, "path": path, "deleted": True}


def move_role(project: dict, name: str, category: str) -> dict:
    normalized_name = _normalize_role_name(name)
    target_category = _normalize_category(category)
    source_path, source_category = _resolve_role_path(project, normalized_name)
    if source_category == target_category:
        return get_role(project, normalized_name)
    create_category(project, target_category)
    target_path = os.path.join(roles_root(project), target_category, f"{normalized_name}.txt")
    if os.path.exists(target_path):
        raise RuntimeError(f"Role already exists in target category: {normalized_name}")
    shutil.move(source_path, target_path)
    return get_role(project, normalized_name)


def import_roles_from_file(project: dict, file_path: str, category: str = ALL_CATEGORY_NAME) -> dict:
    normalized_category = _normalize_category(category)
    content = _read_import_file(file_path)
    parsed = parse_roles_from_analysis(content)
    imported = []
    for role in parsed:
        if role_exists(project, role["name"]):
            raise RuntimeError(f"Role already exists: {role['name']}")
        imported.append(create_role(project, role["name"], category=normalized_category, attributes=role["attributes"]))
    return {
        "input": os.path.abspath(file_path),
        "category": normalized_category,
        "imported_count": len(imported),
        "roles": imported,
    }


def analyze_character_state(project: dict, text: str | None = None, from_file: str | None = None, save_to_temp: bool = True) -> dict:
    if bool(text) == bool(from_file):
        raise RuntimeError("Provide exactly one of text or from_file.")
    content = text if text is not None else _read_import_file(from_file or "")
    if not content.strip():
        raise RuntimeError("No character-state content to analyze.")

    runtime = get_runtime_config(project)
    modules = source_modules(project["source_root"])
    prompt = importlib.import_module("prompt_definitions").Character_Import_Prompt.format(content=content)
    with patched_adapters(project):
        with contextlib.redirect_stdout(io.StringIO()):
            llm = modules["llm_adapters"].create_llm_adapter(
                interface_format=runtime["prompt_draft_llm"]["interface_format"],
                base_url=runtime["prompt_draft_llm"]["base_url"],
                model_name=runtime["prompt_draft_llm"]["model_name"],
                api_key=runtime["prompt_draft_llm"]["api_key"],
                temperature=runtime["prompt_draft_llm"]["temperature"],
                max_tokens=runtime["prompt_draft_llm"]["max_tokens"],
                timeout=runtime["prompt_draft_llm"]["timeout"],
            )
            response = importlib.import_module("novel_generator.common").invoke_with_cleaning(llm, prompt)

    roles = parse_roles_from_analysis(response)
    if save_to_temp:
        temp_dir = os.path.join(roles_root(project), TEMP_LIBRARY_NAME)
        if os.path.isdir(temp_dir):
            for entry in _iter_role_files(temp_dir):
                os.remove(os.path.join(temp_dir, entry))
        else:
            os.makedirs(temp_dir, exist_ok=True)
        for role in roles:
            _write_text(os.path.join(temp_dir, f"{role['name']}.txt"), build_role_text(role["name"], role["attributes"]))
    return {
        "input_source": os.path.abspath(from_file) if from_file else None,
        "analyzed_role_count": len(roles),
        "roles": roles,
        "saved_to_temp": bool(save_to_temp),
        "temp_category": TEMP_LIBRARY_NAME if save_to_temp else None,
    }


def import_from_character_state(project: dict, category: str = ALL_CATEGORY_NAME, from_file: str | None = None) -> dict:
    source = from_file or os.path.join(project["workspace_dir"], "character_state.txt")
    analyzed = analyze_character_state(project, from_file=source, save_to_temp=False)
    imported = []
    for role in analyzed["roles"]:
        if role_exists(project, role["name"]):
            continue
        imported.append(create_role(project, role["name"], category=category, attributes=role["attributes"]))
    analyzed["imported_count"] = len(imported)
    analyzed["imported_roles"] = imported
    analyzed["category"] = _normalize_category(category)
    return analyzed


def inject_role_library_into_prompt(project: dict, prompt_text: str, role_names: str) -> dict:
    requested_names = [item.strip() for item in re.split(r"[,，]\s*", role_names or "") if item.strip()]
    if not requested_names:
        return {"prompt_text": prompt_text, "included_roles": [], "role_blocks": []}
    included_roles = []
    role_blocks = []
    for name in requested_names:
        if not role_exists(project, name):
            continue
        role_data = get_role(project, name)
        included_roles.append(name)
        role_blocks.append(role_data["text"].strip())
    if not role_blocks:
        return {"prompt_text": prompt_text, "included_roles": [], "role_blocks": []}

    role_content = "\n".join(role_blocks)
    updated_prompt = prompt_text
    replacements = [
        "Core characters (may not be specified): {characters_involved}",
        "Core characters: {characters_involved}",
        "核心人物(可能未指定)：{characters_involved}",
        "核心人物：{characters_involved}",
        "核心人物(可能未指定):{characters_involved}",
        "核心人物:{characters_involved}",
    ]
    for placeholder in replacements:
        if placeholder in updated_prompt:
            label = "Core characters:" if "Core characters" in placeholder else "核心人物："
            updated_prompt = updated_prompt.replace(placeholder, f"{label}\n{role_content}")
            break
    else:
        lines = updated_prompt.splitlines()
        for index, line in enumerate(lines):
            if "Core characters" in line or "核心人物" in line:
                label = "Core characters:" if "Core characters" in line else "核心人物："
                lines[index] = f"{label}\n{role_content}"
                break
        updated_prompt = "\n".join(lines)
    return {
        "prompt_text": updated_prompt,
        "included_roles": included_roles,
        "role_blocks": role_blocks,
    }


def parse_role_text(text: str) -> dict:
    attributes = {name: [] for name in ATTRIBUTE_ORDER}
    current_attribute = None
    for raw_line in text.splitlines()[1:]:
        line = raw_line.strip()
        if line.startswith(("├──", "└──")) and (":" in line or "：" in line):
            attr_name = re.split(r"[:：]", line.split("──", 1)[1], 1)[0].strip()
            if attr_name in attributes:
                current_attribute = attr_name
            else:
                current_attribute = None
            continue
        if current_attribute and (line.startswith("│") or line.startswith("├") or line.startswith("└")):
            item = re.sub(r"^[│├└─\s]*", "", line).strip()
            if item:
                attributes[current_attribute].append(item)
    return attributes


def parse_roles_from_analysis(response: str) -> list[dict]:
    roles = []
    current_role = None
    current_attr = None
    current_subattr = None
    attribute_pattern = re.compile(r"^([├└]──)([\w\u4e00-\u9fa5]+)\s*[:：]")
    item_pattern = re.compile(r"^│\s+([├└]──)\s*(.*)")
    role_pattern = re.compile(r"^\s*([\u4e00-\u9fa5a-zA-Z0-9_\-]+)\s*[:：]\s*$")
    for raw_line in response.splitlines():
        line = raw_line.rstrip()
        role_match = role_pattern.match(line)
        if role_match:
            current_role = _normalize_role_name(role_match.group(1).strip())
            roles.append({"name": current_role, "attributes": {}})
            current_attr = None
            current_subattr = None
            continue
        if not current_role:
            continue
        attr_match = attribute_pattern.match(line)
        if attr_match:
            current_attr = attr_match.groups()[1].strip()
            roles[-1]["attributes"].setdefault(current_attr, [])
            current_subattr = None
            continue
        item_match = item_pattern.match(line)
        if item_match and current_attr:
            content = item_match.groups()[1].strip()
            if ":" in content or "：" in content:
                parts = re.split(r"[:：]", content, 1)
                current_subattr = parts[0].strip()
                value = parts[1].strip()
                if value:
                    roles[-1]["attributes"][current_attr].append(f"{current_subattr}: {value}")
                continue
            if content:
                if current_subattr and roles[-1]["attributes"][current_attr]:
                    roles[-1]["attributes"][current_attr][-1] += f"，{content}"
                else:
                    roles[-1]["attributes"][current_attr].append(content)
    for role in roles:
        role["attributes"] = {key: role["attributes"].get(key, []) for key in ATTRIBUTE_ORDER}
    return roles


def build_role_text(name: str, attributes: dict | None = None) -> str:
    normalized_name = _normalize_role_name(name)
    values = attributes or {}
    lines = [f"{normalized_name}："]
    for attr_name in ATTRIBUTE_ORDER:
        lines.append(f"├──{attr_name}：")
        for item in values.get(attr_name, []):
            if str(item).strip():
                lines.append(f"│  ├──{str(item).strip()}")
    return "\n".join(lines)


def role_exists(project: dict, name: str) -> bool:
    try:
        _resolve_role_path(project, _normalize_role_name(name))
    except RuntimeError:
        return False
    return True


def _coerce_role_text(name: str, text: str | None, attributes: dict | None) -> str:
    if text is not None:
        return _replace_role_heading(text, name)
    return build_role_text(name, attributes=attributes)


def _replace_role_heading(text: str, new_name: str) -> str:
    lines = text.splitlines()
    if not lines:
        return build_role_text(new_name)
    lines[0] = f"{new_name}："
    return "\n".join(lines)


def _role_summary(project: dict, name: str, category: str) -> dict:
    data = get_role(project, name)
    return {
        "name": name,
        "category": category,
        "path": data["path"],
        "attribute_counts": {key: len(value) for key, value in data["attributes"].items()},
    }


def _iter_role_files(path: str) -> list[str]:
    if not os.path.isdir(path):
        return []
    return sorted(name for name in os.listdir(path) if name.endswith(".txt"))


def _resolve_role_path(project: dict, name: str) -> tuple[str, str]:
    category = _find_role_category(project, name)
    if not category:
        raise RuntimeError(f"Role not found: {name}")
    return os.path.join(roles_root(project), category, f"{name}.txt"), category


def _find_role_category(project: dict, name: str) -> str | None:
    return _find_role_category_internal(project, name, include_temp=False)


def _find_role_category_internal(project: dict, name: str, include_temp: bool) -> str | None:
    root = ensure_library(project)["roles_root"]
    for category in list_categories(project)["categories"]:
        if not include_temp and category == TEMP_LIBRARY_NAME:
            continue
        path = os.path.join(root, category, f"{name}.txt")
        if os.path.exists(path):
            return category
    return None


def _normalize_category(category: str | None) -> str:
    value = (category or ALL_CATEGORY_NAME).strip()
    return value or ALL_CATEGORY_NAME


def _normalize_role_name(name: str) -> str:
    value = (name or "").strip().split(":")[0].split("：")[0].strip()
    if not value:
        raise RuntimeError("Role name cannot be empty.")
    return value


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _read_import_file(file_path: str) -> str:
    absolute = os.path.abspath(file_path)
    if absolute.lower().endswith(".docx"):
        from docx import Document

        document = Document(absolute)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    return _read_text(absolute)
