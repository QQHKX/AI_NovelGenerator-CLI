import json
import os
import shlex
import sys
from functools import wraps

import click

from cli_anything.ai_novelgenerator import __version__
from cli_anything.ai_novelgenerator.core import configuration as configuration_mod
from cli_anything.ai_novelgenerator.core import export as export_mod
from cli_anything.ai_novelgenerator.core import generation as generation_mod
from cli_anything.ai_novelgenerator.core import inspection as inspection_mod
from cli_anything.ai_novelgenerator.core import knowledge as knowledge_mod
from cli_anything.ai_novelgenerator.core import project as project_mod
from cli_anything.ai_novelgenerator.core import roles as roles_mod
from cli_anything.ai_novelgenerator.core import review as review_mod
from cli_anything.ai_novelgenerator.core import workspace as workspace_mod
from cli_anything.ai_novelgenerator.core.session import Session
from cli_anything.ai_novelgenerator.utils.ai_novelgenerator_backend import get_runtime_config
from cli_anything.ai_novelgenerator.utils.repl_skin import ReplSkin


_session = Session()
_json_output = False
_repl_mode = False


def _echo_text_safe(text: str, err: bool = False):
    try:
        click.echo(text, err=err)
    except UnicodeEncodeError:
        stream = sys.stderr if err else sys.stdout
        encoding = getattr(stream, "encoding", None) or "utf-8"
        stream.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace") + os.linesep)


def _emit(data, message: str = ""):
    if _json_output:
        click.echo(json.dumps(data, ensure_ascii=True, indent=2, default=str))
        return
    if message:
        _echo_text_safe(message)
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                _echo_text_safe(f"{key}: {json.dumps(value, ensure_ascii=False, indent=2)}")
            else:
                _echo_text_safe(f"{key}: {value}")
    elif isinstance(data, list):
        for item in data:
            _echo_text_safe(str(item))
    elif data is not None:
        _echo_text_safe(str(data))


def _emit_error(exc: Exception):
    payload = {"error": str(exc), "type": type(exc).__name__}
    if _json_output:
        click.echo(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        _echo_text_safe(f"Error: {exc}", err=True)
    if not _repl_mode:
        raise SystemExit(1)


def _handle_error(fn=None):
    def decorator(callback):
        @wraps(callback)
        def wrapper(*args, **kwargs):
            try:
                return callback(*args, **kwargs)
            except Exception as exc:
                _emit_error(exc)

        return wrapper

    if fn is None:
        return decorator
    return decorator(fn)


def _decorate_command_tree(command):
    """Apply the CLI error decorator across the Click command tree."""
    if getattr(command, "callback", None) is not None:
        callback = command.callback
        if not getattr(callback, "_cli_anything_error_wrapped", False):
            wrapped = _handle_error(callback)
            wrapped._cli_anything_error_wrapped = True
            command.callback = wrapped
    if isinstance(command, click.core.Group):
        for child in command.commands.values():
            _decorate_command_tree(child)


def _current_project_path(explicit: str | None) -> str:
    project_path = explicit or _session.data.get("current_project")
    if not project_path:
        raise RuntimeError("No project selected. Use --project or 'project open'.")
    return os.path.abspath(project_path)


def _load_project(explicit: str | None) -> tuple[str, dict]:
    project_path = _current_project_path(explicit)
    project = project_mod.load_project(project_path)
    return project_path, project


def _config_path_from(project_path: str | None, config_path: str | None) -> str:
    if config_path:
        return os.path.abspath(config_path)
    _, project = _load_project(project_path)
    return os.path.abspath(project["config_path"])


def _mutate_project(project_path: str, project: dict, command: str, fn):
    _session.checkpoint(project_path, project)
    result = fn(project)
    project_mod.save_project(project, project_path)
    _session.set_current_project(project_path)
    _session.add_history(command)
    return result


def _resolve_text_input(text: str | None, from_file: str | None) -> str:
    if bool(text) == bool(from_file):
        raise RuntimeError("Provide exactly one of --text or --from-file.")
    if from_file:
        with open(from_file, "r", encoding="utf-8") as handle:
            return handle.read()
    return text or ""


@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output machine-readable JSON")
@click.option("--project", "project_path", type=click.Path(), help="Project JSON path")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, use_json, project_path):
    global _json_output
    _json_output = use_json
    if project_path:
        _session.set_current_project(project_path)
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl, project_path=project_path)


@cli.group()
def project():
    """Project create/open/update/status commands."""


@click.option("--words", default=3000, type=int)
def project_new(output_path, workspace_dir, config_path, name, topic, genre, chapters, words):
    project_data = project_mod.create_project(
        output_path,
        name=name,
        workspace_dir=workspace_dir,
        config_path=config_path,
        topic=topic,
        genre=genre,
        num_chapters=chapters,
        word_number=words,
    )
    _session.set_current_project(output_path)
    _session.add_history(f"project new -o {output_path}")
    _emit(project_data, f"Created project: {output_path}")


@click.argument("project_path", type=click.Path(exists=True))
def project_open(project_path):
    data = project_mod.load_project(project_path)
    _session.set_current_project(project_path)
    _session.add_history(f"project open {project_path}")
    _emit({"project_path": os.path.abspath(project_path), "name": data["name"]}, f"Opened project: {project_path}")


@click.option("--time-constraint")
def project_set(project_path, topic, genre, chapters, words, guidance, characters, items, location, time_constraint):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        "project set",
        lambda p: project_mod.update_project(
            p,
            topic=topic,
            genre=genre,
            num_chapters=chapters,
            word_number=words,
            user_guidance=guidance,
            characters_involved=characters,
            key_items=items,
            scene_location=location,
            time_constraint=time_constraint,
        ),
    )
    _emit(result, "Updated project settings")


@click.option("--project", "project_path", type=click.Path())
def project_info(project_path):
    project_path, project_data = _load_project(project_path)
    payload = dict(project_data)
    payload["project_path"] = project_path
    _emit(payload)


@click.option("--project", "project_path", type=click.Path())
def project_status(project_path):
    _, project_data = _load_project(project_path)
    _emit(project_mod.project_status(project_data))


@click.option("--project", "project_path", type=click.Path())
def project_workspace(project_path):
    _, project_data = _load_project(project_path)
    _emit(project_mod.important_workspace_paths(project_data))


@cli.group()
def config():
    """Config inspection and profile binding."""


@click.option("--config-path", type=click.Path())
def config_show(project_path, config_path):
    if config_path:
        _emit(configuration_mod.config_summary(_config_path_from(project_path, config_path)))
        return
    _, project_data = _load_project(project_path)
    runtime = get_runtime_config(project_data)
    runtime["config_path"] = os.path.abspath(project_data["config_path"])
    runtime["choose_configs"] = configuration_mod.show_choose_configs(project_data["config_path"])["choose_configs"]
    _emit(runtime)


@click.option("--embedding")
def config_bind(project_path, architecture_llm, chapter_outline_llm, prompt_draft_llm, final_chapter_llm, consistency_review_llm, embedding):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        "config bind",
        lambda p: project_mod.update_project(
            p,
            architecture_llm=architecture_llm,
            chapter_outline_llm=chapter_outline_llm,
            prompt_draft_llm=prompt_draft_llm,
            final_chapter_llm=final_chapter_llm,
            consistency_review_llm=consistency_review_llm,
            embedding=embedding,
        ),
    )
    _emit(result, "Updated profile bindings")


@config.group("llm")
def config_llm():
    """LLM profile CRUD commands."""


@click.option("--config-path", type=click.Path())
def config_llm_list(project_path, config_path):
    _emit(configuration_mod.list_profiles(_config_path_from(project_path, config_path), "llm"))


@click.option("--config-path", type=click.Path())
def config_llm_show(name, project_path, config_path):
    _emit(configuration_mod.get_profile(_config_path_from(project_path, config_path), "llm", name))


@click.option("--interface-format", default="OpenAI")
def config_llm_create(name, project_path, config_path, api_key, base_url, model_name, temperature, max_tokens, timeout, interface_format):
    result = configuration_mod.create_profile(
        _config_path_from(project_path, config_path),
        "llm",
        name,
        {
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "interface_format": interface_format,
        },
    )
    _emit(result, f"Created LLM profile: {name}")


@click.option("--overwrite", is_flag=True)
def config_llm_import_file(name, project_path, config_path, from_file, overwrite):
    profile_data = json.loads(_resolve_text_input(None, from_file))
    result = configuration_mod.import_profile(
        _config_path_from(project_path, config_path),
        "llm",
        name,
        profile_data,
        overwrite=overwrite,
    )
    _emit(result, f"Imported LLM profile from file: {name}")


@click.option("--interface-format")
def config_llm_update(name, project_path, config_path, api_key, base_url, model_name, temperature, max_tokens, timeout, interface_format):
    result = configuration_mod.update_profile(
        _config_path_from(project_path, config_path),
        "llm",
        name,
        {
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "interface_format": interface_format,
        },
    )
    _emit(result, f"Updated LLM profile: {name}")


@click.option("--config-path", type=click.Path())
def config_llm_rename(old_name, new_name, project_path, config_path):
    result = configuration_mod.rename_profile(_config_path_from(project_path, config_path), "llm", old_name, new_name)
    _emit(result, f"Renamed LLM profile: {old_name} -> {new_name}")


@click.option("--config-path", type=click.Path())
def config_llm_delete(name, project_path, config_path):
    result = configuration_mod.delete_profile(_config_path_from(project_path, config_path), "llm", name)
    _emit(result, f"Deleted LLM profile: {name}")


@config.group("embedding")
def config_embedding():
    """Embedding profile CRUD commands."""


@click.option("--config-path", type=click.Path())
def config_embedding_list(project_path, config_path):
    _emit(configuration_mod.list_profiles(_config_path_from(project_path, config_path), "embedding"))


@click.option("--config-path", type=click.Path())
def config_embedding_show(name, project_path, config_path):
    _emit(configuration_mod.get_profile(_config_path_from(project_path, config_path), "embedding", name))


@click.option("--interface-format", default="OpenAI")
def config_embedding_create(name, project_path, config_path, api_key, base_url, model_name, retrieval_k, interface_format):
    result = configuration_mod.create_profile(
        _config_path_from(project_path, config_path),
        "embedding",
        name,
        {
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name,
            "retrieval_k": retrieval_k,
            "interface_format": interface_format,
        },
    )
    _emit(result, f"Created embedding profile: {name}")


@click.option("--overwrite", is_flag=True)
def config_embedding_import_file(name, project_path, config_path, from_file, overwrite):
    profile_data = json.loads(_resolve_text_input(None, from_file))
    result = configuration_mod.import_profile(
        _config_path_from(project_path, config_path),
        "embedding",
        name,
        profile_data,
        overwrite=overwrite,
    )
    _emit(result, f"Imported embedding profile from file: {name}")


@click.option("--interface-format")
def config_embedding_update(name, project_path, config_path, api_key, base_url, model_name, retrieval_k, interface_format):
    result = configuration_mod.update_profile(
        _config_path_from(project_path, config_path),
        "embedding",
        name,
        {
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_name,
            "retrieval_k": retrieval_k,
            "interface_format": interface_format,
        },
    )
    _emit(result, f"Updated embedding profile: {name}")


@click.option("--config-path", type=click.Path())
def config_embedding_rename(old_name, new_name, project_path, config_path):
    result = configuration_mod.rename_profile(_config_path_from(project_path, config_path), "embedding", old_name, new_name)
    _emit(result, f"Renamed embedding profile: {old_name} -> {new_name}")


@click.option("--config-path", type=click.Path())
def config_embedding_delete(name, project_path, config_path):
    result = configuration_mod.delete_profile(_config_path_from(project_path, config_path), "embedding", name)
    _emit(result, f"Deleted embedding profile: {name}")


@config.group("choose")
def config_choose():
    """Show and update selected config bindings in config.json."""


@click.option("--config-path", type=click.Path())
def config_choose_show(project_path, config_path):
    _emit(configuration_mod.show_choose_configs(_config_path_from(project_path, config_path)))


@click.option("--embedding")
def config_choose_set(project_path, config_path, architecture_llm, chapter_outline_llm, prompt_draft_llm, final_chapter_llm, consistency_review_llm, embedding):
    result = configuration_mod.set_choose_configs(
        _config_path_from(project_path, config_path),
        {
            "architecture_llm": architecture_llm,
            "chapter_outline_llm": chapter_outline_llm,
            "prompt_draft_llm": prompt_draft_llm,
            "final_chapter_llm": final_chapter_llm,
            "consistency_review_llm": consistency_review_llm,
            "embedding": embedding,
        },
    )
    _emit(result, "Updated choose configs")


@cli.group()
def generate():
    """Novel architecture and blueprint generation."""


@click.option("--project", "project_path", type=click.Path())
def generate_architecture(project_path):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        "generate architecture",
        lambda p: generation_mod.generate_architecture(p),
    )
    project_data.setdefault("last_outputs", {}).update(result)
    project_mod.save_project(project_data, project_path)
    _emit(result, "Generated architecture")


@click.option("--project", "project_path", type=click.Path())
def generate_blueprint(project_path):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        "generate blueprint",
        lambda p: generation_mod.generate_blueprint(p),
    )
    project_data.setdefault("last_outputs", {}).update(result)
    project_mod.save_project(project_data, project_path)
    _emit(result, "Generated blueprint")


@click.option("--project", "project_path", type=click.Path())
def generate_architecture_state(project_path):
    _, project_data = _load_project(project_path)
    _emit(inspection_mod.architecture_resume_state(project_data))


@cli.group()
def workspace():
    """Workspace text inspection and editing commands."""


@click.option("--project", "project_path", type=click.Path())
def workspace_show(target, project_path):
    _, project_data = _load_project(project_path)
    _emit(workspace_mod.workspace_text_info(project_data, target))


@cli.group()
def role():
    """Role-library inspection and mutation commands."""


@click.option("--project", "project_path", type=click.Path())
def role_categories(project_path):
    _, project_data = _load_project(project_path)
    _emit(roles_mod.list_categories(project_data))


@click.option("--project", "project_path", type=click.Path())
def role_category_create(category, project_path):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(project_path, project_data, f"role category-create {category}", lambda p: roles_mod.create_category(p, category))
    _emit(result, f"Created role category: {category}")


@click.option("--category", default="全部")
def role_list(project_path, category):
    _, project_data = _load_project(project_path)
    _emit(roles_mod.list_roles(project_data, category=category))


@click.option("--project", "project_path", type=click.Path())
def role_show(name, project_path):
    _, project_data = _load_project(project_path)
    _emit(roles_mod.get_role(project_data, name))


@click.option("--from-file", "from_file", type=click.Path(exists=True))
def role_create(name, project_path, category, text, from_file):
    role_text = None
    if text or from_file:
        role_text = _resolve_text_input(text, from_file)
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        f"role create {name}",
        lambda p: roles_mod.create_role(p, name, category=category, text=role_text),
    )
    _emit(result, f"Created role: {name}")


@click.option("--project", "project_path", type=click.Path())
def role_rename(old_name, new_name, project_path):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(project_path, project_data, f"role rename {old_name} {new_name}", lambda p: roles_mod.rename_role(p, old_name, new_name))
    _emit(result, f"Renamed role: {old_name} -> {new_name}")


@click.option("--project", "project_path", type=click.Path())
def role_delete(name, project_path):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(project_path, project_data, f"role delete {name}", lambda p: roles_mod.delete_role(p, name))
    _emit(result, f"Deleted role: {name}")


@click.option("--project", "project_path", type=click.Path())
def role_move(name, category, project_path):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(project_path, project_data, f"role move {name} {category}", lambda p: roles_mod.move_role(p, name, category))
    _emit(result, f"Moved role: {name} -> {category}")


@click.option("--category", default="全部")
def role_import_file(file_path, project_path, category):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        f"role import-file {file_path}",
        lambda p: roles_mod.import_roles_from_file(p, file_path, category=category),
    )
    _emit(result, f"Imported roles from file: {file_path}")


@click.option("--no-save-temp", is_flag=True)
def role_analyze_state(project_path, text, from_file, no_save_temp):
    _, project_data = _load_project(project_path)
    if not text and not from_file:
        from_file = os.path.join(project_data["workspace_dir"], "character_state.txt")
    result = roles_mod.analyze_character_state(project_data, text=text, from_file=from_file, save_to_temp=not no_save_temp)
    _session.add_history("role analyze-state")
    _emit(result, "Analyzed character state")


@click.option("--from-file", "from_file", type=click.Path(exists=True))
def role_import_state(project_path, category, from_file):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        "role import-state",
        lambda p: roles_mod.import_from_character_state(p, category=category, from_file=from_file),
    )
    _emit(result, "Imported roles from character_state")


@click.option("--from-file", "from_file", type=click.Path(exists=True))
def workspace_write(target, project_path, text, from_file):
    content = _resolve_text_input(text, from_file)
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        f"workspace write {target}",
        lambda p: workspace_mod.write_workspace_text(p, target, content),
    )
    project_data.setdefault("last_outputs", {})[target] = {
        "path": result["path"],
        "char_count": result["char_count"],
    }
    project_mod.save_project(project_data, project_path)
    _emit(result, f"Updated {target}")


@cli.group()
def chapter():
    """Chapter creation and inspection commands."""


@click.option("--prompt", "custom_prompt")
def chapter_generate(chapter_number, project_path, custom_prompt):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        f"chapter generate {chapter_number}",
        lambda p: generation_mod.generate_chapter(p, chapter_number, custom_prompt=custom_prompt),
    )
    project_data.setdefault("last_outputs", {}).update(result)
    project_mod.save_project(project_data, project_path)
    _emit(result, f"Generated chapter {chapter_number}")


@click.option("--prompt", "custom_prompt")
def chapter_batch(start_chapter, end_chapter, project_path, finalize_after_generate, skip_existing, skip_drafts, skip_finalized, clamp_to_blueprint, auto_enrich, min_words, custom_prompt):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        f"chapter batch {start_chapter} {end_chapter}",
        lambda p: generation_mod.batch_generate_chapters(
            p,
            start_chapter,
            end_chapter,
            finalize=finalize_after_generate,
            skip_existing=skip_existing,
            skip_drafts=skip_drafts,
            skip_finalized=skip_finalized,
            clamp_to_blueprint=clamp_to_blueprint,
            auto_enrich=auto_enrich,
            min_words=min_words,
            custom_prompt=custom_prompt,
        ),
    )
    project_data.setdefault("last_outputs", {})["batch"] = {
        "start_chapter": result["start_chapter"],
        "end_chapter": result["end_chapter"],
        "chapter_count": result["chapter_count"],
        "finalize": result["finalize"],
        "skip_existing": result["skip_existing"],
        "skip_drafts": result["skip_drafts"],
        "skip_finalized": result["skip_finalized"],
        "clamp_to_blueprint": result["clamp_to_blueprint"],
        "auto_enrich": result["auto_enrich"],
        "min_words": result["min_words"],
    }
    project_mod.save_project(project_data, project_path)
    _emit(result, f"Processed chapters {start_chapter}-{end_chapter}")


@click.option("--prompt", "custom_prompt")
def chapter_continue(end_chapter, project_path, search_start, finalize_after_generate, skip_existing, skip_drafts, skip_finalized, clamp_to_blueprint, auto_enrich, min_words, custom_prompt):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        f"chapter continue {end_chapter}",
        lambda p: generation_mod.continue_batch_generate_chapters(
            p,
            end_chapter,
            finalize=finalize_after_generate,
            custom_prompt=custom_prompt,
            skip_existing=skip_existing,
            skip_drafts=skip_drafts,
            skip_finalized=skip_finalized,
            clamp_to_blueprint=clamp_to_blueprint,
            auto_enrich=auto_enrich,
            min_words=min_words,
            search_start=search_start,
        ),
    )
    project_data.setdefault("last_outputs", {})["batch_continue"] = {
        "resumed": result["resumed"],
        "next_chapter": result["next_chapter"],
        "end_chapter": result["end_chapter"],
    }
    project_mod.save_project(project_data, project_path)
    if result["resumed"]:
        _emit(result, f"Continued batch generation from chapter {result['next_chapter']}")
    else:
        _emit(result, "No unfinished chapter found in the requested range")


@click.option("--project", "project_path", type=click.Path())
def chapter_finalize(chapter_number, project_path):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        f"chapter finalize {chapter_number}",
        lambda p: generation_mod.finalize_chapter(p, chapter_number),
    )
    project_data.setdefault("last_outputs", {}).update(result)
    project_mod.save_project(project_data, project_path)
    _emit(result, f"Finalized chapter {chapter_number}")


@click.option("--project", "project_path", type=click.Path())
def chapter_enrich(chapter_number, project_path):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        f"chapter enrich {chapter_number}",
        lambda p: generation_mod.enrich_chapter(p, chapter_number),
    )
    _emit(result, f"Enriched chapter {chapter_number}")


@click.option("--project", "project_path", type=click.Path())
def chapter_show(chapter_number, project_path):
    _, project_data = _load_project(project_path)
    result = workspace_mod.chapter_text_info(project_data, chapter_number)
    _emit(result)


@click.option("--from-file", "from_file", type=click.Path(exists=True))
def chapter_write(chapter_number, project_path, text, from_file):
    content = _resolve_text_input(text, from_file)
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        f"chapter write {chapter_number}",
        lambda p: workspace_mod.write_chapter_text(p, chapter_number, content),
    )
    project_data.setdefault("last_outputs", {})[f"chapter_{chapter_number}"] = {
        "path": result["path"],
        "char_count": result["char_count"],
    }
    project_mod.save_project(project_data, project_path)
    _emit(result, f"Updated chapter {chapter_number}")


@click.option("--project", "project_path", type=click.Path())
def chapter_list(project_path):
    _, project_data = _load_project(project_path)
    status = project_mod.project_status(project_data)
    _emit({"chapter_count": status["chapter_count"], "chapter_files": status["chapter_files"]})


@click.option("--project", "project_path", type=click.Path())
def chapter_status(chapter_number, project_path):
    _, project_data = _load_project(project_path)
    _emit(generation_mod.chapter_status(project_data, chapter_number))


@click.option("--clamp-to-blueprint", is_flag=True, help="Clamp the requested range to chapters present in Novel_directory.txt")
def chapter_scan(start_chapter, end_chapter, project_path, clamp_to_blueprint):
    _, project_data = _load_project(project_path)
    _emit(generation_mod.scan_chapter_statuses(project_data, start_chapter, end_chapter, clamp_to_blueprint=clamp_to_blueprint))


@click.option("--project", "project_path", type=click.Path())
def chapter_info(chapter_number, project_path):
    _, project_data = _load_project(project_path)
    _emit(inspection_mod.chapter_info(project_data, chapter_number))


@click.option("-o", "output_path", type=click.Path())
def chapter_prompt(chapter_number, project_path, output_path):
    _, project_data = _load_project(project_path)
    result = inspection_mod.build_prompt(project_data, chapter_number)
    if output_path:
        absolute_output = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(absolute_output), exist_ok=True)
        with open(absolute_output, "w", encoding="utf-8") as handle:
            handle.write(result["prompt_text"])
        result["output_path"] = absolute_output
    _session.add_history(f"chapter prompt {chapter_number}")
    _emit(result, f"Built prompt for chapter {chapter_number}")


@cli.group()
def knowledge():
    """Knowledge import and vector-store management."""


@click.option("--project", "project_path", type=click.Path())
def knowledge_import(file_path, project_path):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        f"knowledge import {file_path}",
        lambda p: knowledge_mod.import_knowledge(p, file_path),
    )
    _emit(result, f"Imported knowledge: {file_path}")


@click.option("--project", "project_path", type=click.Path())
def knowledge_clear(project_path):
    project_path, project_data = _load_project(project_path)
    result = _mutate_project(
        project_path,
        project_data,
        "knowledge clear",
        lambda p: knowledge_mod.clear_knowledge(p),
    )
    _emit(result, "Cleared vector store")


@click.option("--project", "project_path", type=click.Path())
def knowledge_status(project_path):
    _, project_data = _load_project(project_path)
    status = project_mod.project_status(project_data)
    _emit({"vectorstore_exists": status["vectorstore_exists"], "knowledge_files": status["knowledge_files"]})


@cli.group()
def review():
    """Consistency review commands."""


@click.option("--project", "project_path", type=click.Path())
def review_consistency(chapter_number, project_path):
    _, project_data = _load_project(project_path)
    result = review_mod.review_consistency(project_data, chapter_number)
    _session.add_history(f"review consistency {chapter_number}")
    _emit(result, f"Reviewed chapter {chapter_number}")


@click.option("--project", "project_path", type=click.Path())
def review_plot_arcs(project_path):
    _, project_data = _load_project(project_path)
    _emit(inspection_mod.plot_arcs_context(project_data))


@cli.group()
def export():
    """Bundle export commands."""


@click.option("--overwrite", is_flag=True)
def export_bundle(output_path, project_path, overwrite):
    project_path, project_data = _load_project(project_path)
    result = export_mod.export_bundle(project_data, project_path, output_path, overwrite=overwrite)
    project_data.setdefault("last_outputs", {}).update(result)
    project_mod.save_project(project_data, project_path)
    _session.add_history(f"export bundle {output_path}")
    _emit(result, f"Exported bundle: {output_path}")


@cli.group()
def session():
    """Persistent session state and undo/redo."""


@session.command("status")
def session_status():
    _emit(_session.status())


@click.argument("project_path", type=click.Path(exists=True))
def session_use(project_path):
    _session.set_current_project(project_path)
    _session.add_history(f"session use {project_path}")
    _emit({"current_project": os.path.abspath(project_path)})


@click.option("--project", "project_path", type=click.Path())
def session_undo(project_path):
    project_path, project_data = _load_project(project_path)
    result = _session.undo(project_path, project_data)
    _session.add_history("session undo")
    _emit(result, "Undo complete")


@click.option("--project", "project_path", type=click.Path())
def session_redo(project_path):
    project_path, project_data = _load_project(project_path)
    result = _session.redo(project_path, project_data)
    _session.add_history("session redo")
    _emit(result, "Redo complete")


@click.option("--project", "project_path", type=click.Path())
def repl(project_path):
    global _repl_mode
    _repl_mode = True
    skin = ReplSkin("ai_novelgenerator", version=__version__)
    skin.print_banner()
    prompt_session = skin.create_prompt_session()
    commands = {
        "project new/open/status": "Create or inspect projects",
        "generate architecture|blueprint|architecture-state": "Run planning stages or inspect resumable architecture state",
        "workspace show|write": "Inspect or edit core workspace files",
        "chapter generate|batch|continue|finalize|show|write": "Work with chapters",
        "review consistency|plot-arcs": "Check chapter consistency and inspect review context",
        "export bundle": "Write ZIP bundle",
        "session status|undo|redo": "Inspect or rewind state",
        "quit": "Exit the REPL",
    }
    while True:
        current = project_path or _session.data.get("current_project")
        context = os.path.basename(current) if current else "no-project"
        try:
            line = skin.get_input(prompt_session, context=context)
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line in {"quit", "exit"}:
            break
        if line == "help":
            skin.help(commands)
            continue
        try:
            args = shlex.split(line)
            cli.main(args=args, prog_name="cli-anything-ai-novelgenerator", standalone_mode=False)
        except SystemExit:
            continue
        except Exception as exc:
            skin.error(str(exc))
    skin.print_goodbye()
    _repl_mode = False


def _arg(name: str, **kwargs):
    return click.Argument([name], **kwargs)


def _opt(*param_decls, **kwargs):
    return click.Option(list(param_decls), **kwargs)


def _register_command(group, name: str, callback, params: list | None = None):
    command = click.Command(name=name, callback=_handle_error(callback), params=params or [], help=callback.__doc__)
    group.add_command(command)


_register_command(
    project,
    "new",
    project_new,
    [
        _opt("-o", "output_path", type=click.Path(), required=True),
        _opt("--workspace", "workspace_dir", type=click.Path(), required=True),
        _opt("--config", "config_path", type=click.Path(), required=True),
        _opt("--name", default="novel-project"),
        _opt("--topic", default=""),
        _opt("--genre", default=""),
        _opt("--chapters", default=10, type=int),
        _opt("--words", default=3000, type=int),
    ],
)
_register_command(project, "open", project_open, [_arg("project_path", type=click.Path(exists=True))])
_register_command(
    project,
    "set",
    project_set,
    [
        _opt("--project", "project_path", type=click.Path()),
        _opt("--topic"),
        _opt("--genre"),
        _opt("--chapters", type=int),
        _opt("--words", type=int),
        _opt("--guidance"),
        _opt("--characters"),
        _opt("--items"),
        _opt("--location"),
        _opt("--time-constraint"),
    ],
)
_register_command(project, "info", project_info, [_opt("--project", "project_path", type=click.Path())])
_register_command(project, "status", project_status, [_opt("--project", "project_path", type=click.Path())])
_register_command(project, "workspace", project_workspace, [_opt("--project", "project_path", type=click.Path())])

_register_command(config, "show", config_show, [_opt("--project", "project_path", type=click.Path()), _opt("--config-path", type=click.Path())])
_register_command(
    config,
    "bind",
    config_bind,
    [
        _opt("--project", "project_path", type=click.Path()),
        _opt("--architecture-llm"),
        _opt("--chapter-outline-llm"),
        _opt("--prompt-draft-llm"),
        _opt("--final-chapter-llm"),
        _opt("--consistency-review-llm"),
        _opt("--embedding"),
    ],
)
_register_command(config_llm, "list", config_llm_list, [_opt("--project", "project_path", type=click.Path()), _opt("--config-path", type=click.Path())])
_register_command(config_llm, "show", config_llm_show, [_arg("name"), _opt("--project", "project_path", type=click.Path()), _opt("--config-path", type=click.Path())])
_register_command(
    config_llm,
    "create",
    config_llm_create,
    [
        _arg("name"),
        _opt("--project", "project_path", type=click.Path()),
        _opt("--config-path", type=click.Path()),
        _opt("--api-key", default=""),
        _opt("--base-url", default=""),
        _opt("--model-name", default=""),
        _opt("--temperature", type=float, default=0.7),
        _opt("--max-tokens", type=int, default=4096),
        _opt("--timeout", type=int, default=600),
        _opt("--interface-format", default="OpenAI"),
    ],
)
_register_command(
    config_llm,
    "import-file",
    config_llm_import_file,
    [
        _arg("name"),
        _opt("--project", "project_path", type=click.Path()),
        _opt("--config-path", type=click.Path()),
        _opt("--from-file", "from_file", type=click.Path(exists=True), required=True),
        _opt("--overwrite", is_flag=True),
    ],
)
_register_command(
    config_llm,
    "update",
    config_llm_update,
    [
        _arg("name"),
        _opt("--project", "project_path", type=click.Path()),
        _opt("--config-path", type=click.Path()),
        _opt("--api-key"),
        _opt("--base-url"),
        _opt("--model-name"),
        _opt("--temperature", type=float),
        _opt("--max-tokens", type=int),
        _opt("--timeout", type=int),
        _opt("--interface-format"),
    ],
)
_register_command(config_llm, "rename", config_llm_rename, [_arg("old_name"), _arg("new_name"), _opt("--project", "project_path", type=click.Path()), _opt("--config-path", type=click.Path())])
_register_command(config_llm, "delete", config_llm_delete, [_arg("name"), _opt("--project", "project_path", type=click.Path()), _opt("--config-path", type=click.Path())])

_register_command(config_embedding, "list", config_embedding_list, [_opt("--project", "project_path", type=click.Path()), _opt("--config-path", type=click.Path())])
_register_command(config_embedding, "show", config_embedding_show, [_arg("name"), _opt("--project", "project_path", type=click.Path()), _opt("--config-path", type=click.Path())])
_register_command(
    config_embedding,
    "create",
    config_embedding_create,
    [
        _arg("name"),
        _opt("--project", "project_path", type=click.Path()),
        _opt("--config-path", type=click.Path()),
        _opt("--api-key", default=""),
        _opt("--base-url", default=""),
        _opt("--model-name", default=""),
        _opt("--retrieval-k", type=int, default=4),
        _opt("--interface-format", default="OpenAI"),
    ],
)
_register_command(
    config_embedding,
    "import-file",
    config_embedding_import_file,
    [
        _arg("name"),
        _opt("--project", "project_path", type=click.Path()),
        _opt("--config-path", type=click.Path()),
        _opt("--from-file", "from_file", type=click.Path(exists=True), required=True),
        _opt("--overwrite", is_flag=True),
    ],
)
_register_command(
    config_embedding,
    "update",
    config_embedding_update,
    [
        _arg("name"),
        _opt("--project", "project_path", type=click.Path()),
        _opt("--config-path", type=click.Path()),
        _opt("--api-key"),
        _opt("--base-url"),
        _opt("--model-name"),
        _opt("--retrieval-k", type=int),
        _opt("--interface-format"),
    ],
)
_register_command(config_embedding, "rename", config_embedding_rename, [_arg("old_name"), _arg("new_name"), _opt("--project", "project_path", type=click.Path()), _opt("--config-path", type=click.Path())])
_register_command(config_embedding, "delete", config_embedding_delete, [_arg("name"), _opt("--project", "project_path", type=click.Path()), _opt("--config-path", type=click.Path())])

_register_command(config_choose, "show", config_choose_show, [_opt("--project", "project_path", type=click.Path()), _opt("--config-path", type=click.Path())])
_register_command(
    config_choose,
    "set",
    config_choose_set,
    [
        _opt("--project", "project_path", type=click.Path()),
        _opt("--config-path", type=click.Path()),
        _opt("--architecture-llm"),
        _opt("--chapter-outline-llm"),
        _opt("--prompt-draft-llm"),
        _opt("--final-chapter-llm"),
        _opt("--consistency-review-llm"),
        _opt("--embedding"),
    ],
)

_register_command(generate, "architecture", generate_architecture, [_opt("--project", "project_path", type=click.Path())])
_register_command(generate, "blueprint", generate_blueprint, [_opt("--project", "project_path", type=click.Path())])
_register_command(generate, "architecture-state", generate_architecture_state, [_opt("--project", "project_path", type=click.Path())])

_register_command(workspace, "show", workspace_show, [_arg("target"), _opt("--project", "project_path", type=click.Path())])
_register_command(workspace, "write", workspace_write, [_arg("target"), _opt("--project", "project_path", type=click.Path()), _opt("--text"), _opt("--from-file", "from_file", type=click.Path(exists=True))])

_register_command(role, "categories", role_categories, [_opt("--project", "project_path", type=click.Path())])
_register_command(role, "category-create", role_category_create, [_arg("category"), _opt("--project", "project_path", type=click.Path())])
_register_command(role, "list", role_list, [_opt("--project", "project_path", type=click.Path()), _opt("--category", default="全部")])
_register_command(role, "show", role_show, [_arg("name"), _opt("--project", "project_path", type=click.Path())])
_register_command(role, "create", role_create, [_arg("name"), _opt("--project", "project_path", type=click.Path()), _opt("--category", default="全部"), _opt("--text"), _opt("--from-file", "from_file", type=click.Path(exists=True))])
_register_command(role, "rename", role_rename, [_arg("old_name"), _arg("new_name"), _opt("--project", "project_path", type=click.Path())])
_register_command(role, "delete", role_delete, [_arg("name"), _opt("--project", "project_path", type=click.Path())])
_register_command(role, "move", role_move, [_arg("name"), _arg("category"), _opt("--project", "project_path", type=click.Path())])
_register_command(role, "import-file", role_import_file, [_arg("file_path", type=click.Path(exists=True)), _opt("--project", "project_path", type=click.Path()), _opt("--category", default="全部")])
_register_command(role, "analyze-state", role_analyze_state, [_opt("--project", "project_path", type=click.Path()), _opt("--text"), _opt("--from-file", "from_file", type=click.Path(exists=True)), _opt("--no-save-temp", is_flag=True)])
_register_command(role, "import-state", role_import_state, [_opt("--project", "project_path", type=click.Path()), _opt("--category", default="全部"), _opt("--from-file", "from_file", type=click.Path(exists=True))])

_register_command(chapter, "generate", chapter_generate, [_arg("chapter_number", type=int), _opt("--project", "project_path", type=click.Path()), _opt("--prompt", "custom_prompt")])
_register_command(chapter, "batch", chapter_batch, [_arg("start_chapter", type=int), _arg("end_chapter", type=int), _opt("--project", "project_path", type=click.Path()), _opt("--finalize", "finalize_after_generate", is_flag=True), _opt("--skip-existing", is_flag=True), _opt("--skip-drafts", is_flag=True), _opt("--skip-finalized", is_flag=True), _opt("--clamp-to-blueprint", is_flag=True, help="Clamp the requested range to chapters present in Novel_directory.txt"), _opt("--auto-enrich", is_flag=True), _opt("--min-words", type=int), _opt("--prompt", "custom_prompt")])
_register_command(chapter, "continue", chapter_continue, [_arg("end_chapter", type=int), _opt("--project", "project_path", type=click.Path()), _opt("--search-start", type=int, default=1), _opt("--finalize", "finalize_after_generate", is_flag=True), _opt("--skip-existing/--no-skip-existing", default=True), _opt("--skip-drafts", is_flag=True), _opt("--skip-finalized", is_flag=True), _opt("--clamp-to-blueprint", is_flag=True), _opt("--auto-enrich", is_flag=True), _opt("--min-words", type=int), _opt("--prompt", "custom_prompt")])
_register_command(chapter, "finalize", chapter_finalize, [_arg("chapter_number", type=int), _opt("--project", "project_path", type=click.Path())])
_register_command(chapter, "enrich", chapter_enrich, [_arg("chapter_number", type=int), _opt("--project", "project_path", type=click.Path())])
_register_command(chapter, "show", chapter_show, [_arg("chapter_number", type=int), _opt("--project", "project_path", type=click.Path())])
_register_command(chapter, "write", chapter_write, [_arg("chapter_number", type=int), _opt("--project", "project_path", type=click.Path()), _opt("--text"), _opt("--from-file", "from_file", type=click.Path(exists=True))])
_register_command(chapter, "list", chapter_list, [_opt("--project", "project_path", type=click.Path())])
_register_command(chapter, "status", chapter_status, [_arg("chapter_number", type=int), _opt("--project", "project_path", type=click.Path())])
_register_command(chapter, "scan", chapter_scan, [_arg("start_chapter", type=int), _arg("end_chapter", type=int), _opt("--project", "project_path", type=click.Path()), _opt("--clamp-to-blueprint", is_flag=True, help="Clamp the requested range to chapters present in Novel_directory.txt")])
_register_command(chapter, "info", chapter_info, [_arg("chapter_number", type=int), _opt("--project", "project_path", type=click.Path())])
_register_command(chapter, "prompt", chapter_prompt, [_arg("chapter_number", type=int), _opt("--project", "project_path", type=click.Path()), _opt("-o", "output_path", type=click.Path())])

_register_command(knowledge, "import", knowledge_import, [_arg("file_path", type=click.Path(exists=True)), _opt("--project", "project_path", type=click.Path())])
_register_command(knowledge, "clear", knowledge_clear, [_opt("--project", "project_path", type=click.Path())])
_register_command(knowledge, "status", knowledge_status, [_opt("--project", "project_path", type=click.Path())])

_register_command(review, "consistency", review_consistency, [_arg("chapter_number", type=int), _opt("--project", "project_path", type=click.Path())])
_register_command(review, "plot-arcs", review_plot_arcs, [_opt("--project", "project_path", type=click.Path())])

_register_command(export, "bundle", export_bundle, [_arg("output_path", type=click.Path()), _opt("--project", "project_path", type=click.Path()), _opt("--overwrite", is_flag=True)])

_register_command(session, "use", session_use, [_arg("project_path", type=click.Path(exists=True))])
_register_command(session, "undo", session_undo, [_opt("--project", "project_path", type=click.Path())])
_register_command(session, "redo", session_redo, [_opt("--project", "project_path", type=click.Path())])

cli.add_command(click.Command("repl", callback=_handle_error(repl), params=[_opt("--project", "project_path", type=click.Path())]))


_decorate_command_tree(cli)


def main():
    cli()


if __name__ == "__main__":
    main()

