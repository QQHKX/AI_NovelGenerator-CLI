import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from cli_anything.ai_novelgenerator.core import export as export_mod
from cli_anything.ai_novelgenerator.core import generation as generation_mod
from cli_anything.ai_novelgenerator.core import inspection as inspection_mod
from cli_anything.ai_novelgenerator.core import knowledge as knowledge_mod
from cli_anything.ai_novelgenerator.core import project as project_mod
from cli_anything.ai_novelgenerator.core import review as review_mod


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
        name="e2e-test",
        workspace_dir=str(workspace),
        config_path=str(config_path),
        topic="记忆之城",
        genre="科幻",
        num_chapters=3,
        word_number=1200,
    )
    return project_path, workspace, project


def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev.

    Set env CLI_ANYTHING_FORCE_INSTALLED=1 to require the installed command.
    """
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    suffix = name.replace("cli-anything-", "").replace("-", "_")
    module = f"cli_anything.{suffix}.{suffix}_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


def test_full_pipeline_with_real_source_modules(tmp_path):
    project_path, workspace, project = make_project(tmp_path)
    knowledge_file = tmp_path / "knowledge.txt"
    knowledge_file.write_text("遗迹中藏着一枚会共振的钥匙。", encoding="utf-8")

    arch = generation_mod.generate_architecture(project)
    assert Path(arch["architecture_path"]).exists()
    assert Path(arch["character_state_path"]).exists()

    blueprint = generation_mod.generate_blueprint(project)
    blueprint_path = Path(blueprint["blueprint_path"])
    assert blueprint_path.exists()
    assert "第1章 - [章节1]" in blueprint_path.read_text(encoding="utf-8")

    draft = generation_mod.generate_chapter(project, 1)
    assert Path(draft["chapter_path"]).exists()
    assert draft["word_count"] > 0

    knowledge_mod.import_knowledge(project, str(knowledge_file))
    final = generation_mod.finalize_chapter(project, 1)
    assert Path(final["global_summary_path"]).exists()
    assert Path(final["character_state_path"]).exists()
    assert Path(final["vectorstore_dir"]).exists()

    review = review_mod.review_consistency(project, 1)
    assert "无明显冲突" in review["result"]

    bundle = export_mod.export_bundle(project, str(project_path), str(tmp_path / "artifact.zip"), overwrite=True)
    assert Path(bundle["output"]).exists()
    with open(bundle["output"], "rb") as handle:
        assert handle.read(4) == b"PK\x03\x04"
    print(f"\n  ZIP: {bundle['output']} ({bundle['file_size']:,} bytes)")


def test_project_status_after_pipeline(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.generate_chapter(project, 1)
    status = project_mod.project_status(project)
    assert status["architecture"]["exists"] is True
    assert status["blueprint"]["exists"] is True
    assert status["chapter_count"] == 1
    assert status["next_action"] == "generate_chapter"
    assert status["recommended_next_chapter"] == 2


def test_export_bundle_contains_manifest(tmp_path):
    project_path, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    out = tmp_path / "bundle.zip"
    export_mod.export_bundle(project, str(project_path), str(out), overwrite=True)
    with zipfile.ZipFile(out) as archive:
        assert "manifest.json" in archive.namelist()


def test_prompt_inspection_after_first_chapter(tmp_path):
    _, _, project = make_project(tmp_path)
    knowledge_file = tmp_path / "knowledge.txt"
    knowledge_file.write_text("钟楼遗迹会放大记忆残响。", encoding="utf-8")

    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.generate_chapter(project, 1)
    generation_mod.finalize_chapter(project, 1)
    knowledge_mod.import_knowledge(project, str(knowledge_file))

    info = inspection_mod.chapter_info(project, 2)
    prompt = inspection_mod.build_prompt(project, 2)
    assert info["chapter_info"]["chapter_number"] == 2
    assert prompt["chapter_info"]["chapter_number"] == 2
    assert prompt["next_chapter_info"]["chapter_number"] == 3
    assert "第2章" in prompt["prompt_text"]
    assert prompt["recent_chapter_files"]


def test_batch_generation_workflow_creates_multiple_chapters(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    result = generation_mod.batch_generate_chapters(project, 1, 2, finalize=True)
    assert result["chapter_count"] == 2
    assert result["finalize"] is True
    assert Path(project["workspace_dir"], "chapters", "chapter_1.txt").exists()
    assert Path(project["workspace_dir"], "chapters", "chapter_2.txt").exists()
    assert Path(project["workspace_dir"], "global_summary.txt").exists()


def test_batch_generation_can_resume_from_next_chapter(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    generation_mod.generate_chapter(project, 1)
    result = generation_mod.continue_batch_generate_chapters(project, 3)
    assert result["resumed"] is True
    assert result["next_chapter"] == 2
    assert result["result"]["generated_count"] == 2
    assert Path(project["workspace_dir"], "chapters", "chapter_2.txt").exists()
    assert Path(project["workspace_dir"], "chapters", "chapter_3.txt").exists()


def test_architecture_resume_and_plot_arcs_inspection(tmp_path):
    _, workspace, project = make_project(tmp_path)
    partial = {
        "core_seed_result": "seed",
        "character_dynamics_result": "characters",
    }
    (workspace / "partial_architecture.json").write_text(json.dumps(partial, ensure_ascii=False, indent=2), encoding="utf-8")
    (workspace / "plot_arcs.txt").write_text("未解决冲突：地下机枢层的门为何提前开启", encoding="utf-8")

    resume_state = inspection_mod.architecture_resume_state(project)
    plot_arcs = inspection_mod.plot_arcs_context(project)
    assert resume_state["resume_available"] is True
    assert resume_state["next_step"] == "character_state"
    assert plot_arcs["review_context_ready"] is True
    assert "地下机枢层" in plot_arcs["text"]


def test_workspace_text_editing_roundtrip(tmp_path):
    _, _, project = make_project(tmp_path)
    generation_mod.generate_architecture(project)
    generation_mod.generate_blueprint(project)
    from cli_anything.ai_novelgenerator.core import workspace as workspace_mod

    architecture = workspace_mod.write_workspace_text(project, "architecture", "修订后的设定大纲")
    blueprint = workspace_mod.write_workspace_text(project, "blueprint", "修订后的章节蓝图")
    chapter = workspace_mod.write_chapter_text(project, 1, "第1章人工改稿")
    assert architecture["text"] == "修订后的设定大纲"
    assert blueprint["text"] == "修订后的章节蓝图"
    assert chapter["text"] == "第1章人工改稿"
    assert Path(chapter["path"]).exists()


class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-ai-novelgenerator")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "project" in result.stdout

    def test_full_workflow_json(self, tmp_path):
        config_path = write_mock_config(tmp_path / "config.json")
        project_path = tmp_path / "project.json"
        workspace = tmp_path / "workspace"
        bundle = tmp_path / "bundle.zip"

        result = self._run(
            [
                "--json",
                "project",
                "new",
                "-o",
                str(project_path),
                "--workspace",
                str(workspace),
                "--config",
                str(config_path),
                "--topic",
                "记忆之城",
                "--genre",
                "科幻",
                "--chapters",
                "3",
                "--words",
                "1200",
            ]
        )
        data = json.loads(result.stdout)
        assert data["name"] == "novel-project"

        self._run(["--project", str(project_path), "generate", "architecture"])
        self._run(["--project", str(project_path), "generate", "blueprint"])
        self._run(["--project", str(project_path), "chapter", "generate", "1"])
        self._run(["--project", str(project_path), "chapter", "finalize", "1"])
        result = self._run(["--json", "--project", str(project_path), "export", "bundle", str(bundle), "--overwrite"])
        export_data = json.loads(result.stdout)
        assert Path(export_data["output"]).exists()
        with open(export_data["output"], "rb") as handle:
            assert handle.read(4) == b"PK\x03\x04"
        print(f"\n  ZIP: {export_data['output']} ({export_data['file_size']:,} bytes)")

    def test_prompt_commands_json(self, tmp_path):
        config_path = write_mock_config(tmp_path / "config.json")
        project_path = tmp_path / "project.json"
        workspace = tmp_path / "workspace"
        prompt_path = tmp_path / "chapter-2-prompt.txt"

        self._run(
            [
                "project",
                "new",
                "-o",
                str(project_path),
                "--workspace",
                str(workspace),
                "--config",
                str(config_path),
                "--topic",
                "记忆之城",
                "--genre",
                "科幻",
                "--chapters",
                "3",
                "--words",
                "1200",
            ]
        )
        self._run(["--project", str(project_path), "generate", "architecture"])
        self._run(["--project", str(project_path), "generate", "blueprint"])
        self._run(["--project", str(project_path), "chapter", "generate", "1"])
        self._run(["--project", str(project_path), "chapter", "finalize", "1"])

        info_result = self._run(["--json", "--project", str(project_path), "chapter", "info", "2"])
        info_data = json.loads(info_result.stdout)
        assert info_data["chapter_info"]["chapter_number"] == 2

        prompt_result = self._run(
            ["--json", "--project", str(project_path), "chapter", "prompt", "2", "-o", str(prompt_path)]
        )
        prompt_data = json.loads(prompt_result.stdout)
        assert prompt_data["chapter_number"] == 2
        assert prompt_data["output_path"] == str(prompt_path.resolve())
        assert prompt_path.exists()
        assert "第2章" in prompt_path.read_text(encoding="utf-8")

    def test_batch_generate_json(self, tmp_path):
        config_path = write_mock_config(tmp_path / "config.json")
        project_path = tmp_path / "project.json"
        workspace = tmp_path / "workspace"

        self._run(
            [
                "project",
                "new",
                "-o",
                str(project_path),
                "--workspace",
                str(workspace),
                "--config",
                str(config_path),
                "--topic",
                "记忆之城",
                "--genre",
                "科幻",
                "--chapters",
                "3",
                "--words",
                "1200",
            ]
        )
        self._run(["--project", str(project_path), "generate", "architecture"])
        self._run(["--project", str(project_path), "generate", "blueprint"])

        result = self._run(
            ["--json", "--project", str(project_path), "chapter", "batch", "1", "2", "--finalize"]
        )
        data = json.loads(result.stdout)
        assert data["chapter_count"] == 2
        assert data["finalize"] is True
        assert Path(data["chapters"][0]["generated"]["chapter_path"]).exists()
        assert Path(data["chapters"][1]["generated"]["chapter_path"]).exists()

    def test_role_library_workflow_and_prompt_injection_json(self, tmp_path):
        config_path = write_mock_config(tmp_path / "config.json")
        project_path = tmp_path / "project.json"
        workspace = tmp_path / "workspace"
        import_file = tmp_path / "roles.txt"
        state_file = workspace / "character_state.txt"
        import_file.write_text(
            "林雾：\n├──物品：\n│  ├──残卷: 会自我改写\n├──能力：\n│  ├──修复: 拼接档案\n├──状态：\n│  ├──身体状态: 稳定\n│  ├──心理状态: 警觉\n├──主要角色间关系网：\n│  ├──沈砚: 盟友\n├──触发或加深的事件：\n│  ├──收到残卷: 导火索",
            encoding="utf-8",
        )

        self._run(
            [
                "project", "new", "-o", str(project_path), "--workspace", str(workspace), "--config", str(config_path),
                "--topic", "记忆之城", "--genre", "科幻", "--chapters", "3", "--words", "1200",
            ]
        )
        self._run(["--project", str(project_path), "role", "category-create", "主角组"])
        self._run(["--project", str(project_path), "role", "create", "林雾", "--category", "主角组"])
        self._run(["--project", str(project_path), "role", "rename", "林雾", "林雾主"])
        self._run(["--project", str(project_path), "role", "move", "林雾主", "全部"])
        self._run(["--project", str(project_path), "role", "delete", "林雾主"])
        import_result = self._run(["--json", "--project", str(project_path), "role", "import-file", str(import_file), "--category", "主角组"])
        import_data = json.loads(import_result.stdout)
        assert import_data["imported_count"] == 1

        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text("林雾与沈砚在遗迹调查中建立合作。", encoding="utf-8")
        analyze_result = self._run(["--json", "--project", str(project_path), "role", "analyze-state"])
        analyze_data = json.loads(analyze_result.stdout)
        assert analyze_data["analyzed_role_count"] == 2
        assert Path(workspace, "角色库", "临时角色库", "林雾.txt").exists()

        import_state_result = self._run(["--json", "--project", str(project_path), "role", "import-state", "--category", "分析导入"])
        import_state_data = json.loads(import_state_result.stdout)
        assert import_state_data["imported_count"] >= 1

        self._run(["--project", str(project_path), "project", "set", "--characters", "林雾"])
        self._run(["--project", str(project_path), "generate", "architecture"])
        self._run(["--project", str(project_path), "generate", "blueprint"])
        prompt_result = self._run(["--json", "--project", str(project_path), "chapter", "prompt", "1"])
        prompt_data = json.loads(prompt_result.stdout)
        assert prompt_data["included_roles"] == ["林雾"]
        assert "残卷: 会自我改写" in prompt_data["prompt_text"]

        chapter_result = self._run(["--json", "--project", str(project_path), "chapter", "generate", "1"])
        chapter_data = json.loads(chapter_result.stdout)
        assert chapter_data["included_roles"] == ["林雾"]
        assert Path(chapter_data["chapter_path"]).exists()

    def test_batch_continue_and_skip_existing_json(self, tmp_path):
        config_path = write_mock_config(tmp_path / "config.json")
        project_path = tmp_path / "project.json"
        workspace = tmp_path / "workspace"

        self._run(
            [
                "project",
                "new",
                "-o",
                str(project_path),
                "--workspace",
                str(workspace),
                "--config",
                str(config_path),
                "--topic",
                "记忆之城",
                "--genre",
                "科幻",
                "--chapters",
                "3",
                "--words",
                "1200",
            ]
        )
        self._run(["--project", str(project_path), "generate", "architecture"])
        self._run(["--project", str(project_path), "generate", "blueprint"])
        self._run(["--project", str(project_path), "chapter", "generate", "1"])

        continue_result = self._run(
            ["--json", "--project", str(project_path), "chapter", "continue", "3", "--finalize"]
        )
        continue_data = json.loads(continue_result.stdout)
        assert continue_data["resumed"] is True
        assert continue_data["reason"] == "resumed_from_first_unskipped_chapter"
        assert continue_data["next_chapter"] == 2
        assert continue_data["skip_summary"]["skipped_count"] == 1
        assert continue_data["skip_summary"]["skipped_chapters"][0]["reason"] == "skipped_draft"
        assert continue_data["result"]["start_chapter"] == 2
        assert Path(workspace, "chapters", "chapter_2.txt").exists()
        assert Path(workspace, "chapters", "chapter_3.txt").exists()

        batch_result = self._run(
            ["--json", "--project", str(project_path), "chapter", "batch", "1", "3", "--skip-existing"]
        )
        batch_data = json.loads(batch_result.stdout)
        assert batch_data["skip_existing"] is True
        assert batch_data["skipped_count"] == 3
        assert batch_data["skipped_draft_count"] == 1
        assert batch_data["skipped_finalized_count"] == 2
        assert [item["status"] for item in batch_data["chapters"]] == [
            "skipped_draft",
            "skipped_finalized",
            "skipped_finalized",
        ]

    def test_batch_clamp_and_distinct_skip_modes_json(self, tmp_path):
        config_path = write_mock_config(tmp_path / "config.json")
        project_path = tmp_path / "project.json"
        workspace = tmp_path / "workspace"

        self._run(
            [
                "project",
                "new",
                "-o",
                str(project_path),
                "--workspace",
                str(workspace),
                "--config",
                str(config_path),
                "--topic",
                "记忆之城",
                "--genre",
                "科幻",
                "--chapters",
                "3",
                "--words",
                "1200",
            ]
        )
        self._run(["--project", str(project_path), "generate", "architecture"])
        (workspace / "Novel_directory.txt").write_text(
            "第2章 - [章节2]\n本章定位：[推进]\n\n第3章 - [章节3]\n本章定位：[收束]\n",
            encoding="utf-8",
        )

        clamp_result = self._run(
            [
                "--json",
                "--project",
                str(project_path),
                "chapter",
                "batch",
                "1",
                "3",
                "--clamp-to-blueprint",
            ]
        )
        clamp_data = json.loads(clamp_result.stdout)
        assert clamp_data["requested_start_chapter"] == 1
        assert clamp_data["start_chapter"] == 2
        assert clamp_data["end_chapter"] == 3
        assert clamp_data["clamped_to_blueprint"] is True

        self._run(["--project", str(project_path), "chapter", "finalize", "2"])
        skip_result = self._run(
            [
                "--json",
                "--project",
                str(project_path),
                "chapter",
                "batch",
                "1",
                "3",
                "--skip-drafts",
                "--skip-finalized",
            ]
        )
        skip_data = json.loads(skip_result.stdout)
        assert skip_data["skipped_draft_count"] == 1
        assert skip_data["skipped_finalized_count"] == 1
        assert skip_data["generated_count"] == 1
        assert [item["status"] for item in skip_data["chapters"]] == [
            "generated",
            "skipped_finalized",
            "skipped_draft",
        ]

    def test_resume_and_review_context_commands_json(self, tmp_path):
        config_path = write_mock_config(tmp_path / "config.json")
        project_path = tmp_path / "project.json"
        workspace = tmp_path / "workspace"

        self._run(
            [
                "project",
                "new",
                "-o",
                str(project_path),
                "--workspace",
                str(workspace),
                "--config",
                str(config_path),
                "--topic",
                "记忆之城",
                "--genre",
                "科幻",
                "--chapters",
                "3",
                "--words",
                "1200",
            ]
        )

        (workspace / "partial_architecture.json").write_text(
            json.dumps({"core_seed_result": "seed", "character_dynamics_result": "characters"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (workspace / "plot_arcs.txt").write_text("未解决冲突：钥匙真正归属", encoding="utf-8")

        resume_result = self._run(["--json", "--project", str(project_path), "generate", "architecture-state"])
        resume_data = json.loads(resume_result.stdout)
        assert resume_data["resume_available"] is True
        assert resume_data["next_step"] == "character_state"

        plot_arcs_result = self._run(["--json", "--project", str(project_path), "review", "plot-arcs"])
        plot_arcs_data = json.loads(plot_arcs_result.stdout)
        assert plot_arcs_data["review_context_ready"] is True
        assert "钥匙真正归属" in plot_arcs_data["text"]

        self._run(["--project", str(project_path), "generate", "architecture"])
        self._run(["--project", str(project_path), "generate", "blueprint"])
        self._run(["--project", str(project_path), "chapter", "generate", "1"])
        review_result = self._run(["--json", "--project", str(project_path), "review", "consistency", "1"])
        review_data = json.loads(review_result.stdout)
        assert review_data["plot_arcs_included"] is True
        assert review_data["plot_arcs_path"].endswith("plot_arcs.txt")

    def test_workspace_and_chapter_write_commands_json(self, tmp_path):
        config_path = write_mock_config(tmp_path / "config.json")
        project_path = tmp_path / "project.json"
        workspace = tmp_path / "workspace"
        chapter_text_path = tmp_path / "chapter-1-edit.txt"
        chapter_text_path.write_text("第1章来自文件的人工修订", encoding="utf-8")

        self._run(
            [
                "project",
                "new",
                "-o",
                str(project_path),
                "--workspace",
                str(workspace),
                "--config",
                str(config_path),
                "--topic",
                "记忆之城",
                "--genre",
                "科幻",
                "--chapters",
                "3",
                "--words",
                "1200",
            ]
        )

        workspace_result = self._run(
            [
                "--json",
                "--project",
                str(project_path),
                "workspace",
                "write",
                "architecture",
                "--text",
                "CLI人工修订后的架构",
            ]
        )
        workspace_data = json.loads(workspace_result.stdout)
        assert workspace_data["target"] == "architecture"
        assert workspace_data["text"] == "CLI人工修订后的架构"

        chapter_result = self._run(
            [
                "--json",
                "--project",
                str(project_path),
                "chapter",
                "write",
                "1",
                "--from-file",
                str(chapter_text_path),
            ]
        )
        chapter_data = json.loads(chapter_result.stdout)
        assert chapter_data["chapter_number"] == 1
        assert chapter_data["text"] == "第1章来自文件的人工修订"
        assert Path(chapter_data["path"]).exists()

    def test_chapter_status_scan_and_project_status_json(self, tmp_path):
        config_path = write_mock_config(tmp_path / "config.json")
        project_path = tmp_path / "project.json"
        workspace = tmp_path / "workspace"
        role_file = tmp_path / "linwu.txt"
        role_file.write_text(
            "林雾：\n├──物品：\n│  ├──残卷: 会自我改写\n├──能力：\n│  ├──修复: 拼接档案\n├──状态：\n│  ├──身体状态: 稳定\n├──主要角色间关系网：\n│  ├──沈砚: 盟友\n├──触发或加深的事件：\n│  ├──收到残卷: 导火索",
            encoding="utf-8",
        )

        self._run(
            [
                "project",
                "new",
                "-o",
                str(project_path),
                "--workspace",
                str(workspace),
                "--config",
                str(config_path),
                "--topic",
                "记忆之城",
                "--genre",
                "科幻",
                "--chapters",
                "3",
                "--words",
                "1200",
            ]
        )
        self._run(["--project", str(project_path), "generate", "architecture"])
        self._run(["--project", str(project_path), "generate", "blueprint"])
        self._run(["--project", str(project_path), "role", "category-create", "主角组"])
        self._run(["--project", str(project_path), "role", "create", "林雾", "--category", "主角组", "--from-file", str(role_file)])
        self._run(["--project", str(project_path), "project", "set", "--characters", "林雾,沈砚"])
        self._run(["--project", str(project_path), "chapter", "generate", "1"])
        self._run(["--project", str(project_path), "chapter", "generate", "2"])
        self._run(["--project", str(project_path), "chapter", "finalize", "2"])

        chapter_status_result = self._run(["--json", "--project", str(project_path), "chapter", "status", "2"])
        chapter_status_data = json.loads(chapter_status_result.stdout)
        assert chapter_status_data["chapter_number"] == 2
        assert chapter_status_data["state"] == "finalized"

        scan_result = self._run(["--json", "--project", str(project_path), "chapter", "scan", "1", "3"])
        scan_data = json.loads(scan_result.stdout)
        assert scan_data["draft_count"] == 1
        assert scan_data["finalized_count"] == 1
        assert scan_data["missing_count"] == 1

        project_status_result = self._run(["--json", "--project", str(project_path), "project", "status"])
        project_status_data = json.loads(project_status_result.stdout)
        assert project_status_data["finalized_chapter_count"] == 1
        assert project_status_data["finalized_chapters"] == [2]
        assert project_status_data["chapter_state_counts"] == {"missing": 1, "draft": 1, "finalized": 1}
        assert project_status_data["next_action"] == "generate_chapter"
        assert project_status_data["recommended_next_chapter"] == 3
        assert project_status_data["role_library"]["categories"] == ["全部", "主角组"]
        assert project_status_data["role_library"]["roles"] == ["林雾"]
        assert project_status_data["role_library"]["requested_characters"] == ["林雾", "沈砚"]
        assert project_status_data["role_library"]["available_requested_characters"] == ["林雾"]
        assert project_status_data["role_library"]["missing_requested_characters"] == ["沈砚"]

    def test_config_management_crud_and_choose_json(self, tmp_path):
        config_path = write_mock_config(tmp_path / "config.json")
        project_path = tmp_path / "project.json"
        workspace = tmp_path / "workspace"
        llm_import_file = tmp_path / "llm-profile.json"
        embedding_import_file = tmp_path / "embedding-profile.json"
        llm_import_file.write_text(
            json.dumps(
                {
                    "id": "llm-import-1",
                    "api_key": "k-import",
                    "base_url": "mock://story-llm",
                    "model_name": "story-model",
                    "temperature": 0.25,
                    "max_tokens": 8192,
                    "timeout": 75,
                    "interface_format": "HarnessMock",
                    "created_at": "2026-05-01T12:00:00",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        embedding_import_file.write_text(
            json.dumps(
                {
                    "id": "embed-import-1",
                    "api_key": "ek1",
                    "base_url": "mock://embed-x",
                    "model_name": "embed-model",
                    "retrieval_k": 7,
                    "interface_format": "HarnessMock",
                    "created_at": "2026-05-01T12:00:00",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self._run(
            [
                "project",
                "new",
                "-o",
                str(project_path),
                "--workspace",
                str(workspace),
                "--config",
                str(config_path),
                "--topic",
                "记忆之城",
                "--genre",
                "科幻",
                "--chapters",
                "3",
                "--words",
                "1200",
            ]
        )

        llm_create = self._run(
            [
                "--json",
                "--project",
                str(project_path),
                "config",
                "llm",
                "import-file",
                "StoryLLM",
                "--from-file",
                str(llm_import_file),
            ]
        )
        llm_create_data = json.loads(llm_create.stdout)
        assert llm_create_data["name"] == "StoryLLM"
        assert llm_create_data["config"]["model_name"] == "story-model"
        assert llm_create_data["config"]["id"] == "llm-import-1"

        llm_update = self._run(
            [
                "--json",
                "--project",
                str(project_path),
                "config",
                "llm",
                "update",
                "StoryLLM",
                "--temperature",
                "0.45",
            ]
        )
        assert json.loads(llm_update.stdout)["config"]["temperature"] == 0.45

        llm_rename = self._run(
            ["--json", "--project", str(project_path), "config", "llm", "rename", "StoryLLM", "StoryLLM2"]
        )
        llm_rename_data = json.loads(llm_rename.stdout)
        assert llm_rename_data["name"] == "StoryLLM2"

        embedding_create = self._run(
            [
                "--json",
                "--project",
                str(project_path),
                "config",
                "embedding",
                "import-file",
                "EmbedX",
                "--from-file",
                str(embedding_import_file),
            ]
        )
        embedding_data = json.loads(embedding_create.stdout)
        assert embedding_data["config"]["retrieval_k"] == 7
        assert embedding_data["config"]["id"] == "embed-import-1"

        choose_set = self._run(
            [
                "--json",
                "--project",
                str(project_path),
                "config",
                "choose",
                "set",
                "--architecture-llm",
                "StoryLLM2",
                "--chapter-outline-llm",
                "StoryLLM2",
                "--prompt-draft-llm",
                "StoryLLM2",
                "--final-chapter-llm",
                "StoryLLM2",
                "--consistency-review-llm",
                "StoryLLM2",
                "--embedding",
                "EmbedX",
            ]
        )
        choose_data = json.loads(choose_set.stdout)
        assert choose_data["choose_configs"]["architecture_llm"] == "StoryLLM2"
        assert choose_data["choose_configs"]["embedding"] == "EmbedX"

        choose_show = self._run(["--json", "--project", str(project_path), "config", "choose", "show"])
        choose_show_data = json.loads(choose_show.stdout)
        assert choose_show_data["choose_configs"] == choose_data["choose_configs"]

        list_result = self._run(["--json", "--project", str(project_path), "config", "llm", "list"])
        list_data = json.loads(list_result.stdout)
        selected = [item for item in list_data["profiles"] if item["name"] == "StoryLLM2"][0]
        assert selected["is_selected"] is True
        assert set(selected["selected_slots"]) == {
            "architecture_llm",
            "chapter_outline_llm",
            "prompt_draft_llm",
            "final_chapter_llm",
            "consistency_review_llm",
        }

        show_result = self._run(["--json", "--project", str(project_path), "config", "embedding", "show", "EmbedX"])
        assert json.loads(show_result.stdout)["config"]["model_name"] == "embed-model"

        self._run(
            [
                "--project",
                str(project_path),
                "config",
                "choose",
                "set",
                "--architecture-llm",
                "MockLLM",
                "--chapter-outline-llm",
                "MockLLM",
                "--prompt-draft-llm",
                "MockLLM",
                "--final-chapter-llm",
                "MockLLM",
                "--consistency-review-llm",
                "MockLLM",
                "--embedding",
                "MockEmbedding",
            ]
        )
        delete_llm = self._run(["--json", "--project", str(project_path), "config", "llm", "delete", "StoryLLM2"])
        delete_embedding = self._run(["--json", "--project", str(project_path), "config", "embedding", "delete", "EmbedX"])
        assert json.loads(delete_llm.stdout)["deleted"] is True
        assert json.loads(delete_embedding.stdout)["deleted"] is True

        persisted = json.loads(config_path.read_text(encoding="utf-8"))
        assert "StoryLLM2" not in persisted["llm_configs"]
        assert "EmbedX" not in persisted["embedding_configs"]
        assert persisted["choose_configs"]["architecture_llm"] == "MockLLM"
        assert persisted["choose_configs"]["embedding"] == "MockEmbedding"
