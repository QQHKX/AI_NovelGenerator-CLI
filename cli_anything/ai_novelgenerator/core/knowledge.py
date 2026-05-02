"""Knowledge-base import and cleanup helpers for the workspace vector store."""

import os

from cli_anything.ai_novelgenerator.utils.ai_novelgenerator_backend import get_runtime_config, patched_adapters, source_modules


def import_knowledge(project: dict, file_path: str) -> dict:
    runtime = get_runtime_config(project)
    modules = source_modules(project["source_root"])
    target = os.path.abspath(file_path)
    with patched_adapters(project):
        modules["novel_generator"].import_knowledge_file(
            embedding_api_key=runtime["embedding"]["api_key"],
            embedding_url=runtime["embedding"]["base_url"],
            embedding_interface_format=runtime["embedding"]["interface_format"],
            embedding_model_name=runtime["embedding"]["model_name"],
            file_path=target,
            filepath=project["workspace_dir"],
        )
    return {
        "input": target,
        "vectorstore_dir": os.path.join(project["workspace_dir"], "vectorstore"),
    }


def clear_knowledge(project: dict) -> dict:
    modules = source_modules(project["source_root"])
    removed = modules["novel_generator"].clear_vector_store(project["workspace_dir"])
    return {
        "removed": bool(removed),
        "vectorstore_dir": os.path.join(project["workspace_dir"], "vectorstore"),
    }
