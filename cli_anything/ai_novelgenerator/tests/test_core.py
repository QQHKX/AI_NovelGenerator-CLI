import json
import zipfile
from pathlib import Path

import pytest

from cli_anything.ai_novelgenerator.core import export as export_mod
from cli_anything.ai_novelgenerator.core import configuration as configuration_mod
from cli_anything.ai_novelgenerator.core import inspection as inspection_mod
from cli_anything.ai_novelgenerator.core import generation as generation_mod
from cli_anything.ai_novelgenerator.core import project as project_mod
from cli_anything.ai_novelgenerator.core import roles as roles_mod
from cli_anything.ai_novelgenerator.core import review as review_mod
from cli_anything.ai_novelgenerator.core import workspace as workspace_mod
from cli_anything.ai_novelgenerator.core.session import Session, capture_workspace_snapshot, restore_workspace_snapshot
from cli_anything.ai_novelgenerator.utils.ai_novelgenerator_backend import HarnessMockLLM, get_runtime_config, source_modules


def write_mock_config(path: Path) -> Path:
    data = {
        "llm_configs": {
            "MockLLM": {
                "api_key": "mock",
                "base_url": "mock://llm",
                "model_name": "mock-model",
                "temperature": 0.1,
                "max_tokens": 2048,
                "timeout": 30,
                "interface_format": "HarnessMock",
            }
        },
        "embedding_configs": {
            "MockEmbedding": {
                "api_key": "mock",
                "base_url": "mock://embedding",
                "model_name": "mock-embedding",
                "retrieval_k": 4,
                "interface_format": "HarnessMock",
            }
        },
        "choose_configs": {
            "prompt_draft_llm": "MockLLM",
            "chapter_outline_llm": "MockLLM",
            "architecture_llm": "MockLLM",
            "final_chapter_llm": "MockLLM",
            "consistency_review_llm": "MockLLM",
        },
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def make_project(tmp_path: Path):
    config_path = write_mock_config(tmp_path / "config.json")
    project_path = tmp_path / "project.json"
    workspace = tmp_path / "workspace"
    project = project_mod.create_project(
        str(project_path),
        name="unit-test",
        workspace_dir=str(workspace),
        config_path=str(config_path),
        topic="记忆之城",
        genre="科幻",
        num_chapters=3,
        word_number=1200,
    )
    return project_path, workspace, project


def test_create_project_writes_expected_shape(tmp_path):
    project_path, workspace, project = make_project(tmp_path)
    assert project_path.exists()
    assert workspace.exists()
    assert project["parameters"]["topic"] == "记忆之城"
    assert project["software"] == "AI_NovelGenerator"


def test_load_and_update_project(tmp_path):
    project_path, _, _ = make_project(tmp_path)
    project = project_mod.load_project(str(project_path))
    updated = project_mod.update_project(project, topic="新主题", user_guidance="更黑暗")
    project_mod.save_project(updated, str(project_path))
    reloaded = project_mod.load_project(str(project_path))
    assert reloaded["parameters"]["topic"] == "新主题"
    assert reloaded["chapter_defaults"]["user_guidance"] == "更黑暗"


def test_project_status_counts_workspace_files(tmp_path):
    _, workspace, project = make_project(tmp_path)
    (workspace / "Novel_architecture.txt").write_text("arch", encoding="utf-8")
    chapters = workspace / "chapters"
    chapters.mkdir()
    (chapters / "chapter_1.txt").write_text("chapter", encoding="utf-8")
    status = project_mod.project_status(project)
    assert status["architecture"]["exists"] is True
    assert status["chapter_count"] == 1
    assert status["chapter_state_counts"]["draft"] == 1
    assert status["finalized_chapter_count"] == 0
    assert status["next_action"] == "generate_blueprint"


def test_important_workspace_paths(tmp_path):
    _, workspace, project = make_project(tmp_path)
    paths = project_mod.important_workspace_paths(project)
    assert paths["workspace_dir"] == str(workspace)
    assert paths["chapters_dir"].endswith("chapters")


def test_capture_and_restore_workspace_snapshot(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "a.txt").write_text("alpha", encoding="utf-8")
    nested = workspace / "chapters"
    nested.mkdir()
    (nested / "chapter_1.txt").write_text("beta", encoding="utf-8")
    snap = capture_workspace_snapshot(str(workspace))
    (workspace / "a.txt").write_text("changed", encoding="utf-8")
    restore_workspace_snapshot(str(workspace), snap)
    assert (workspace / "a.txt").read_text(encoding="utf-8") == "alpha"


def test_session_undo_and_redo_restore_project(tmp_path):
    project_path, workspace, project = make_project(tmp_path)
    session = Session(path=tmp_path / "session.json")
    (workspace / "Novel_architecture.txt").write_text("one", encoding="utf-8")
    session.checkpoint(str(project_path), project)
    project["parameters"]["topic"] = "changed"
    project_mod.save_project(project, str(project_path))
    (workspace / "Novel_architecture.txt").write_text("two", encoding="utf-8")
    restored = session.undo(str(project_path), project)
    restored_project = project_mod.load_project(restored["project_path"])
    assert restored_project["parameters"]["topic"] == "记忆之城"
    assert (workspace / "Novel_architecture.txt").read_text(encoding="utf-8") == "one"
    session.redo(restored["project_path"], restored_project)
    assert project_mod.load_project(str(project_path))["parameters"]["topic"] == "changed"


def test_export_bundle_writes_valid_zip(tmp_path):
    project_path, workspace, project = make_project(tmp_path)
    (workspace / "Novel_architecture.txt").write_text("arch", encoding="utf-8")
    bundle = tmp_path / "bundle.zip"
    result = export_mod.export_bundle(project, str(project_path), str(bundle), overwrite=True)
    assert bundle.exists()
    assert result["format"] == "zip"
    with zipfile.ZipFile(bundle) as archive:
        assert "manifest.json" in archive.namelist()
        assert "project.json" in archive.namelist()


def test_project_compat_wrappers_return_expected_metadata(tmp_path):
    project_path, workspace, created = make_project(tmp_path)
    opened = project_mod.open(str(project_path))
    assert opened["project_path"] == str(project_path.resolve())

    created_via_wrapper = project_mod.create(
        str(tmp_path / "project-compat.json"),
        name="compat",
        workspace_dir=str(tmp_path / "workspace-compat"),
        config_path=str(tmp_path / "config.json"),
    )
    assert created_via_wrapper["name"] == "compat"

    info = project_mod.info(created, str(project_path))
    assert info["project_path"] == str(project_path.resolve())
    assert "status" in info
    assert info["important_paths"]["workspace_dir"] == str(workspace)

    saved = project_mod.save(created, str(project_path))
    assert saved["saved"] is True
    assert saved["project_path"] == str(project_path.resolve())


def test_project_list_profiles_groups_project_bound_slots(tmp_path):
    _, _, project = make_project(tmp_path)
    project_mod.update_project(project, architecture_llm="MockLLM", embedding="MockEmbedding")
    profiles = project_mod.list_profiles(project)
    assert profiles["profiles"]["architecture_llm"] == "MockLLM"
    assert profiles["profile_groups"]["embedding"][0]["selected"] == "MockEmbedding"


def test_export_render_compat_uses_bundle_preset(tmp_path):
    project_path, workspace, project = make_project(tmp_path)
    (workspace / "Novel_architecture.txt").write_text("arch", encoding="utf-8")
    output = tmp_path / "render.zip"
    result = export_mod.render(project, str(project_path), str(output), preset="bundle", overwrite=True)
    assert output.exists()
    assert result["preset"] == "bundle"
    assert result["requested_preset"] == "bundle"
    assert export_mod.EXPORT_PRESETS["bundle"]["format"] == "zip"


def test_export_render_rejects_unknown_preset(tmp_path):
    project_path, _, project = make_project(tmp_path)
    with pytest.raises(RuntimeError, match="Unsupported export preset"):
        export_mod.render(project, str(project_path), str(tmp_path / "out.zip"), preset="pdf", overwrite=True)


def test_runtime_config_resolves_mock_profiles(tmp_path):
    _, _, project = make_project(tmp_path)
    runtime = get_runtime_config(project)
    assert runtime["architecture_llm"]["interface_format"] == "HarnessMock"
    assert runtime["embedding"]["interface_format"] == "HarnessMock"


def test_config_profile_crud_and_choose_persist_to_json(tmp_path):
    config_path = write_mock_config(tmp_path / "config.json")

    created = configuration_mod.create_profile(
        str(config_path),
        "llm",
        "MockLLM2",
        {
            "api_key": "k2",
            "base_url": "mock://llm2",
            "model_name": "mock-model-2",
            "temperature": 0.2,
            "max_tokens": 3072,
            "timeout": 45,
            "interface_format": "HarnessMock",
        },
    )
    assert created["name"] == "MockLLM2"
    assert created["config"]["model_name"] == "mock-model-2"

    updated = configuration_mod.update_profile(str(config_path), "llm", "MockLLM2", {"temperature": 0.55, "timeout": 90})
    assert updated["config"]["temperature"] == 0.55
    assert updated["config"]["timeout"] == 90

    renamed = configuration_mod.rename_profile(str(config_path), "llm", "MockLLM2", "StoryLLM")
    assert renamed["name"] == "StoryLLM"

    embedding_created = configuration_mod.create_profile(
        str(config_path),
        "embedding",
        "MockEmbedding2",
        {
            "api_key": "ek2",
            "base_url": "mock://embedding2",
            "model_name": "mock-embedding-2",
            "retrieval_k": 8,
            "interface_format": "HarnessMock",
        },
    )
    assert embedding_created["config"]["retrieval_k"] == 8

    choose = configuration_mod.set_choose_configs(
        str(config_path),
        {
            "architecture_llm": "StoryLLM",
            "chapter_outline_llm": "StoryLLM",
            "prompt_draft_llm": "StoryLLM",
            "final_chapter_llm": "StoryLLM",
            "consistency_review_llm": "StoryLLM",
            "embedding": "MockEmbedding2",
        },
    )
    assert choose["choose_configs"]["embedding"] == "MockEmbedding2"

    with pytest.raises(RuntimeError, match="Cannot delete selected llm profile"):
        configuration_mod.delete_profile(str(config_path), "llm", "StoryLLM")

    configuration_mod.set_choose_configs(
        str(config_path),
        {
            "architecture_llm": "MockLLM",
            "chapter_outline_llm": "MockLLM",
            "prompt_draft_llm": "MockLLM",
            "final_chapter_llm": "MockLLM",
            "consistency_review_llm": "MockLLM",
            "embedding": "MockEmbedding",
        },
    )
    deleted_llm = configuration_mod.delete_profile(str(config_path), "llm", "StoryLLM")
    deleted_embedding = configuration_mod.delete_profile(str(config_path), "embedding", "MockEmbedding2")
    assert deleted_llm["deleted"] is True
    assert deleted_embedding["deleted"] is True

    reloaded = json.loads(config_path.read_text(encoding="utf-8"))
    assert "StoryLLM" not in reloaded["llm_configs"]
    assert "MockEmbedding2" not in reloaded["embedding_configs"]
    assert reloaded["choose_configs"]["architecture_llm"] == "MockLLM"
    assert reloaded["choose_configs"]["embedding"] == "MockEmbedding"


def test_config_rename_updates_selected_choose_slots(tmp_path):
    config_path = write_mock_config(tmp_path / "config.json")
    configuration_mod.create_profile(
        str(config_path),
        "embedding",
        "EmbedA",
        {
            "api_key": "ea",
            "base_url": "mock://embed-a",
            "model_name": "embed-a",
            "retrieval_k": 6,
            "interface_format": "HarnessMock",
        },
    )
    configuration_mod.set_choose_configs(str(config_path), {"embedding": "EmbedA"})
    renamed = configuration_mod.rename_profile(str(config_path), "embedding", "EmbedA", "EmbedB")
    assert renamed["name"] == "EmbedB"
    choose = configuration_mod.show_choose_configs(str(config_path))
    assert choose["choose_configs"]["embedding"] == "EmbedB"


def test_config_import_profile_preserves_extra_metadata_fields(tmp_path):
    config_path = write_mock_config(tmp_path / "config.json")
    llm_profile = {
        "id": "llm-123",
        "api_key": "k-meta",
        "base_url": "mock://meta-llm",
        "model_name": "meta-model",
        "temperature": 0.33,
        "max_tokens": 16384,
        "timeout": 120,
        "interface_format": "HarnessMock",
        "created_at": "2026-05-01T12:00:00",
        "updated_at": "2026-05-02T12:00:00",
    }
    embedding_profile = {
        "id": "embed-123",
        "api_key": "ek-meta",
        "base_url": "mock://meta-embedding",
        "model_name": "meta-embed-model",
        "retrieval_k": 9,
        "interface_format": "HarnessMock",
        "created_at": "2026-05-01T12:00:00",
    }

    imported_llm = configuration_mod.import_profile(str(config_path), "llm", "MetaLLM", llm_profile)
    imported_embedding = configuration_mod.import_profile(str(config_path), "embedding", "MetaEmbedding", embedding_profile)

    assert imported_llm["imported"] is True
    assert imported_llm["config"]["id"] == "llm-123"
    assert imported_llm["config"]["created_at"] == "2026-05-01T12:00:00"
    assert imported_embedding["config"]["id"] == "embed-123"
    assert imported_embedding["config"]["created_at"] == "2026-05-01T12:00:00"

    overwritten = configuration_mod.import_profile(
        str(config_path),
        "llm",
        "MetaLLM",
        {**llm_profile, "model_name": "meta-model-v2", "updated_at": "2026-05-03T12:00:00"},
        overwrite=True,
    )
    assert overwritten["overwrote_existing"] is True
    assert overwritten["config"]["model_name"] == "meta-model-v2"
    assert overwritten["config"]["updated_at"] == "2026-05-03T12:00:00"


def test_harness_mock_llm_blueprint_response_is_parseable():
    llm = HarnessMockLLM()
    text = llm.invoke("设计3章的节奏分布\n本章定位")
    assert "第1章 - [章节1]" in text


def test_chapter_info_parses_blueprint_entry(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    result = inspection_mod.chapter_info(project, 1)
    assert result["chapter_info"]["chapter_number"] == 1
    assert result["chapter_info"]["chapter_title"] == "章节1"
    assert result["blueprint_exists"] is True


def test_build_prompt_returns_chapter_context(tmp_path):
    _, _, project = make_project(tmp_path)
    knowledge_file = tmp_path / "knowledge.txt"
    knowledge_file.write_text("遗迹回声会干扰记忆读取。", encoding="utf-8")
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.generate_chapter(project, 1)
    generation_mod.finalize_chapter(project, 1)
    from cli_anything.ai_novelgenerator.core import knowledge as knowledge_mod

    knowledge_mod.import_knowledge(project, str(knowledge_file))
    result = inspection_mod.build_prompt(project, 2)
    assert result["chapter_number"] == 2
    assert "第2章" in result["prompt_text"]
    assert result["recent_chapter_files"]
    assert isinstance(result["knowledge_files"], list)


def test_role_library_crud_and_move(tmp_path):
    _, _, project = make_project(tmp_path)
    roles_mod.create_category(project, "配角")
    created = roles_mod.create_role(project, "林雾", category="全部")
    assert created["name"] == "林雾"
    assert created["category"] == "全部"
    renamed = roles_mod.rename_role(project, "林雾", "林雾主")
    assert renamed["name"] == "林雾主"
    moved = roles_mod.move_role(project, "林雾主", "配角")
    assert moved["category"] == "配角"
    listing = roles_mod.list_roles(project, "配角")
    assert listing["role_count"] == 1
    deleted = roles_mod.delete_role(project, "林雾主")
    assert deleted["deleted"] is True
    assert roles_mod.list_roles(project, "配角")["role_count"] == 0


def test_import_roles_from_file_parses_multiple_entries(tmp_path):
    _, _, project = make_project(tmp_path)
    import_file = tmp_path / "roles.txt"
    import_file.write_text(
        "林雾：\n├──物品：\n│  ├──残卷: 会自我改写\n├──能力：\n│  ├──修复: 拼接档案\n├──状态：\n│  ├──身体状态: 稳定\n│  ├──心理状态: 警觉\n├──主要角色间关系网：\n│  ├──沈砚: 盟友\n├──触发或加深的事件：\n│  ├──收到残卷: 导火索\n\n沈砚：\n├──物品：\n│  ├──记录仪: 追踪信号\n├──能力：\n│  ├──追踪: 锁定异常\n├──状态：\n│  ├──身体状态: 轻伤\n│  ├──心理状态: 审慎\n├──主要角色间关系网：\n│  ├──林雾: 合作者\n├──触发或加深的事件：\n│  ├──遗迹追踪: 结盟",
        encoding="utf-8",
    )
    result = roles_mod.import_roles_from_file(project, str(import_file), category="全部")
    assert result["imported_count"] == 2
    assert roles_mod.role_exists(project, "林雾") is True
    assert roles_mod.role_exists(project, "沈砚") is True


def test_analyze_and_import_roles_from_character_state(tmp_path):
    _, workspace, project = make_project(tmp_path)
    character_state = workspace / "character_state.txt"
    character_state.write_text("林雾与沈砚在遗迹调查中建立合作。", encoding="utf-8")
    analyzed = roles_mod.analyze_character_state(project, from_file=str(character_state))
    assert analyzed["analyzed_role_count"] == 2
    assert Path(project["workspace_dir"], "角色库", "临时角色库", "林雾.txt").exists()
    imported = roles_mod.import_from_character_state(project, category="主角组", from_file=str(character_state))
    assert imported["imported_count"] == 2
    assert Path(project["workspace_dir"], "角色库", "主角组", "林雾.txt").exists()


def test_build_prompt_injects_role_library_content(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.generate_chapter(project, 1)
    generation_mod.finalize_chapter(project, 1)
    roles_mod.create_role(
        project,
        "林雾",
        attributes={
            "物品": ["残卷: 会自我改写的古老文稿"],
            "能力": ["修复: 擅长拼接破损档案"],
            "状态": ["身体状态: 疲惫但稳定", "心理状态: 强烈追索真相"],
            "主要角色间关系网": ["沈砚: 互相试探的盟友"],
            "触发或加深的事件": ["收到残卷: 故事导火索"],
        },
    )
    project["chapter_defaults"]["characters_involved"] = "林雾"
    result = inspection_mod.build_prompt(project, 2)
    assert result["included_roles"] == ["林雾"]
    assert "残卷: 会自我改写的古老文稿" in result["prompt_text"]
    assert "核心人物" in result["prompt_text"]


def test_generate_chapter_reports_included_roles(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    roles_mod.create_role(project, "林雾", attributes={"物品": ["残卷: 文稿"], "能力": [], "状态": [], "主要角色间关系网": [], "触发或加深的事件": []})
    project["chapter_defaults"]["characters_involved"] = "林雾"
    result = generation_mod.generate_chapter(project, 1)
    assert result["included_roles"] == ["林雾"]
    assert "残卷: 文稿" in result["prompt_text"]


def test_architecture_resume_state_reports_partial_progress(tmp_path):
    _, workspace, project = make_project(tmp_path)
    partial = {
        "core_seed_result": "seed",
        "character_dynamics_result": "characters",
        "character_state_result": "state",
    }
    (workspace / "partial_architecture.json").write_text(json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8")
    result = inspection_mod.architecture_resume_state(project)
    assert result["partial_architecture_exists"] is True
    assert result["resume_available"] is True
    assert result["state"] == "in_progress"
    assert result["completed_steps"] == ["core_seed", "character_dynamics", "character_state"]
    assert result["next_step"] == "world_building"
    assert result["raw_data"] == partial


def test_plot_arcs_context_reads_review_context(tmp_path):
    _, workspace, project = make_project(tmp_path)
    (workspace / "plot_arcs.txt").write_text("线索A\n冲突B\n", encoding="utf-8")
    result = inspection_mod.plot_arcs_context(project)
    assert result["exists"] is True
    assert result["review_context_ready"] is True
    assert result["line_count"] == 2
    assert "冲突B" in result["text"]


def test_review_consistency_includes_plot_arcs_context(tmp_path, monkeypatch):
    _, workspace, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.generate_chapter(project, 1)
    generation_mod.finalize_chapter(project, 1)
    (workspace / "plot_arcs.txt").write_text("未解决：密钥去向", encoding="utf-8")

    captured = {}
    modules = source_modules(project["source_root"])
    original = modules["consistency_checker"].check_consistency

    def fake_check_consistency(**kwargs):
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(modules["consistency_checker"], "check_consistency", fake_check_consistency)
    result = review_mod.review_consistency(project, 1)
    assert result["plot_arcs_included"] is True
    assert result["plot_arcs_path"].endswith("plot_arcs.txt")
    assert captured["plot_arcs"] == "未解决：密钥去向"
    assert result["result"] == "ok"
    monkeypatch.setattr(modules["consistency_checker"], "check_consistency", original)


def test_batch_generate_chapters_can_finalize_range(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    result = generation_mod.batch_generate_chapters(project, 1, 2, finalize=True)
    assert result["chapter_count"] == 2
    assert result["finalize"] is True
    assert result["chapters"][0]["chapter_number"] == 1
    assert result["chapters"][1]["chapter_number"] == 2
    assert "finalized" in result["chapters"][0]
    assert Path(result["chapters"][0]["generated"]["chapter_path"]).exists()
    assert Path(result["chapters"][1]["generated"]["chapter_path"]).exists()


def test_batch_generate_chapters_can_skip_existing(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    first = generation_mod.generate_chapter(project, 1)
    result = generation_mod.batch_generate_chapters(project, 1, 2, skip_existing=True)
    assert result["skip_existing"] is True
    assert result["skipped_count"] == 1
    assert result["generated_count"] == 1
    assert result["chapters"][0]["status"] == "skipped_draft"
    assert result["chapters"][0]["chapter_path"] == first["chapter_path"]
    assert result["chapters"][1]["status"].startswith("generated")


def test_batch_generate_chapters_can_clamp_to_blueprint_range(tmp_path):
    _, workspace, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    (workspace / "Novel_directory.txt").write_text(
        "第2章 - [章节2]\n本章定位：[推进]\n\n第3章 - [章节3]\n本章定位：[收束]\n",
        encoding="utf-8",
    )

    result = generation_mod.batch_generate_chapters(project, 1, 3, clamp_to_blueprint=True)
    assert result["requested_start_chapter"] == 1
    assert result["requested_end_chapter"] == 3
    assert result["start_chapter"] == 2
    assert result["end_chapter"] == 3
    assert result["clamped_to_blueprint"] is True
    assert result["blueprint_range"]["chapter_numbers"] == [2, 3]
    assert Path(project["workspace_dir"], "chapters", "chapter_2.txt").exists()
    assert Path(project["workspace_dir"], "chapters", "chapter_3.txt").exists()


def test_batch_generate_chapters_distinguishes_draft_and_finalized_skips(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.generate_chapter(project, 1)
    generation_mod.generate_chapter(project, 2)
    generation_mod.finalize_chapter(project, 2)

    result = generation_mod.batch_generate_chapters(project, 1, 3, skip_drafts=True, skip_finalized=True)
    assert result["skip_drafts"] is True
    assert result["skip_finalized"] is True
    assert result["skipped_count"] == 2
    assert result["skipped_draft_count"] == 1
    assert result["skipped_finalized_count"] == 1
    assert result["chapters"][0]["status"] == "skipped_draft"
    assert result["chapters"][1]["status"] == "skipped_finalized"
    assert result["chapters"][1]["is_finalized"] is True
    assert result["chapters"][2]["status"].startswith("generated")


def test_batch_generate_chapters_can_auto_enrich_low_word_drafts(tmp_path, monkeypatch):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)

    original_generate = generation_mod.generate_chapter
    original_enrich = generation_mod.enrich_chapter

    def fake_generate(project_data, chapter_number, custom_prompt=None):
        result = original_generate(project_data, chapter_number, custom_prompt=custom_prompt)
        Path(result["chapter_path"]).write_text("短稿", encoding="utf-8")
        result["text"] = "短稿"
        result["word_count"] = 2
        return result

    def fake_enrich(project_data, chapter_number):
        chapter_path = Path(project_data["workspace_dir"]) / "chapters" / f"chapter_{chapter_number}.txt"
        chapter_path.write_text("扩写后章节内容", encoding="utf-8")
        return {
            "chapter_number": chapter_number,
            "chapter_path": str(chapter_path),
            "word_count": len("扩写后章节内容"),
        }

    monkeypatch.setattr(generation_mod, "generate_chapter", fake_generate)
    monkeypatch.setattr(generation_mod, "enrich_chapter", fake_enrich)
    result = generation_mod.batch_generate_chapters(project, 1, 1, auto_enrich=True, min_words=10)
    assert result["auto_enrich"] is True
    assert result["min_words"] == 10
    assert result["enriched_count"] == 1
    assert result["chapters"][0]["status"] == "generated_enriched"
    assert result["chapters"][0]["enriched"]["trigger_min_words"] == 10
    assert result["chapters"][0]["enriched"]["word_count"] > result["chapters"][0]["generated"]["word_count"]


def test_next_unfinished_and_continue_batch_generation(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.generate_chapter(project, 1)
    next_state = generation_mod.next_unfinished_chapter(project, start_chapter=1, end_chapter=3)
    assert next_state["found"] is True
    assert next_state["chapter_number"] == 2

    result = generation_mod.continue_batch_generate_chapters(project, 3, search_start=1)
    assert result["resumed"] is True
    assert result["reason"] == "resumed_from_first_unskipped_chapter"
    assert result["next_chapter"] == 2
    assert result["skip_summary"]["skipped_count"] == 1
    assert result["skip_summary"]["skipped_draft_count"] == 1
    assert result["skip_summary"]["skipped_chapters"][0]["chapter_number"] == 1
    assert "first chapter in range" in result["resume_reason"]
    assert result["result"]["start_chapter"] == 2
    assert Path(project["workspace_dir"], "chapters", "chapter_2.txt").exists()
    assert Path(project["workspace_dir"], "chapters", "chapter_3.txt").exists()


def test_continue_batch_generation_can_clamp_and_skip_finalized(tmp_path):
    _, workspace, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    (workspace / "Novel_directory.txt").write_text(
        "第2章 - [章节2]\n本章定位：[推进]\n\n第3章 - [章节3]\n本章定位：[收束]\n",
        encoding="utf-8",
    )
    generation_mod.generate_chapter(project, 2)
    generation_mod.finalize_chapter(project, 2)

    result = generation_mod.continue_batch_generate_chapters(
        project,
        3,
        search_start=1,
        skip_finalized=True,
        clamp_to_blueprint=True,
    )
    assert result["resumed"] is True
    assert result["clamped_to_blueprint"] is True
    assert result["next_chapter"] == 3
    assert result["skip_summary"]["skipped_finalized_count"] == 1
    assert result["skip_summary"]["skipped_chapters"][0]["reason"] == "skipped_finalized"
    assert result["result"]["start_chapter"] == 3
    assert result["result"]["end_chapter"] == 3
    assert Path(project["workspace_dir"], "chapters", "chapter_3.txt").exists()


def test_continue_batch_generation_reports_when_no_chapter_can_resume(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.batch_generate_chapters(project, 1, 3, finalize=True)

    result = generation_mod.continue_batch_generate_chapters(project, 3, search_start=1)
    assert result["resumed"] is False
    assert result["reason"] == "no_unfinished_chapter"
    assert result["skip_summary"]["skipped_count"] == 3
    assert result["skip_summary"]["skipped_finalized_count"] == 3
    assert "No chapter in the requested range" in result["resume_reason"]


def test_chapter_status_and_scan_report_missing_draft_finalized(tmp_path):
    _, workspace, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    (workspace / "Novel_directory.txt").write_text(
        "第2章 - [章节2]\n本章定位：[推进]\n\n第3章 - [章节3]\n本章定位：[收束]\n",
        encoding="utf-8",
    )
    generation_mod.generate_chapter(project, 1)
    generation_mod.generate_chapter(project, 2)
    generation_mod.finalize_chapter(project, 2)

    chapter_one = generation_mod.chapter_status(project, 1)
    chapter_two = generation_mod.chapter_status(project, 2)
    chapter_three = generation_mod.chapter_status(project, 3)
    assert chapter_one["state"] == "draft"
    assert chapter_two["state"] == "finalized"
    assert chapter_three["state"] == "missing"

    scan = generation_mod.scan_chapter_statuses(project, 1, 3)
    assert scan["draft_count"] == 1
    assert scan["finalized_count"] == 1
    assert scan["missing_count"] == 1
    assert [item["state"] for item in scan["chapters"]] == ["draft", "finalized", "missing"]

    clamped_scan = generation_mod.scan_chapter_statuses(project, 1, 3, clamp_to_blueprint=True)
    assert clamped_scan["start_chapter"] == 2
    assert clamped_scan["clamped_to_blueprint"] is True
    assert [item["state"] for item in clamped_scan["chapters"]] == ["finalized", "missing"]


def test_project_status_reports_finalized_chapter_summary(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.generate_chapter(project, 1)
    generation_mod.generate_chapter(project, 2)
    generation_mod.finalize_chapter(project, 2)
    roles_mod.create_category(project, "主角组")
    roles_mod.create_role(project, "林雾", category="主角组")
    project["chapter_defaults"]["characters_involved"] = "林雾,沈砚"

    status = project_mod.project_status(project)
    assert status["chapter_states"]["exists"] is True
    assert status["finalized_chapter_count"] == 1
    assert status["finalized_chapters"] == [2]
    assert status["chapter_state_counts"] == {"missing": 1, "draft": 1, "finalized": 1}
    assert status["next_action"] == "generate_chapter"
    assert status["recommended_next_chapter"] == 3
    assert status["role_library"]["category_count"] == 2
    assert status["role_library"]["categories"] == ["全部", "主角组"]
    assert status["role_library"]["role_count"] == 1
    assert status["role_library"]["roles"] == ["林雾"]
    assert status["role_library"]["available_requested_characters"] == ["林雾"]
    assert status["role_library"]["missing_requested_characters"] == ["沈砚"]


def test_project_status_recommends_generate_blueprint_before_chapters(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)

    status = project_mod.project_status(project)
    assert status["next_action"] == "generate_blueprint"
    assert status["recommended_next_chapter"] is None


def test_project_status_recommends_finalizing_existing_draft(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.generate_chapter(project, 1)

    status = project_mod.project_status(project)
    assert status["next_action"] == "generate_chapter"
    assert status["recommended_next_chapter"] == 2

    generation_mod.generate_chapter(project, 2)
    generation_mod.generate_chapter(project, 3)
    followup_status = project_mod.project_status(project)
    assert followup_status["next_action"] == "finalize_chapter"
    assert followup_status["recommended_next_chapter"] == 1


def test_project_status_reports_complete_when_all_chapters_finalized(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.batch_generate_chapters(project, 1, 3, finalize=True)

    status = project_mod.project_status(project)
    assert status["next_action"] == "project_complete"
    assert status["recommended_next_chapter"] is None


def test_workspace_text_info_and_write_roundtrip(tmp_path):
    _, _, project = make_project(tmp_path)
    written = workspace_mod.write_workspace_text(project, "architecture", "人工修订后的架构")
    shown = workspace_mod.workspace_text_info(project, "architecture")
    assert written["exists"] is True
    assert written["char_count"] > 0
    assert shown["text"] == "人工修订后的架构"
    assert shown["target"] == "architecture"


def test_write_chapter_text_creates_editable_chapter_file(tmp_path):
    _, _, project = make_project(tmp_path)
    result = workspace_mod.write_chapter_text(project, 2, "第2章人工修订版")
    shown = workspace_mod.chapter_text_info(project, 2)
    assert result["chapter_number"] == 2
    assert Path(result["path"]).exists()
    assert shown["text"] == "第2章人工修订版"
