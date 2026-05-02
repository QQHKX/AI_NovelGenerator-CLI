"""Generation wrappers around the source novel-planning and chapter pipeline."""

import contextlib
import io
import importlib
import json
import os
import re

from cli_anything.ai_novelgenerator.core import roles as roles_mod
from cli_anything.ai_novelgenerator.utils.ai_novelgenerator_backend import get_runtime_config, patched_adapters, source_modules


def _quiet_call(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def _progress(callback, scope: str, step: str, current: int | None = None, total: int | None = None, **extra):
    if callback is None:
        return
    callback(scope=scope, step=step, current=current, total=total, **extra)


def _chapter_path(project: dict, chapter_number: int) -> str:
    return os.path.join(project["workspace_dir"], "chapters", f"chapter_{int(chapter_number)}.txt")


def _blueprint_path(project: dict) -> str:
    return os.path.join(project["workspace_dir"], "Novel_directory.txt")


def _chapter_state_path(project: dict) -> str:
    return os.path.join(project["workspace_dir"], "chapter_states.json")


def _chapter_exists(project: dict, chapter_number: int) -> bool:
    return os.path.exists(_chapter_path(project, chapter_number))


def _load_chapter_state(project: dict) -> dict:
    path = _chapter_state_path(project)
    if not os.path.exists(path):
        return {"finalized_chapters": []}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    finalized = sorted({int(item) for item in data.get("finalized_chapters", [])})
    return {"finalized_chapters": finalized}


def _save_chapter_state(project: dict, state: dict) -> str:
    path = _chapter_state_path(project)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
    return path


def _is_finalized(project: dict, chapter_number: int) -> bool:
    state = _load_chapter_state(project)
    return int(chapter_number) in set(state["finalized_chapters"])


def _mark_finalized(project: dict, chapter_number: int) -> str:
    state = _load_chapter_state(project)
    finalized = set(state["finalized_chapters"])
    finalized.add(int(chapter_number))
    return _save_chapter_state(project, {"finalized_chapters": sorted(finalized)})


def _word_count(project: dict, text: str) -> int:
    modules = source_modules(project["source_root"])
    return int(modules["source_utils"].get_word_count(text))


def _blueprint_chapter_numbers(project: dict) -> list[int]:
    report = validate_blueprint(project, require_complete=False)
    return report["chapter_numbers"]


def validate_blueprint(project: dict, require_complete: bool = True) -> dict:
    blueprint_path = _blueprint_path(project)
    if not os.path.exists(blueprint_path):
        return {
            "exists": False,
            "path": blueprint_path,
            "chapter_numbers": [],
            "chapter_count": 0,
            "requires_complete": bool(require_complete),
        }

    with open(blueprint_path, "r", encoding="utf-8") as handle:
        blueprint_text = handle.read()

    source_modules(project["source_root"])
    parser = importlib.import_module("chapter_directory_parser")
    chapters = parser.parse_chapter_blueprint(blueprint_text)
    configured_total = int(project["parameters"]["num_chapters"])
    header_numbers = [int(match.group(1)) for match in re.finditer(r"^第\s*(\d+)\s*章\s*-", blueprint_text, re.MULTILINE)]
    parsed_numbers = [int(item["chapter_number"]) for item in chapters]
    duplicate_numbers = sorted({number for number in parsed_numbers if parsed_numbers.count(number) > 1})
    out_of_range_numbers = sorted({number for number in parsed_numbers if number < 1 or number > configured_total})
    invalid_header_count = max(0, len(header_numbers) - len(parsed_numbers))

    if invalid_header_count:
        raise RuntimeError(f"Blueprint contains {invalid_header_count} invalid chapter block(s) that could not be parsed strictly.")
    if duplicate_numbers:
        raise RuntimeError(f"Blueprint contains duplicate chapter numbers: {', '.join(str(item) for item in duplicate_numbers)}")
    if out_of_range_numbers:
        raise RuntimeError(
            f"Blueprint chapter numbers exceed configured total {configured_total}: {', '.join(str(item) for item in out_of_range_numbers)}"
        )

    unique_numbers = sorted(set(parsed_numbers))
    if require_complete:
        expected_numbers = list(range(1, configured_total + 1))
        missing_numbers = [number for number in expected_numbers if number not in unique_numbers]
        if missing_numbers:
            raise RuntimeError(
                f"Blueprint must contain every chapter from 1 to {configured_total}. Missing: {', '.join(str(item) for item in missing_numbers)}"
            )
        if unique_numbers != expected_numbers:
            raise RuntimeError("Blueprint chapter numbering must be continuous and ordered from 1 to the configured total.")

    return {
        "exists": True,
        "path": blueprint_path,
        "chapter_numbers": unique_numbers,
        "chapter_count": len(unique_numbers),
        "requires_complete": bool(require_complete),
    }


def validate_chapter_number(
    project: dict,
    chapter_number: int,
    require_in_blueprint: bool = False,
    require_complete_blueprint: bool = False,
) -> dict:
    number = int(chapter_number)
    if number < 1:
        raise RuntimeError("Chapter numbers must be positive integers.")
    configured_total = int(project["parameters"]["num_chapters"])
    if number > configured_total:
        raise RuntimeError(f"Chapter {number} exceeds configured total chapters: {configured_total}")

    blueprint_report = (
        validate_blueprint(project, require_complete=require_complete_blueprint) if os.path.exists(_blueprint_path(project)) else None
    )
    if require_in_blueprint and blueprint_report and number not in blueprint_report["chapter_numbers"]:
        raise RuntimeError(f"Chapter {number} is not present in the blueprint.")
    return {
        "chapter_number": number,
        "configured_total": configured_total,
        "blueprint": blueprint_report,
    }


def _resolve_range(project: dict, start_chapter: int, end_chapter: int, clamp_to_blueprint: bool = False) -> dict:
    start = int(start_chapter)
    end = int(end_chapter)
    if start < 1 or end < 1:
        raise RuntimeError("Chapter numbers must be positive integers.")
    if start > end:
        raise RuntimeError("Start chapter must be less than or equal to end chapter.")

    configured_total = int(project["parameters"]["num_chapters"])
    if end > configured_total:
        raise RuntimeError(f"Chapter range exceeds configured total chapters: {configured_total}")

    blueprint_numbers = _blueprint_chapter_numbers(project)
    blueprint_range = None
    effective_start = start
    effective_end = end
    if blueprint_numbers:
        blueprint_range = {
            "start_chapter": blueprint_numbers[0],
            "end_chapter": blueprint_numbers[-1],
            "chapter_numbers": blueprint_numbers,
        }
        if clamp_to_blueprint:
            effective_start = max(start, blueprint_numbers[0])
            effective_end = min(end, blueprint_numbers[-1])
            if effective_start > effective_end:
                raise RuntimeError(
                    f"Requested chapter range does not overlap blueprint chapters: {blueprint_numbers[0]}-{blueprint_numbers[-1]}"
                )

    return {
        "requested_start_chapter": start,
        "requested_end_chapter": end,
        "start_chapter": effective_start,
        "end_chapter": effective_end,
        "clamped_to_blueprint": bool(clamp_to_blueprint and (effective_start != start or effective_end != end)),
        "blueprint_range": blueprint_range,
    }


def _skip_reason(project: dict, chapter_number: int, skip_drafts: bool, skip_finalized: bool) -> str | None:
    has_draft = _chapter_exists(project, chapter_number)
    is_finalized = _is_finalized(project, chapter_number)
    if skip_finalized and is_finalized:
        return "skipped_finalized"
    if skip_drafts and has_draft and not is_finalized:
        return "skipped_draft"
    return None


def chapter_status(project: dict, chapter_number: int) -> dict:
    number = validate_chapter_number(project, chapter_number, require_in_blueprint=False)["chapter_number"]
    has_draft = _chapter_exists(project, number)
    is_finalized = _is_finalized(project, number)
    if is_finalized:
        state = "finalized"
    elif has_draft:
        state = "draft"
    else:
        state = "missing"
    return {
        "chapter_number": number,
        "chapter_path": _chapter_path(project, number),
        "exists": has_draft,
        "is_finalized": is_finalized,
        "state": state,
    }


def scan_chapter_statuses(
    project: dict,
    start_chapter: int = 1,
    end_chapter: int | None = None,
    clamp_to_blueprint: bool = False,
) -> dict:
    configured_total = int(project["parameters"]["num_chapters"])
    end = int(end_chapter) if end_chapter is not None else configured_total
    range_info = _resolve_range(project, start_chapter, end, clamp_to_blueprint=clamp_to_blueprint)
    chapters = [chapter_status(project, chapter_number) for chapter_number in range(range_info["start_chapter"], range_info["end_chapter"] + 1)]
    return {
        "requested_start_chapter": range_info["requested_start_chapter"],
        "requested_end_chapter": range_info["requested_end_chapter"],
        "start_chapter": range_info["start_chapter"],
        "end_chapter": range_info["end_chapter"],
        "clamp_to_blueprint": bool(clamp_to_blueprint),
        "clamped_to_blueprint": range_info["clamped_to_blueprint"],
        "blueprint_range": range_info["blueprint_range"],
        "chapter_count": len(chapters),
        "missing_count": sum(1 for item in chapters if item["state"] == "missing"),
        "draft_count": sum(1 for item in chapters if item["state"] == "draft"),
        "finalized_count": sum(1 for item in chapters if item["state"] == "finalized"),
        "chapters": chapters,
    }


def next_unfinished_chapter(
    project: dict,
    start_chapter: int = 1,
    end_chapter: int | None = None,
    skip_drafts: bool = True,
    skip_finalized: bool = True,
    clamp_to_blueprint: bool = False,
) -> dict:
    configured_total = int(project["parameters"]["num_chapters"])
    end = int(end_chapter) if end_chapter is not None else configured_total
    range_info = _resolve_range(project, start_chapter, end, clamp_to_blueprint=clamp_to_blueprint)
    skipped = []

    for chapter_number in range(range_info["start_chapter"], range_info["end_chapter"] + 1):
        skip_reason = _skip_reason(project, chapter_number, skip_drafts=skip_drafts, skip_finalized=skip_finalized)
        if skip_reason is None:
            return {
                "found": True,
                "chapter_number": chapter_number,
                "chapter_path": _chapter_path(project, chapter_number),
                "search_start": range_info["start_chapter"],
                "search_end": range_info["end_chapter"],
                "requested_start_chapter": range_info["requested_start_chapter"],
                "requested_end_chapter": range_info["requested_end_chapter"],
                "clamped_to_blueprint": range_info["clamped_to_blueprint"],
                "blueprint_range": range_info["blueprint_range"],
                "skip_summary": {
                    "skipped_count": len(skipped),
                    "skipped_draft_count": sum(1 for item in skipped if item["reason"] == "skipped_draft"),
                    "skipped_finalized_count": sum(1 for item in skipped if item["reason"] == "skipped_finalized"),
                    "skipped_chapters": skipped,
                },
                "resume_reason": f"Chapter {chapter_number} is the first chapter in range that is not skipped by the current continue policy.",
            }
        skipped.append(
            {
                "chapter_number": chapter_number,
                "reason": skip_reason,
                "chapter_path": _chapter_path(project, chapter_number),
            }
        )

    return {
        "found": False,
        "chapter_number": None,
        "chapter_path": None,
        "search_start": range_info["start_chapter"],
        "search_end": range_info["end_chapter"],
        "requested_start_chapter": range_info["requested_start_chapter"],
        "requested_end_chapter": range_info["requested_end_chapter"],
        "clamped_to_blueprint": range_info["clamped_to_blueprint"],
        "blueprint_range": range_info["blueprint_range"],
        "skip_summary": {
            "skipped_count": len(skipped),
            "skipped_draft_count": sum(1 for item in skipped if item["reason"] == "skipped_draft"),
            "skipped_finalized_count": sum(1 for item in skipped if item["reason"] == "skipped_finalized"),
            "skipped_chapters": skipped,
        },
        "resume_reason": "No chapter in the requested range passed the current continue policy.",
    }


def generate_architecture(project: dict, progress_callback=None) -> dict:
    _progress(progress_callback, "generate:architecture", "加载运行时配置")
    runtime = get_runtime_config(project)
    modules = source_modules(project["source_root"])
    params = project["parameters"]
    defaults = project["chapter_defaults"]
    _progress(progress_callback, "generate:architecture", "Calling model")
    with patched_adapters(project):
        _quiet_call(
            modules["novel_generator"].Novel_architecture_generate,
            interface_format=runtime["architecture_llm"]["interface_format"],
            api_key=runtime["architecture_llm"]["api_key"],
            base_url=runtime["architecture_llm"]["base_url"],
            llm_model=runtime["architecture_llm"]["model_name"],
            topic=params["topic"],
            genre=params["genre"],
            number_of_chapters=int(params["num_chapters"]),
            word_number=int(params["word_number"]),
            filepath=project["workspace_dir"],
            user_guidance=defaults["user_guidance"],
            temperature=runtime["architecture_llm"]["temperature"],
            max_tokens=runtime["architecture_llm"]["max_tokens"],
            timeout=runtime["architecture_llm"]["timeout"],
        )
    result = {
        "workspace_dir": project["workspace_dir"],
        "architecture_path": os.path.join(project["workspace_dir"], "Novel_architecture.txt"),
        "character_state_path": os.path.join(project["workspace_dir"], "character_state.txt"),
    }
    _progress(progress_callback, "generate:architecture", "Completed")
    return result


def generate_blueprint(project: dict, progress_callback=None) -> dict:
    _progress(progress_callback, "generate:blueprint", "加载运行时配置")
    runtime = get_runtime_config(project)
    modules = source_modules(project["source_root"])
    params = project["parameters"]
    defaults = project["chapter_defaults"]
    _progress(progress_callback, "generate:blueprint", "Calling model")
    with patched_adapters(project):
        _quiet_call(
            modules["novel_generator"].Chapter_blueprint_generate,
            interface_format=runtime["chapter_outline_llm"]["interface_format"],
            api_key=runtime["chapter_outline_llm"]["api_key"],
            base_url=runtime["chapter_outline_llm"]["base_url"],
            llm_model=runtime["chapter_outline_llm"]["model_name"],
            filepath=project["workspace_dir"],
            number_of_chapters=int(params["num_chapters"]),
            user_guidance=defaults["user_guidance"],
            temperature=runtime["chapter_outline_llm"]["temperature"],
            max_tokens=runtime["chapter_outline_llm"]["max_tokens"],
            timeout=runtime["chapter_outline_llm"]["timeout"],
        )
    result = {
        "workspace_dir": project["workspace_dir"],
        "blueprint_path": os.path.join(project["workspace_dir"], "Novel_directory.txt"),
    }
    _progress(progress_callback, "generate:blueprint", "Validating blueprint")
    result["blueprint_validation"] = validate_blueprint(project, require_complete=True)
    _progress(progress_callback, "generate:blueprint", "Completed")
    return result


def generate_chapter(project: dict, chapter_number: int, custom_prompt: str | None = None, progress_callback=None) -> dict:
    validated = validate_chapter_number(project, chapter_number, require_in_blueprint=True)
    chapter_number = validated["chapter_number"]
    _progress(progress_callback, "chapter:generate", f"第 {chapter_number} 章：加载运行时配置")
    runtime = get_runtime_config(project)
    modules = source_modules(project["source_root"])
    params = project["parameters"]
    defaults = project["chapter_defaults"]
    prompt_text = custom_prompt
    included_roles = []
    if prompt_text is None:
        _progress(progress_callback, "chapter:generate", f"Chapter {chapter_number}: Building prompt")
        prompt_payload = importlib.import_module("cli_anything.ai_novelgenerator.core.inspection").build_prompt(project, chapter_number)
        prompt_text = prompt_payload["prompt_text"]
        included_roles = prompt_payload.get("included_roles", [])
    else:
        injected = roles_mod.inject_role_library_into_prompt(project, prompt_text, defaults["characters_involved"])
        prompt_text = injected["prompt_text"]
        included_roles = injected["included_roles"]

    _progress(progress_callback, "chapter:generate", f"Chapter {chapter_number}: Calling model")
    with patched_adapters(project):
        text = _quiet_call(
            modules["novel_generator"].generate_chapter_draft,
            api_key=runtime["prompt_draft_llm"]["api_key"],
            base_url=runtime["prompt_draft_llm"]["base_url"],
            model_name=runtime["prompt_draft_llm"]["model_name"],
            filepath=project["workspace_dir"],
            novel_number=int(chapter_number),
            word_number=int(params["word_number"]),
            temperature=runtime["prompt_draft_llm"]["temperature"],
            user_guidance=defaults["user_guidance"],
            characters_involved=defaults["characters_involved"],
            key_items=defaults["key_items"],
            scene_location=defaults["scene_location"],
            time_constraint=defaults["time_constraint"],
            embedding_api_key=runtime["embedding"]["api_key"],
            embedding_url=runtime["embedding"]["base_url"],
            embedding_interface_format=runtime["embedding"]["interface_format"],
            embedding_model_name=runtime["embedding"]["model_name"],
            embedding_retrieval_k=int(defaults["embedding_retrieval_k"]),
            interface_format=runtime["prompt_draft_llm"]["interface_format"],
            max_tokens=runtime["prompt_draft_llm"]["max_tokens"],
            timeout=runtime["prompt_draft_llm"]["timeout"],
            custom_prompt_text=prompt_text,
        )
    output_path = _chapter_path(project, chapter_number)
    return {
        "chapter_number": int(chapter_number),
        "chapter_path": output_path,
        "text": text,
        "word_count": _word_count(project, text),
        "included_roles": included_roles,
        "prompt_text": prompt_text,
    }


def batch_generate_chapters(
    project: dict,
    start_chapter: int,
    end_chapter: int,
    finalize: bool = False,
    custom_prompt: str | None = None,
    skip_existing: bool = False,
    skip_drafts: bool = False,
    skip_finalized: bool = False,
    auto_enrich: bool = False,
    min_words: int | None = None,
    clamp_to_blueprint: bool = False,
    progress_callback=None,
) -> dict:
    if os.path.exists(_blueprint_path(project)):
        validate_blueprint(project, require_complete=not clamp_to_blueprint)
    range_info = _resolve_range(project, start_chapter, end_chapter, clamp_to_blueprint=clamp_to_blueprint)
    start = range_info["start_chapter"]
    end = range_info["end_chapter"]
    effective_skip_drafts = bool(skip_drafts or skip_existing)
    effective_skip_finalized = bool(skip_finalized or skip_existing)

    min_words_value = int(min_words) if min_words is not None else int(project["parameters"]["word_number"])
    if min_words_value < 0:
        raise RuntimeError("Minimum words must be zero or greater.")

    results = []
    total = max(0, end - start + 1)
    for chapter_number in range(start, end + 1):
        current = chapter_number - start + 1
        chapter_path = _chapter_path(project, chapter_number)
        _progress(progress_callback, "chapter:batch", f"检查第 {chapter_number} 章", current=current, total=total)
        skip_reason = _skip_reason(
            project,
            chapter_number,
            skip_drafts=effective_skip_drafts,
            skip_finalized=effective_skip_finalized,
        )
        if skip_reason is not None:
            reason_text = "Skipping finalized chapter" if skip_reason == "skipped_finalized" else "Skipping existing draft chapter"
            _progress(progress_callback, "chapter:batch", f"{reason_text}：第 {chapter_number} 章", current=current, total=total)
            results.append(
                {
                    "chapter_number": chapter_number,
                    "status": skip_reason,
                    "chapter_path": chapter_path,
                    "is_finalized": _is_finalized(project, chapter_number),
                }
            )
            continue

        _progress(progress_callback, "chapter:batch", f"生成第 {chapter_number} 章", current=current, total=total)
        draft = generate_chapter(project, chapter_number, custom_prompt=custom_prompt, progress_callback=progress_callback)
        chapter_result = {
            "chapter_number": chapter_number,
            "status": "generated",
            "generated": {
                "chapter_path": draft["chapter_path"],
                "word_count": draft["word_count"],
            },
        }
        if auto_enrich and draft["word_count"] < int(0.7 * min_words_value):
            _progress(progress_callback, "chapter:batch", f"扩写第 {chapter_number} 章", current=current, total=total)
            enriched = enrich_chapter(project, chapter_number, progress_callback=progress_callback)
            chapter_result["status"] = "generated_enriched"
            chapter_result["enriched"] = {
                "chapter_path": enriched["chapter_path"],
                "word_count": enriched["word_count"],
                "trigger_min_words": min_words_value,
                "trigger_threshold": 0.7,
            }
        if finalize:
            _progress(progress_callback, "chapter:batch", f"定稿第 {chapter_number} 章", current=current, total=total)
            finalized = finalize_chapter(project, chapter_number, progress_callback=progress_callback)
            chapter_result["finalized"] = {
                "chapter_path": finalized["chapter_path"],
                "global_summary_path": finalized["global_summary_path"],
                "character_state_path": finalized["character_state_path"],
                "vectorstore_dir": finalized["vectorstore_dir"],
            }
        results.append(chapter_result)
        _progress(progress_callback, "chapter:batch", f"Completed chapter {chapter_number}", current=current, total=total)

    return {
        "requested_start_chapter": range_info["requested_start_chapter"],
        "requested_end_chapter": range_info["requested_end_chapter"],
        "start_chapter": start,
        "end_chapter": end,
        "finalize": bool(finalize),
        "skip_existing": bool(skip_existing),
        "skip_drafts": effective_skip_drafts,
        "skip_finalized": effective_skip_finalized,
        "auto_enrich": bool(auto_enrich),
        "min_words": min_words_value,
        "clamp_to_blueprint": bool(clamp_to_blueprint),
        "clamped_to_blueprint": range_info["clamped_to_blueprint"],
        "blueprint_range": range_info["blueprint_range"],
        "chapter_count": len(results),
        "generated_count": sum(1 for item in results if item["status"].startswith("generated")),
        "skipped_count": sum(1 for item in results if item["status"].startswith("skipped_")),
        "skipped_draft_count": sum(1 for item in results if item["status"] == "skipped_draft"),
        "skipped_finalized_count": sum(1 for item in results if item["status"] == "skipped_finalized"),
        "enriched_count": sum(1 for item in results if item["status"] == "generated_enriched"),
        "chapters": results,
    }


def continue_batch_generate_chapters(
    project: dict,
    end_chapter: int,
    finalize: bool = False,
    custom_prompt: str | None = None,
    skip_existing: bool = True,
    skip_drafts: bool = False,
    skip_finalized: bool = False,
    auto_enrich: bool = False,
    min_words: int | None = None,
    search_start: int = 1,
    clamp_to_blueprint: bool = False,
    progress_callback=None,
) -> dict:
    if os.path.exists(_blueprint_path(project)):
        validate_blueprint(project, require_complete=not clamp_to_blueprint)
    effective_skip_drafts = bool(skip_drafts or skip_existing)
    effective_skip_finalized = bool(skip_finalized or skip_existing)
    _progress(progress_callback, "chapter:continue", "查找续跑起点")
    next_state = next_unfinished_chapter(
        project,
        start_chapter=search_start,
        end_chapter=end_chapter,
        skip_drafts=effective_skip_drafts,
        skip_finalized=effective_skip_finalized,
        clamp_to_blueprint=clamp_to_blueprint,
    )
    if not next_state["found"]:
        _progress(progress_callback, "chapter:continue", "No resumable chapter found")
        return {
            "resumed": False,
            "reason": "no_unfinished_chapter",
            "resume_reason": next_state["resume_reason"],
            "search_start": next_state["search_start"],
            "requested_end_chapter": next_state["requested_end_chapter"],
            "end_chapter": next_state["search_end"],
            "next_chapter": None,
            "clamped_to_blueprint": next_state["clamped_to_blueprint"],
            "blueprint_range": next_state["blueprint_range"],
            "skip_summary": next_state["skip_summary"],
            "result": None,
        }

    _progress(progress_callback, "chapter:continue", f"Continuing from chapter {next_state['chapter_number']}")
    batch_result = batch_generate_chapters(
        project,
        next_state["chapter_number"],
        end_chapter,
        finalize=finalize,
        custom_prompt=custom_prompt,
        skip_existing=skip_existing,
        skip_drafts=skip_drafts,
        skip_finalized=skip_finalized,
        auto_enrich=auto_enrich,
        min_words=min_words,
        clamp_to_blueprint=clamp_to_blueprint,
        progress_callback=progress_callback,
    )
    return {
        "resumed": True,
        "reason": "resumed_from_first_unskipped_chapter",
        "resume_reason": next_state["resume_reason"],
        "search_start": next_state["search_start"],
        "requested_end_chapter": next_state["requested_end_chapter"],
        "end_chapter": batch_result["end_chapter"],
        "next_chapter": next_state["chapter_number"],
        "clamped_to_blueprint": next_state["clamped_to_blueprint"],
        "blueprint_range": next_state["blueprint_range"],
        "skip_summary": next_state["skip_summary"],
        "result": batch_result,
    }


def finalize_chapter(project: dict, chapter_number: int, progress_callback=None) -> dict:
    chapter_number = validate_chapter_number(project, chapter_number, require_in_blueprint=True)["chapter_number"]
    _progress(progress_callback, "chapter:finalize", f"第 {chapter_number} 章：加载运行时配置")
    runtime = get_runtime_config(project)
    modules = source_modules(project["source_root"])
    params = project["parameters"]
    _progress(progress_callback, "chapter:finalize", f"Chapter {chapter_number}: Calling model")
    with patched_adapters(project):
        _quiet_call(
            modules["novel_generator"].finalize_chapter,
            novel_number=int(chapter_number),
            word_number=int(params["word_number"]),
            api_key=runtime["final_chapter_llm"]["api_key"],
            base_url=runtime["final_chapter_llm"]["base_url"],
            model_name=runtime["final_chapter_llm"]["model_name"],
            temperature=runtime["final_chapter_llm"]["temperature"],
            filepath=project["workspace_dir"],
            embedding_api_key=runtime["embedding"]["api_key"],
            embedding_url=runtime["embedding"]["base_url"],
            embedding_interface_format=runtime["embedding"]["interface_format"],
            embedding_model_name=runtime["embedding"]["model_name"],
            interface_format=runtime["final_chapter_llm"]["interface_format"],
            max_tokens=runtime["final_chapter_llm"]["max_tokens"],
            timeout=runtime["final_chapter_llm"]["timeout"],
        )
    chapter_state_path = _mark_finalized(project, chapter_number)
    _progress(progress_callback, "chapter:finalize", f"Chapter {chapter_number}: Completed")
    return {
        "chapter_number": int(chapter_number),
        "chapter_path": _chapter_path(project, chapter_number),
        "global_summary_path": os.path.join(project["workspace_dir"], "global_summary.txt"),
        "character_state_path": os.path.join(project["workspace_dir"], "character_state.txt"),
        "vectorstore_dir": os.path.join(project["workspace_dir"], "vectorstore"),
        "chapter_state_path": chapter_state_path,
    }


def enrich_chapter(project: dict, chapter_number: int, progress_callback=None) -> dict:
    chapter_number = validate_chapter_number(project, chapter_number, require_in_blueprint=True)["chapter_number"]
    _progress(progress_callback, "chapter:enrich", f"第 {chapter_number} 章：加载运行时配置")
    runtime = get_runtime_config(project)
    modules = source_modules(project["source_root"])
    params = project["parameters"]
    chapter_path = _chapter_path(project, chapter_number)
    with open(chapter_path, "r", encoding="utf-8") as handle:
        text = handle.read()
    _progress(progress_callback, "chapter:enrich", f"Chapter {chapter_number}: Calling model")
    with patched_adapters(project):
        enriched = _quiet_call(
            modules["novel_generator"].enrich_chapter_text,
            chapter_text=text,
            word_number=int(params["word_number"]),
            api_key=runtime["prompt_draft_llm"]["api_key"],
            base_url=runtime["prompt_draft_llm"]["base_url"],
            model_name=runtime["prompt_draft_llm"]["model_name"],
            temperature=runtime["prompt_draft_llm"]["temperature"],
            interface_format=runtime["prompt_draft_llm"]["interface_format"],
            max_tokens=runtime["prompt_draft_llm"]["max_tokens"],
            timeout=runtime["prompt_draft_llm"]["timeout"],
        )
    with open(chapter_path, "w", encoding="utf-8") as handle:
        handle.write(enriched)
    _progress(progress_callback, "chapter:enrich", f"Chapter {chapter_number}: Completed")
    return {
        "chapter_number": int(chapter_number),
        "chapter_path": chapter_path,
        "word_count": _word_count(project, enriched),
    }
