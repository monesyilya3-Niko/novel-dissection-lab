#!/usr/bin/env python3
"""
统一 LLM 调用层 — 零依赖（仅标准库）

设计要点：
1. 密钥与配置分离存储，配置可进 git，密钥不可
2. 三种协议：openai 兼容（通吃绝大多数）/ anthropic / ollama
3. 按任务路由模型：拆书四遍各自可指定不同模型
4. 失败可回退到备用模型：候选链由 resolve_fallback_chain 给出
   （主模型配置的 fallback → default 角色 → 其余已配置模型），
   chat(allow_fallback=True) 逐个候选重试；不可重试的错误（401/403/余额不足）
   立即换候选。连通性测试 test_model 显式关闭回退，避免「备用通了」被误报成
   「主模型通了」。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
for _p in (str(ROOT_DIR), str(SCRIPTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CONFIG_DIR = ROOT_DIR / "config"
MODELS_FILE = CONFIG_DIR / "models.json"
SECRETS_FILE = CONFIG_DIR / ".secrets.json"


def user_config_dir() -> Path:
    """用户数据目录下的 config/（模型与密钥的**权威**位置，2026-11-02）。

    为什么需要它：配置属于用户数据，不是程序的一部分。放在 ``ROOT/config``
    时有两个实际问题——
      1. 装新版会连配置一起覆盖，用户刚配好的模型没了；
      2. 源码运行读 ``ROOT/config``、安装版读 ``resources/backend/config``，
         同一台机器上两份配置各读各的，改一份另一份不知道。
    统一到用户目录后，两种运行方式读同一份，升级也不碰它。

    ``ROOT/config`` 保留为**模板**：用户目录没有 models.json 时回落到它
    （全新安装、未配置模型的开箱状态）。

    路径在**函数内实时求值**，不做模块级快照——AGENTS.md §4 记录过导入期
    快照无法被 patch 重定向的事故（system_service 的 _SETTINGS_FILE）。

    与 gui/config.py::_user_data_dir() 同口径，但 scripts/ 不得 import gui/
    （依赖方向禁令），故此处独立实现；支持 XUAN_DATA_DIR 覆盖供测试隔离。
    """
    import os
    import sys as _sys

    override = os.environ.get("XUAN_DATA_DIR", "").strip()
    if override:
        return Path(override) / "config"
    if _sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "暮冬念春" / "config"
    if _sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "暮冬念春" / "config"
    return Path.home() / ".local" / "share" / "暮冬念春" / "config"


def resolve_models_file() -> Path:
    """模型配置的最终路径：用户目录优先，回落仓库模板（实时求值）。"""
    user = user_config_dir() / "models.json"
    if user.exists():
        return user
    return MODELS_FILE


def resolve_secrets_dir() -> Path:
    """密钥目录：用户目录优先；那里还没有密钥时回落到仓库 config（兼容旧布局）。"""
    user = user_config_dir()
    if (user / ".secrets.bin").exists() or (user / ".secrets.json").exists():
        return user
    if (CONFIG_DIR / ".secrets.bin").exists() or (CONFIG_DIR / ".secrets.json").exists():
        return CONFIG_DIR
    return user  # 都没有 → 新密钥写入用户目录

# 任务默认路由。抽取类任务用便宜模型，判断类任务用强模型
DEFAULT_ROUTES = {
    "pass1_structure": "cheap",
    "pass2_character": "cheap",
    "pass3_style": "strong",
    "pass4_commercial": "strong",
    "pass5_aggregate": "strong",
    "writing": "strong",
    "consistency_check": "cheap",
}


class LLMError(Exception):
    pass


# LLM 不可用时仍可本地完成的能力（评估报告 item 10：显式降级提示）
LLM_DEGRADED_FEATURES = (
    "拆书分析 pass1-5（LLM 扫描）",
    "写作台 generate / novel 写作（LLM 正文生成）",
    "qc --llm-hook 因果二次判定",
    "模型连通性测试与额度相关操作",
)
LLM_STILL_AVAILABLE = (
    "纯算法质检（novel 检查 / 质检 / qc 默认路径）",
    "资产校验、注入 prompt 组装、组装 CLI（无模型可用）",
    "章节加载 / 重复检测 / 设定与逻辑一致性纯算法检测",
)


def describe_llm_degradation(error) -> str:
    """把 LLM 失败原因翻译成「哪些能力不可用 / 哪些仍可用」的可读提示。"""
    err = str(error or "")
    low = err.lower()
    if "尚未配置" in err:
        reason = "尚未配置外部模型"
        hint = "运行: python scripts/model_config.py add"
    elif ("insufficient" in low or "余额" in err
          or "HTTP 403" in err or "HTTP 401" in err):
        reason = "模型额度/权限不足"
        hint = ("充值或更换可用模型；可配置备用链: "
                "python scripts/model_config.py fallback <主模型> <备用...>")
    elif "连接失败" in err or "timed out" in low or "timeout" in low:
        reason = "网络连接失败"
        hint = "检查网络/代理后重试；配置备用模型可提高可用性"
    else:
        reason = "模型调用失败"
        hint = "查看原始错误；必要时 python novel.py 模型 --test <id>"

    degraded = "\n".join(f"  - {x}" for x in LLM_DEGRADED_FEATURES)
    still = "\n".join(f"  - {x}" for x in LLM_STILL_AVAILABLE)
    return (
        f"[LLM 降级] {reason}：{err}\n"
        f"  处理建议: {hint}\n"
        f"  当前不可用（依赖外部模型）:\n{degraded}\n"
        f"  仍然可用（纯本地）:\n{still}"
    )


# --------------------------------------------------------------------------
# 配置读写
# --------------------------------------------------------------------------

def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def any_model_configured() -> bool:
    """是否配置了至少一个外部模型。无模型时 pipeline 走 WorkBuddy 内置智能模式。

    环境变量 ``NOVEL_LAB_FORCE_NO_MODEL=1`` 强制视为「无模型」。
    2026-11-02：测试需要在**有模型配置的开发机上**验证无模型降级路径
    （write.py 的无模型接管清单、pipeline 的任务生成分支）。此前这些
    测试直接读真实 config/models.json，于是开发机配好模型后它们会真的
    去调 LLM 并超时——测试结果取决于机器状态，不可复现。
    有了这个开关，测试显式声明"我要无模型"，与真实配置解耦。
    """
    import os

    if os.environ.get("NOVEL_LAB_FORCE_NO_MODEL") == "1":
        return False
    try:
        return bool(load_models().get("models"))
    except Exception:
        return False


def load_models() -> dict:
    """读取模型配置。文件不存在或损坏时返回空骨架。

    路径经 ``resolve_models_file()`` 实时求值（用户目录优先，回落仓库模板）。
    """
    path = resolve_models_file()
    if not path.exists():
        return {"version": 1, "models": {}, "roles": {}, "routes": dict(DEFAULT_ROUTES)}
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            raise ValueError("models.json 顶层不是对象")
    except (json.JSONDecodeError, OSError, ValueError):
        return {"version": 1, "models": {}, "roles": {}, "routes": dict(DEFAULT_ROUTES)}
    cfg.setdefault("models", {})
    cfg.setdefault("roles", {})
    cfg.setdefault("routes", dict(DEFAULT_ROUTES))
    return cfg


def save_models(cfg: dict):
    """写模型配置到**用户目录**（配置属于用户数据，不进程序目录）。"""
    d = user_config_dir()
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "models.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_secrets() -> dict:
    import secret_store
    return secret_store.load_secrets(resolve_secrets_dir())


def save_secrets(secrets: dict):
    import secret_store
    secret_store.save_secrets(secrets, resolve_secrets_dir())


def resolve_api_key(model_id: str, model: dict) -> str:
    """
    密钥解析优先级：
    1. 环境变量（model.api_key_env 指定的变量名）
    2. .secrets.json
    3. 空串（本地模型如 ollama 通常不需要）
    """
    env_name = model.get("api_key_env")
    if env_name:
        val = os.environ.get(env_name)
        if val:
            return val
    return load_secrets().get(model_id, "")


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

def _post_json(url: str, payload: dict, headers: dict, timeout: int = 180) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw_bytes = resp.read()
            try:
                return json.loads(raw_bytes.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
                preview = raw_bytes[:400].decode("utf-8", errors="replace")
                raise LLMError(f"响应非合法 JSON: {preview}") from exc
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:600]
        raise LLMError(f"HTTP {e.code}: {body}") from None
    except urllib.error.URLError as e:
        raise LLMError(f"连接失败: {e.reason}") from None


# --------------------------------------------------------------------------
# 协议适配
# --------------------------------------------------------------------------

def _reject_empty_text(text: str, model: dict, max_tokens: int, usage: dict,
                       finish_reason=None, reasoning=None) -> None:
    """空正文一律当失败抛出。三种协议共用（2026-11-16）。

    背景：推理型模型把 max_tokens 全烧在思考上时返回 ``content: null`` +
    ``finish_reason: "length"``。旧实现把 None 静默转成 ``""`` 当成功返回，
    上层 ``run_pass`` 只看到「JSON 解析失败」，重试 3 轮后报「模型拒绝本 pass」
    ——用户以为模型能力不行，实际是 max_tokens 给小了。

    这个缺陷在三个协议里都存在（openai 的 content:null、anthropic 的空
    content block 列表、ollama 的 message.content:null），所以抽成共用函数，
    避免只修一处留下两处。

    参数 finish_reason / reasoning 是协议特有的诊断信息，有就带上。
    """
    if text and text.strip():
        return

    detail = []
    if finish_reason:
        detail.append(f"finish_reason={finish_reason}")
    detail.append(f"completion_tokens={usage.get('completion_tokens', 0)}")
    detail.append(f"max_tokens={max_tokens}")
    if reasoning:
        detail.append(f"思考内容 {len(str(reasoning))} 字符")

    hint = ""
    # 三种协议的「输出被截断」标记各不相同，都要认：
    #   openai    → finish_reason: "length"
    #   anthropic → stop_reason:   "max_tokens"
    #   ollama    → done_reason:   "length"
    if finish_reason in ("length", "max_tokens"):
        hint = (
            "\n  这是 max_tokens 用尽：推理型模型把预算烧在思考上，"
            "正文一个字都没留下。\n"
            f"  改法：把 max_tokens 调大（当前 {max_tokens}，"
            "推理模型建议 ≥ 4096），或换非推理模型。"
        )
    raise LLMError(
        f"模型 '{model.get('model_name', '?')}' 返回空正文"
        f"（{', '.join(detail)}）。{hint}"
    )


def _call_openai_compatible(model: dict, api_key: str, system: str,
                            user: str, max_tokens: int, temperature: float) -> dict:
    base = model["base_url"].rstrip("/")
    url = base + "/chat/completions" if not base.endswith("/chat/completions") else base
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    payload = {
        "model": model["model_name"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if model.get("json_mode"):
        payload["response_format"] = {"type": "json_object"}
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    for k, v in (model.get("extra_headers") or {}).items():
        headers[k] = v

    raw = _post_json(url, payload, headers, model.get("timeout", 180))
    try:
        choices = raw["choices"]
        if not isinstance(choices, list) or not choices:
            raise IndexError("choices 必须是非空列表")
        choice = choices[0]
        if not isinstance(choice, dict):
            raise TypeError("choice 必须是字典")
        msg = choice["message"]
        if not isinstance(msg, dict):
            raise TypeError("message 必须是字典")
        text = msg.get("content")
        if text is None:
            text = ""
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise LLMError(f"响应格式异常: {json.dumps(raw, ensure_ascii=False)[:400]}") from exc
    usage = raw.get("usage") if isinstance(raw, dict) else {}
    if not isinstance(usage, dict):
        usage = {}

    # 空正文必须当失败，不能当成功（2026-11-16 实测定根因）。
    #
    # 推理型模型（deepseek-4.1-flash 等）把 max_tokens 全烧在思考上时，
    # 返回的是 content: null + finish_reason: "length"，completion_tokens
    # 顶到上限。旧实现把 None 静默转成 ""，当成功返回给上层。
    #
    # 后果链：run_pass 拿到空字符串 → extract_json 失败 → 重试 3 轮
    # （同样烧满 3 次预算）→ 抛 PassRefused → 用户看到「模型拒绝本 pass」。
    # 用户以为模型能力不行，实际是 max_tokens 给小了。
    #
    # 实测对照（同一模型、同一 prompt，只改 max_tokens）：
    #   max_tokens=32   → completion=32(满额)  textlen=0   <- 空正文
    #   max_tokens=256  → completion=97        textlen=39  <- 正常
    #   max_tokens=1024 → completion=95        textlen=41  <- 正常
    _reject_empty_text(text, model, max_tokens, usage,
                       finish_reason=choice.get("finish_reason"),
                       reasoning=msg.get("reasoning_content") or msg.get("reasoning"))

    return {
        "text": text,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
    }


def _call_anthropic(model: dict, api_key: str, system: str,
                    user: str, max_tokens: int, temperature: float) -> dict:
    base = model["base_url"].rstrip("/")
    url = base + "/messages" if not base.endswith("/messages") else base
    payload = {
        "model": model["model_name"],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": user}],
    }
    if system:
        payload["system"] = system
    headers = {
        "x-api-key": api_key,
        "anthropic-version": model.get("anthropic_version", "2023-06-01"),
    }
    for k, v in (model.get("extra_headers") or {}).items():
        headers[k] = v

    raw = _post_json(url, payload, headers, model.get("timeout", 180))
    try:
        content = raw["content"]
        if not isinstance(content, list) or not content:
            raise TypeError("content 必须是非空列表")
        text_blocks = []
        for b in content:
            if not isinstance(b, dict) or "text" not in b:
                raise TypeError(f"content block 格式异常: {b}")
            text_blocks.append(str(b.get("text", "")))
        text = "".join(text_blocks)
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise LLMError(f"响应格式异常: {json.dumps(raw, ensure_ascii=False)[:400]}") from exc
    usage = raw.get("usage") if isinstance(raw, dict) else {}
    if not isinstance(usage, dict):
        usage = {}
    # anthropic 的 stop_reason 等价于 openai 的 finish_reason（"max_tokens" 表示截断）
    _reject_empty_text(text, model, max_tokens, usage,
                       finish_reason=raw.get("stop_reason") if isinstance(raw, dict) else None)
    return {
        "text": text,
        "prompt_tokens": usage.get("input_tokens", 0),
        "completion_tokens": usage.get("output_tokens", 0),
    }


def _call_ollama(model: dict, api_key: str, system: str,
                 user: str, max_tokens: int, temperature: float) -> dict:
    base = model["base_url"].rstrip("/")
    url = base + "/api/chat" if not base.endswith("/api/chat") else base
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    payload = {
        "model": model["model_name"],
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            # 拆书是长上下文刚需，默认拉高
            "num_ctx": model.get("num_ctx", 32768),
        },
    }
    raw = _post_json(url, payload, {}, model.get("timeout", 600))
    try:
        if not isinstance(raw, dict):
            raise TypeError("响应必须是字典")
        msg = raw["message"]
        if not isinstance(msg, dict):
            raise TypeError("message 必须是字典")
        text = msg.get("content")
        if text is None:
            text = ""
    except (KeyError, TypeError, IndexError, AttributeError) as exc:
        raise LLMError(f"响应格式异常: {json.dumps(raw, ensure_ascii=False)[:400]}") from exc
    prompt_tokens = raw.get("prompt_eval_count", 0) if isinstance(raw, dict) else 0
    completion_tokens = raw.get("eval_count", 0) if isinstance(raw, dict) else 0
    # ollama 用 done_reason 表示结束原因（"length" 表示 num_predict 用尽）
    _reject_empty_text(text, model, max_tokens,
                       {"completion_tokens": completion_tokens},
                       finish_reason=raw.get("done_reason") if isinstance(raw, dict) else None)
    return {
        "text": text,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


PROTOCOL_HANDLERS = {
    "openai": _call_openai_compatible,
    "anthropic": _call_anthropic,
    "ollama": _call_ollama,
}


# --------------------------------------------------------------------------
# 对外接口
# --------------------------------------------------------------------------

def resolve_model(task: str | None = None, model_id: str | None = None) -> tuple:
    """
    解析该用哪个模型。
    显式 model_id > 任务路由 > 角色默认 > 报错
    返回 (model_id, model_dict)
    """
    cfg = load_models()
    models = cfg["models"]
    if not models:
        raise LLMError("尚未配置任何模型。运行: python model_config.py add")

    if model_id:
        if model_id not in models:
            raise LLMError(f"模型 '{model_id}' 不存在。已配置: {', '.join(models)}")
        return model_id, models[model_id]

    if task:
        role = cfg["routes"].get(task)
        if role:
            mid = cfg["roles"].get(role)
            if mid and mid in models:
                return mid, models[mid]

    # 回退：找 default 角色，再回退第一个
    mid = cfg["roles"].get("default")
    if mid and mid in models:
        return mid, models[mid]
    first = next(iter(models))
    return first, models[first]


def resolve_fallback_chain(task: str | None = None,
                           model_id: str | None = None) -> list:
    """
    给出候选模型 id 列表，第 1 位是 resolve_model 得到的主模型。

    第 2 位起的优先级：
      1. 主模型配置里的 fallback（字符串或字符串列表）
      2. cfg["roles"]["default"] 指向的模型
      3. 其余已配置模型（按 cfg["models"] 的插入顺序）

    去重、排除主模型本身、只保留确实存在于 cfg["models"] 的 id。
    主模型解析失败（无模型 / id 不存在）时不再抛错，返回「其它已配置模型」。
    """
    cfg = load_models()
    models = cfg["models"]
    try:
        primary_id, primary = resolve_model(task, model_id)
    except LLMError:
        return list(models)

    chain = [primary_id]
    fallback = primary.get("fallback")
    if isinstance(fallback, str):
        fallback = [fallback]
    for cand in (fallback or []):
        if isinstance(cand, str) and cand in models and cand not in chain:
            chain.append(cand)

    default_id = cfg["roles"].get("default")
    if default_id in models and default_id not in chain:
        chain.append(default_id)

    for mid in models:
        if mid not in chain:
            chain.append(mid)
    return chain


# 不可重试的错误特征（小写匹配）：重试只是白等，直接换候选
_NON_RETRYABLE_MARKERS = ("http 401", "http 403", "insufficient")

# 上下文预算：超预算的错误也不值得重试——同样的输入再发一次还是一样超。
# 空正文同理：max_tokens 不变、prompt 不变，重试只会再烧一次预算。
_NON_RETRYABLE_MARKERS = _NON_RETRYABLE_MARKERS + (
    "超出上下文预算", "context budget", "返回空正文",
)

# 中文语料的粗略 token 估算：1 个汉字 ≈ 1 token，ASCII 约 4 字符 ≈ 1 token。
# 宁可高估（提前拦下）也不要低估（发出去被网关截断或静默返回空文本）。
_CJK_RATIO = 1.0
_ASCII_CHARS_PER_TOKEN = 4

# 给响应预留的余量：模型输出 + 协议开销（role 标记、JSON 包装等）。
_RESPONSE_HEADROOM_TOKENS = 512


def estimate_tokens(text: str) -> int:
    """粗略估算一段文本的 token 数（纯标准库，不引入 tokenizer）。

    估算口径刻意偏保守：中文按 1 字 1 token，ASCII 按 4 字符 1 token。
    真实 tokenizer 对中文通常落在 0.6~1.5 token/字，取 1.0 是中间偏上的值。
    """
    if not text:
        return 0
    cjk = 0
    ascii_chars = 0
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff" or "\u3400" <= ch <= "\u4dbf":
            cjk += 1
        else:
            ascii_chars += 1
    return int(cjk * _CJK_RATIO) + (ascii_chars + _ASCII_CHARS_PER_TOKEN - 1) // _ASCII_CHARS_PER_TOKEN


def check_context_budget(mid: str, model: dict, system: str, user: str,
                         max_tokens: int) -> dict:
    """发请求前校验 prompt + 预期输出是否装得进模型的上下文窗口。

    返回 {"prompt_tokens", "max_tokens", "context_window", "ok"}。

    背景（2026-11-16 实测，纠正了 11-11 的初判）
    --------------------------------------------
    11-11 观察到 pass1 真实调用返回 ``completion_tokens`` 满额而 ``text`` 为空，
    当时归因为「313K 字符塞进 128K 窗口」。**这个归因是错的**：313,137 字符是
    英文语料，按 4 字符/token 只合 78,524 tokens，128K 窗口装得下。

    真正缺的是**任何**预算检查——``context_window`` 在配置里写了却从没被读过。
    中文语料才是真会撑爆的场景：313,137 个汉字 ≈ 313,137 tokens，是窗口的 2.4 倍。
    而 novel-lab 的主场景正是中文网文，所以这个缺口必须堵。

    超限的请求网关不一定报错：可能返回空文本，也可能直接断开。上层
    ``run_pass`` 只看到「JSON 解析失败」，重试 3 轮后抛 ``PassRefused``，
    用户看到的是「模型拒绝本 pass」——指不到真正原因，还白烧 3 次请求的钱。
    所以这里在发请求之前拦下，并明确告诉调用方：输入超了多少、该怎么改。
    """
    window = model.get("context_window")
    prompt_tokens = estimate_tokens(system) + estimate_tokens(user)
    info = {
        "prompt_tokens": prompt_tokens,
        "max_tokens": max_tokens,
        "context_window": window,
        "ok": True,
    }
    # 没配 context_window 的模型（自定义中转站常见）不做判断——不能凭猜测拦截。
    if not isinstance(window, int) or window <= 0:
        return info

    budget = window - max_tokens - _RESPONSE_HEADROOM_TOKENS
    info["budget"] = budget
    if prompt_tokens <= budget:
        return info

    info["ok"] = False
    raise LLMError(
        f"输入超出上下文预算：模型 '{mid}' 窗口 {window} tokens，"
        f"为输出预留 {max_tokens} + 开销 {_RESPONSE_HEADROOM_TOKENS} 后"
        f"可用 {budget}，但本次 prompt 约 {prompt_tokens} tokens"
        f"（超出约 {prompt_tokens - budget}）。\n"
        f"  这不是模型拒答，是请求根本装不下——发出去只会拿回空文本。\n"
        f"  改法：减少采样章节数（sampler 的采样量）、缩小单批输入，"
        f"或换用 context_window 更大的模型。"
    )


def _is_retryable_error(exc: Exception) -> bool:
    """该异常是否值得重试。401/403/余额不足/超预算 → False，其余（含网络层）→ True。"""
    if not isinstance(exc, LLMError):
        return True
    msg = str(exc).lower()
    return not any(marker in msg for marker in _NON_RETRYABLE_MARKERS)


def _chat_one(mid: str, model: dict, user: str, system: str,
              max_tokens: int, temperature: float, retries: int,
              json_mode: bool | None, skip_unretryable: bool) -> dict:
    """对单个模型执行「重试 retries 次」逻辑。彻底失败则抛 LLMError。

    skip_unretryable 保留在签名里是为了不破坏调用方，但它**不再影响重试**：
    不可重试的错误（401/403/余额不足/超预算/空正文）在任何路径下都只发一次。
    2026-11-16 修正——旧实现把它当成「是否允许重试」的开关，导致单模型路径
    下 401 和空正文照样重试满 retries 次，白烧预算且掩盖真实原因。
    """
    protocol = model.get("protocol", "openai")
    handler = PROTOCOL_HANDLERS.get(protocol)
    if not handler:
        raise LLMError(f"未知协议 '{protocol}'，支持: {', '.join(PROTOCOL_HANDLERS)}")

    api_key = resolve_api_key(mid, model)
    if protocol != "ollama" and not api_key:
        raise LLMError(
            f"模型 '{mid}' 缺少 API Key。\n"
            f"  设置环境变量 {model.get('api_key_env', 'N/A')}，或运行:\n"
            f"  python model_config.py key {mid}"
        )

    # 发请求前先校验装不装得下。超预算的请求网关不会报错，只会返回空文本，
    # 上层看到的是「JSON 解析失败」，根本指不到真正原因（2026-11-11 实测）。
    check_context_budget(mid, model, system, user, max_tokens)

    # json_mode 按调用覆盖（写作任务关闭，拆书任务沿用模型配置）
    if json_mode is not None:
        model = dict(model)
        model["json_mode"] = json_mode

    last_err = None
    for attempt in range(retries + 1):
        try:
            t0 = time.time()
            result = handler(model, api_key, system, user, max_tokens, temperature)
            result["model_id"] = mid
            result["model_name"] = model["model_name"]
            result["elapsed"] = round(time.time() - t0, 2)
            result["cost"] = _estimate_cost(model, result)
            return result
        except LLMError as e:
            last_err = e
            # 不可重试的错误（401/403/余额不足/超预算/空正文）无论走哪条路径
            # 都不该重试：同样的输入再发一次，结果不会变，只会再烧一次预算。
            #
            # 2026-11-16 修正：旧实现把这个判断绑在 skip_unretryable 上，
            # 导致单模型路径（skip_unretryable=False）下 401 和空正文照样
            # 重试满 retries 次。skip_unretryable 的语义应该是「是否立刻换
            # 候选模型」，不是「是否允许重试」——两者被混为一谈了。
            if not _is_retryable_error(e) or attempt >= retries:
                break
            time.sleep(2 ** attempt)
        except Exception as e:
            # 网络层异常（RemoteDisconnected/URLError/超时）也要重试
            last_err = e
            if attempt >= retries:
                break
            time.sleep(2 ** attempt + 1)
    raise LLMError(f"模型 '{mid}' 调用失败（重试 {retries} 次）: {last_err}")


def chat(user: str, system: str = "", task: str | None = None,
         model_id: str | None = None, max_tokens: int = 8192,
         temperature: float = 0.7, retries: int = 2,
         json_mode: bool | None = None,
         allow_fallback: bool = True) -> dict:
    """
    统一调用入口。

    task: 任务名（pass1_structure / pass3_style / writing ...），按路由表选模型
    model_id: 显式指定模型，优先级高于 task
    json_mode: None=沿用模型配置；True/False=强制开启/关闭。
       写作任务必须传 False——小说正文不是 JSON。
    allow_fallback: True（默认）时按 resolve_fallback_chain 依次尝试候选模型；
       False 时只对主模型重试 retries 次，行为与不启用备用模型时完全一致。
       连通性测试应传 False——否则会把「备用模型通了」误报成「主模型通了」。
    """
    if not allow_fallback:
        mid, model = resolve_model(task, model_id)
        return _chat_one(mid, model, user, system, max_tokens, temperature,
                         retries, json_mode, skip_unretryable=False)

    chain = resolve_fallback_chain(task, model_id)
    if not chain:
        raise LLMError("尚未配置任何模型。运行: python model_config.py add")

    models = load_models()["models"]
    failures = []
    for mid in chain:
        try:
            return _chat_one(mid, models[mid], user, system, max_tokens,
                             temperature, retries, json_mode, skip_unretryable=True)
        except LLMError as e:
            failures.append((mid, str(e)))

    if len(chain) == 1:
        raise LLMError(
            f"模型 '{chain[0]}' 调用失败（重试 {retries} 次）: {failures[0][1]}"
            f"（无可用备用模型）"
        )
    detail = "；".join(f"候选 {mid}: {reason}" for mid, reason in failures)
    raise LLMError(f"全部 {len(chain)} 个候选模型均失败：{detail}")


def _estimate_cost(model: dict, result: dict) -> float:
    """按配置的价格估算本次花费（元）。本地模型为 0"""
    try:
        pin = float(model.get("price_in_per_1m", 0) or 0)
    except (ValueError, TypeError):
        pin = 0.0
    try:
        pout = float(model.get("price_out_per_1m", 0) or 0)
    except (ValueError, TypeError):
        pout = 0.0
    try:
        pt = float(result.get("prompt_tokens", 0) or 0)
        ct = float(result.get("completion_tokens", 0) or 0)
    except (ValueError, TypeError):
        return 0.0
    return round(
        pt / 1_000_000 * pin + ct / 1_000_000 * pout,
        4,
    )


def test_model(model_id: str) -> dict:
    """连通性测试。配完模型必须能一键验证，否则用户不知道配对没配对"""
    cfg = load_models()
    if model_id not in cfg["models"]:
        return {"ok": False, "error": f"模型 '{model_id}' 不存在"}
    try:
        r = chat(
            user="请只回复两个字：正常",
            system="你是一个测试助手，严格按要求回复。",
            model_id=model_id,
            max_tokens=32,
            temperature=0,
            retries=0,
            # 连通性测试必须只测这一个模型：否则备用模型通了会被误报成主模型通了
            allow_fallback=False,
        )
        return {
            "ok": True,
            "reply": r["text"].strip()[:50],
            "elapsed": r["elapsed"],
            "tokens": r["prompt_tokens"] + r["completion_tokens"],
        }
    except LLMError as e:
        return {"ok": False, "error": str(e)}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print("用法: python llm_client.py <model_id>   # 连通性测试")
        return 2
    if argv[0] in ("-h", "--help"):
        print("用法: python llm_client.py <model_id>   # 连通性测试")
        return 0
    _result = test_model(argv[0])
    print(json.dumps(_result, ensure_ascii=False, indent=2))
    return 0 if _result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
