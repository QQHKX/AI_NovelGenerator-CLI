import contextlib
import importlib
import json
import os
import re
import sys
import types
from pathlib import Path


def source_root_from(project_or_path) -> str:
    if isinstance(project_or_path, dict):
        return os.path.abspath(project_or_path["source_root"])
    return os.path.abspath(str(project_or_path))


def ensure_source_path(source_root: str) -> None:
    if source_root not in sys.path:
        sys.path.insert(0, source_root)


def _ensure_optional_dependency_stubs() -> None:
    try:
        importlib.import_module("google.genai")
    except ImportError:
        google_module = sys.modules.get("google")
        if google_module is None:
            google_module = types.ModuleType("google")
            google_module.__path__ = []
            sys.modules["google"] = google_module

        genai_module = types.ModuleType("google.genai")
        genai_module.Client = type("Client", (), {})

        types_module = types.ModuleType("google.genai.types")
        types_module.GenerateContentConfig = type("GenerateContentConfig", (), {})

        genai_module.types = types_module
        setattr(google_module, "genai", genai_module)
        sys.modules["google.genai"] = genai_module
        sys.modules["google.genai.types"] = types_module

    try:
        importlib.import_module("azure.ai.inference")
        importlib.import_module("azure.ai.inference.models")
        importlib.import_module("azure.core.credentials")
    except ImportError:
        azure_module = sys.modules.get("azure")
        if azure_module is None:
            azure_module = types.ModuleType("azure")
            azure_module.__path__ = []
            sys.modules["azure"] = azure_module

        azure_ai_module = sys.modules.get("azure.ai")
        if azure_ai_module is None:
            azure_ai_module = types.ModuleType("azure.ai")
            azure_ai_module.__path__ = []
            sys.modules["azure.ai"] = azure_ai_module
            setattr(azure_module, "ai", azure_ai_module)

        inference_module = types.ModuleType("azure.ai.inference")
        inference_module.__path__ = []
        inference_module.ChatCompletionsClient = type("ChatCompletionsClient", (), {})

        inference_models_module = types.ModuleType("azure.ai.inference.models")
        inference_models_module.SystemMessage = type("SystemMessage", (), {})
        inference_models_module.UserMessage = type("UserMessage", (), {})

        azure_core_module = sys.modules.get("azure.core")
        if azure_core_module is None:
            azure_core_module = types.ModuleType("azure.core")
            azure_core_module.__path__ = []
            sys.modules["azure.core"] = azure_core_module
            setattr(azure_module, "core", azure_core_module)

        credentials_module = types.ModuleType("azure.core.credentials")
        credentials_module.AzureKeyCredential = type("AzureKeyCredential", (), {})

        setattr(azure_ai_module, "inference", inference_module)
        setattr(inference_module, "models", inference_models_module)
        setattr(azure_core_module, "credentials", credentials_module)
        sys.modules["azure.ai.inference"] = inference_module
        sys.modules["azure.ai.inference.models"] = inference_models_module
        sys.modules["azure.core.credentials"] = credentials_module

    try:
        importlib.import_module("nltk")
    except ImportError:
        nltk_module = types.ModuleType("nltk")

        def sent_tokenize(text: str):
            parts = [item.strip() for item in re.split(r"(?<=[。！？.!?])\s+", text) if item.strip()]
            return parts or ([text] if text else [])

        nltk_module.sent_tokenize = sent_tokenize
        sys.modules["nltk"] = nltk_module

    try:
        importlib.import_module("langchain_chroma")
        importlib.import_module("chromadb.config")
        importlib.import_module("langchain.docstore.document")
        importlib.import_module("langchain.embeddings.base")
    except ImportError:
        class _Document:
            def __init__(self, page_content: str):
                self.page_content = page_content

        class _Settings:
            def __init__(self, **_kwargs):
                pass

        class _Embeddings:
            pass

        class _SimpleChroma:
            def __init__(self, persist_directory=None, embedding_function=None, client_settings=None, collection_name=None):
                self.persist_directory = persist_directory
                self.embedding_function = embedding_function
                self.collection_name = collection_name
                self._docs = []
                self._load()

            @classmethod
            def from_documents(cls, documents, embedding=None, persist_directory=None, client_settings=None, collection_name=None):
                instance = cls(
                    persist_directory=persist_directory,
                    embedding_function=embedding,
                    client_settings=client_settings,
                    collection_name=collection_name,
                )
                instance.add_documents(documents)
                return instance

            def _store_path(self):
                if not self.persist_directory:
                    return None
                os.makedirs(self.persist_directory, exist_ok=True)
                return os.path.join(self.persist_directory, "mock_store.json")

            def _load(self):
                store_path = self._store_path()
                if not store_path or not os.path.exists(store_path):
                    return
                with open(store_path, "r", encoding="utf-8") as handle:
                    self._docs = json.load(handle)

            def _save(self):
                store_path = self._store_path()
                if not store_path:
                    return
                with open(store_path, "w", encoding="utf-8") as handle:
                    json.dump(self._docs, handle, ensure_ascii=False, indent=2)

            def add_documents(self, docs):
                self._docs.extend(doc.page_content for doc in docs)
                self._save()

            def similarity_search(self, query, k=2):
                del query
                return [_Document(text) for text in self._docs[:k]]

        langchain_chroma_module = types.ModuleType("langchain_chroma")
        langchain_chroma_module.Chroma = _SimpleChroma
        sys.modules["langchain_chroma"] = langchain_chroma_module

        chromadb_module = sys.modules.get("chromadb")
        if chromadb_module is None:
            chromadb_module = types.ModuleType("chromadb")
            chromadb_module.__path__ = []
            sys.modules["chromadb"] = chromadb_module
        chromadb_config_module = types.ModuleType("chromadb.config")
        chromadb_config_module.Settings = _Settings
        setattr(chromadb_module, "config", chromadb_config_module)
        sys.modules["chromadb.config"] = chromadb_config_module

        langchain_module = sys.modules.get("langchain")
        if langchain_module is None:
            langchain_module = types.ModuleType("langchain")
            langchain_module.__path__ = []
            sys.modules["langchain"] = langchain_module

        docstore_module = sys.modules.get("langchain.docstore")
        if docstore_module is None:
            docstore_module = types.ModuleType("langchain.docstore")
            docstore_module.__path__ = []
            sys.modules["langchain.docstore"] = docstore_module
            setattr(langchain_module, "docstore", docstore_module)
        document_module = types.ModuleType("langchain.docstore.document")
        document_module.Document = _Document
        setattr(docstore_module, "document", document_module)
        sys.modules["langchain.docstore.document"] = document_module

        embeddings_module = sys.modules.get("langchain.embeddings")
        if embeddings_module is None:
            embeddings_module = types.ModuleType("langchain.embeddings")
            embeddings_module.__path__ = []
            sys.modules["langchain.embeddings"] = embeddings_module
            setattr(langchain_module, "embeddings", embeddings_module)
        embeddings_base_module = types.ModuleType("langchain.embeddings.base")
        embeddings_base_module.Embeddings = _Embeddings
        setattr(embeddings_module, "base", embeddings_base_module)
        sys.modules["langchain.embeddings.base"] = embeddings_base_module

    try:
        importlib.import_module("sklearn.metrics.pairwise")
    except ImportError:
        sklearn_module = sys.modules.get("sklearn")
        if sklearn_module is None:
            sklearn_module = types.ModuleType("sklearn")
            sklearn_module.__path__ = []
            sys.modules["sklearn"] = sklearn_module

        metrics_module = sys.modules.get("sklearn.metrics")
        if metrics_module is None:
            metrics_module = types.ModuleType("sklearn.metrics")
            metrics_module.__path__ = []
            sys.modules["sklearn.metrics"] = metrics_module
            setattr(sklearn_module, "metrics", metrics_module)

        pairwise_module = types.ModuleType("sklearn.metrics.pairwise")

        def cosine_similarity(a, b):
            return [[1.0 for _ in b] for _ in a]

        pairwise_module.cosine_similarity = cosine_similarity
        setattr(metrics_module, "pairwise", pairwise_module)
        sys.modules["sklearn.metrics.pairwise"] = pairwise_module


def source_modules(source_root: str) -> dict:
    ensure_source_path(source_root)
    _ensure_optional_dependency_stubs()
    return {
        "novel_generator": importlib.import_module("novel_generator"),
        "config_manager": importlib.import_module("config_manager"),
        "llm_adapters": importlib.import_module("llm_adapters"),
        "embedding_adapters": importlib.import_module("embedding_adapters"),
        "source_utils": importlib.import_module("utils"),
        "consistency_checker": importlib.import_module("consistency_checker"),
        "chapter_module": importlib.import_module("novel_generator.chapter"),
        "architecture_module": importlib.import_module("novel_generator.architecture"),
        "blueprint_module": importlib.import_module("novel_generator.blueprint"),
        "finalization_module": importlib.import_module("novel_generator.finalization"),
        "knowledge_module": importlib.import_module("novel_generator.knowledge"),
        "vectorstore_module": importlib.import_module("novel_generator.vectorstore_utils"),
    }


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_runtime_config(project: dict) -> dict:
    config = _load_json(project["config_path"])
    llm_configs = config.get("llm_configs", {})
    embedding_configs = config.get("embedding_configs", {})
    chosen = config.get("choose_configs", {})
    overrides = project.get("profiles", {})

    def pick_llm(slot: str) -> dict:
        name = overrides.get(slot) or chosen.get(slot)
        if not name:
            raise RuntimeError(f"No profile bound for {slot}")
        if name not in llm_configs:
            raise RuntimeError(f"LLM profile not found: {name}")
        profile = dict(llm_configs[name])
        profile["name"] = name
        return profile

    def pick_embedding() -> dict:
        name = overrides.get("embedding")
        if not name:
            if len(embedding_configs) == 1:
                name = next(iter(embedding_configs))
            elif "OpenAI" in embedding_configs:
                name = "OpenAI"
            elif embedding_configs:
                name = next(iter(embedding_configs))
        if not name or name not in embedding_configs:
            raise RuntimeError(f"Embedding profile not found: {name}")
        profile = dict(embedding_configs[name])
        profile["name"] = name
        return profile

    return {
        "architecture_llm": pick_llm("architecture_llm"),
        "chapter_outline_llm": pick_llm("chapter_outline_llm"),
        "prompt_draft_llm": pick_llm("prompt_draft_llm"),
        "final_chapter_llm": pick_llm("final_chapter_llm"),
        "consistency_review_llm": pick_llm("consistency_review_llm"),
        "embedding": pick_embedding(),
    }


class HarnessMockLLM:
    def __init__(self, **_kwargs):
        pass

    def invoke(self, prompt: str) -> str:
        if "当前章节摘要" in prompt and "前三章内容" in prompt:
            return "当前章节摘要: 主角承接前章余波，确认行动目标，并为下一章冲突埋下线索。"
        if "生成合适的知识库检索关键词" in prompt:
            return "遗迹·密钥\n地下城·回声\n盟友·背叛"
        if "三级过滤" in prompt:
            return "[情节燃料]→可用于推进悬念\n❗ 遗迹深处的密钥与主角身份有关"
        if "雪花写作法" in prompt or "故事核心" in prompt:
            return "当失忆的档案修复师收到一份会自我改写的残卷，她必须在城市崩坏前追索真相，否则整座记忆之城将被篡改。"
        if "动态变化潜力的核心角色" in prompt:
            return "林雾：档案修复师，表面冷静，内心执着真相。\n沈砚：调查员，与林雾合作却隐瞒关键过去。\n祁星：技术顾问，擅长破解遗迹系统。"
        if "生成一个角色状态文档" in prompt:
            return (
                "林雾：\n├──物品:\n│  ├──残卷：会自我改写的古老文稿\n├──能力\n│  ├──修复：擅长拼接破损档案\n├──状态\n│  ├──身体状态: 疲惫但稳定\n│  └──心理状态: 强烈追索真相\n"
                "├──主要角色间关系网\n│  ├──沈砚：互相试探的盟友\n├──触发或加深的事件\n│  ├──收到残卷：故事导火索\n\n新出场角色：\n- 暂无"
            )
        if "构建三维交织的世界观" in prompt:
            return "记忆之城分为地表档案区、地下机枢层、失落遗迹带。权力由馆议会控制，城市能源依赖记忆回路。"
        if "第一幕（触发）" in prompt and "第三幕（解决）" in prompt:
            return "第一幕：残卷现身并打破平衡。\n第二幕：调查推进并暴露记忆篡改网络。\n第三幕：主角以真实记忆为代价关闭核心装置。"
        if "节奏分布" in prompt and "本章定位" in prompt:
            match = re.search(r"第(\d+)章到第(\d+)", prompt)
            if match:
                start = int(match.group(1))
                end = int(match.group(2))
            else:
                total_match = re.search(r"设计(\d+)章的节奏分布", prompt)
                start = 1
                end = int(total_match.group(1)) if total_match else 3
            return "\n\n".join(_chapter_blueprint(i) for i in range(start, end + 1))
        if "更新前文摘要" in prompt:
            return "林雾获得残卷并确认敌人正在篡改城市记忆，团队开始追踪遗迹密钥。"
        if "请更新主要角色状态" in prompt:
            return (
                "林雾：\n├──物品:\n│  ├──残卷：确认与城市核心相关\n├──能力\n│  ├──修复：能辨认篡改痕迹\n├──状态\n│  ├──身体状态: 轻微失眠\n│  └──心理状态: 更坚定也更警惕\n"
                "├──主要角色间关系网\n│  ├──沈砚：开始建立信任\n├──触发或加深的事件\n│  ├──遗迹追踪：明确主线目标\n\n新出场角色：\n- 暂无"
            )
        if "请检查下面的小说设定与最新章节" in prompt:
            return "无明显冲突"
        if "根据以下文本内容，分析出所有角色及其属性信息" in prompt:
            return (
                "林雾:\n├──物品:\n│  ├──残卷: 会自我改写的古老文稿\n├──能力:\n│  ├──修复: 擅长拼接破损档案\n├──状态:\n│  ├──身体状态: 疲惫但稳定\n│  └──心理状态: 强烈追索真相\n"
                "├──主要角色间关系网:\n│  ├──沈砚: 互相试探的盟友\n├──触发或加深的事件:\n│  ├──收到残卷: 故事导火索\n\n"
                "沈砚:\n├──物品:\n│  ├──调查记录仪: 记录遗迹异常信号\n├──能力:\n│  ├──追踪: 擅长锁定异常源头\n├──状态:\n│  ├──身体状态: 轻伤未愈\n│  └──心理状态: 对林雾保持审慎信任\n"
                "├──主要角色间关系网:\n│  ├──林雾: 需要合作的调查对象\n├──触发或加深的事件:\n│  ├──遗迹追踪: 与林雾结成临时同盟"
            )
        if "进行扩写" in prompt:
            return "扩写后的章节加入更多环境细节、对话张力与行动推进。"
        if "完成第" in prompt and "章节正文" in prompt:
            chap_match = re.search(r"第\s*(\d+)\s*章", prompt)
            chap = int(chap_match.group(1)) if chap_match else 1
            return f"第{chap}章正文：林雾在档案馆深夜破解残卷，发现遗迹密钥与自身记忆缺口有关，随后与沈砚前往地下机枢层继续追查。"
        return "默认测试响应"


class HarnessMockEmbedding:
    def embed_documents(self, texts):
        return [self._embed_single(text) for text in texts]

    def embed_query(self, query: str):
        return self._embed_single(query)

    def _embed_single(self, text: str):
        total = sum(ord(char) for char in text) or 1
        length = max(len(text), 1)
        vowels = sum(1 for char in text.lower() if char in "aeiou")
        return [float(total % 997), float(length), float(vowels), float((total // length) % 113)]


def _chapter_blueprint(number: int) -> str:
    stars = "★" * min(5, ((number - 1) % 5) + 1) + "☆" * max(0, 5 - min(5, ((number - 1) % 5) + 1))
    return (
        f"第{number}章 - [章节{number}]\n"
        "本章定位：[事件]\n"
        "核心作用：[推进]\n"
        "悬念密度：[渐进]\n"
        "伏笔操作：埋设(密钥线索)→强化(身份疑点)\n"
        f"认知颠覆：{stars}\n"
        f"本章简述：[第{number}章推动主线并制造新疑点]"
    )


def _patched_create_llm_adapter(interface_format: str, **kwargs):
    if interface_format.strip().lower() == "harnessmock":
        return HarnessMockLLM(**kwargs)
    modules = source_modules(kwargs.pop("_source_root"))
    return modules["llm_adapters"].create_llm_adapter(interface_format=interface_format, **kwargs)


def _patched_create_embedding_adapter(interface_format: str, **kwargs):
    if interface_format.strip().lower() == "harnessmock":
        return HarnessMockEmbedding()
    modules = source_modules(kwargs.pop("_source_root"))
    return modules["embedding_adapters"].create_embedding_adapter(interface_format=interface_format, **kwargs)


@contextlib.contextmanager
def patched_adapters(project: dict):
    runtime = get_runtime_config(project)
    needs_mock = any(profile["interface_format"].strip().lower() == "harnessmock" for profile in runtime.values())
    if not needs_mock:
        yield
        return
    modules = source_modules(project["source_root"])
    originals = {
        "llm_root": modules["llm_adapters"].create_llm_adapter,
        "emb_root": modules["embedding_adapters"].create_embedding_adapter,
        "architecture": modules["architecture_module"].create_llm_adapter,
        "blueprint": modules["blueprint_module"].create_llm_adapter,
        "chapter": modules["chapter_module"].create_llm_adapter,
        "final_llm": modules["finalization_module"].create_llm_adapter,
        "final_emb": modules["finalization_module"].create_embedding_adapter,
        "consistency": modules["consistency_checker"].create_llm_adapter,
        "knowledge_sent_tokenize": modules["knowledge_module"].nltk.sent_tokenize,
        "vector_sent_tokenize": modules["vectorstore_module"].nltk.sent_tokenize,
    }

    def llm_factory(interface_format: str, **kwargs):
        if interface_format.strip().lower() == "harnessmock":
            return HarnessMockLLM(**kwargs)
        return originals["llm_root"](interface_format=interface_format, **kwargs)

    def emb_factory(interface_format: str, api_key: str, base_url: str, model_name: str):
        if interface_format.strip().lower() == "harnessmock":
            return HarnessMockEmbedding()
        return originals["emb_root"](interface_format, api_key, base_url, model_name)

    modules["llm_adapters"].create_llm_adapter = llm_factory
    modules["embedding_adapters"].create_embedding_adapter = emb_factory
    modules["architecture_module"].create_llm_adapter = llm_factory
    modules["blueprint_module"].create_llm_adapter = llm_factory
    modules["chapter_module"].create_llm_adapter = llm_factory
    modules["finalization_module"].create_llm_adapter = llm_factory
    modules["finalization_module"].create_embedding_adapter = emb_factory
    modules["consistency_checker"].create_llm_adapter = llm_factory

    def simple_sent_tokenize(text: str):
        parts = [item.strip() for item in re.split(r"(?<=[。！？.!?])\s+", text) if item.strip()]
        return parts or [text]

    modules["knowledge_module"].nltk.sent_tokenize = simple_sent_tokenize
    modules["vectorstore_module"].nltk.sent_tokenize = simple_sent_tokenize
    try:
        yield
    finally:
        modules["llm_adapters"].create_llm_adapter = originals["llm_root"]
        modules["embedding_adapters"].create_embedding_adapter = originals["emb_root"]
        modules["architecture_module"].create_llm_adapter = originals["architecture"]
        modules["blueprint_module"].create_llm_adapter = originals["blueprint"]
        modules["chapter_module"].create_llm_adapter = originals["chapter"]
        modules["finalization_module"].create_llm_adapter = originals["final_llm"]
        modules["finalization_module"].create_embedding_adapter = originals["final_emb"]
        modules["consistency_checker"].create_llm_adapter = originals["consistency"]
        modules["knowledge_module"].nltk.sent_tokenize = originals["knowledge_sent_tokenize"]
        modules["vectorstore_module"].nltk.sent_tokenize = originals["vector_sent_tokenize"]
