import json
import logging
import re
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from time import perf_counter

from app.api.deps import get_current_user_id, get_db
from app.runtime.code_executor import code_runtime_executor
from app.runtime.llm_service import LLMRequest, llm_service
from app.runtime.mcp_client import (
    extract_tool_result_text,
    get_mcp_client,
    mcp_tool_to_openai,
)
from app.runtime.knowledge_service import KnowledgeService
from app.runtime.providers import _supports_function_calling
from app.runtime.file_references import extract_referenced_file_paths
from app.runtime.skill_executor import SkillRuntime
from app.runtime.skill_activation import skill_activation_engine
from app.runtime.artifact_skills.registry import run_artifact_skill_pipelines
from app.runtime.skill_code_runner import skill_code_runner, should_attempt_skill_code_runner
from app.runtime.skill_loader import build_skill_catalog_text, find_skill, render_loaded_skill
from app.runtime.agent_engine import LangChainLLMWrapper, ReActAgent, ToolManager
from app.schemas.resource import (
    CodeExecutionAuditRecord,
    ChatMessageRecord,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionRecord,
    RuntimeRunEventRecord,
    RuntimeRunRecord,
)
from app.services.postgres_store import store
from app.services.user_file_service import user_file_service

logger = logging.getLogger(__name__)
router = APIRouter()


def _is_skill_listing_query(text: str) -> bool:
    normalized = (text or "").strip().lower()
    patterns = [
        r"有哪些\s*skills?",
        r"有哪?些\s*skill",
        r"what\s+skills?\s+do\s+you\s+have",
        r"list\s+.*skills?",
        r"当前\s*skills?",
        r"有什么\s*skills?",
        r"现在\s*.*\s*什么\s*skills?",
    ]
    return any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in patterns)


def _render_bound_skills(bound_skills: list[dict]) -> str:
    if not bound_skills:
        return "当前没有绑定任何 Skill。"

    lines = ["当前我已绑定并可用的 Skills："]
    for idx, skill in enumerate(bound_skills, start=1):
        name = skill.get("name") or skill.get("skill_id")
        version = skill.get("version") or "-"
        entrypoint = skill.get("entrypoint") or "-"
        desc = skill.get("description") or ""
        purpose = skill.get("purpose") or desc or "未提供"
        capabilities = skill.get("capabilities") or []
        caps_text = "、".join(str(item) for item in capabilities[:6]) if capabilities else "-"
        lines.append(f"{idx}. {name}")
        lines.append(f"   - 用途: {purpose}")
        lines.append(f"   - version: {version}")
        lines.append(f"   - entrypoint: {entrypoint}")
        lines.append(f"   - capabilities: {caps_text}")
        if desc:
            lines.append(f"   - description: {desc}")

    lines.append("如你希望我调用某个 Skill，请直接说“使用 <Skill 名称> 来处理 …”，我会在回复中标注使用的 Skill。")
    return "\n".join(lines)


def _extract_mentioned_skills(text: str, bound_skills: list[dict]) -> list[str]:
    normalized = (text or "").lower()
    result: list[str] = []
    for item in bound_skills:
        name = str(item.get("name") or "").strip()
        if name and name.lower() in normalized:
            result.append(name)
    return list(dict.fromkeys(result))




def _llm_answer_or_error(llm_response) -> str:
    if llm_response and llm_response.ok and llm_response.text:
        return llm_response.text

    error = getattr(llm_response, "error", None) if llm_response else "empty LLM response"
    provider = getattr(llm_response, "provider", None) if llm_response else None
    model_name = getattr(llm_response, "model_name", None) if llm_response else None
    details = ""
    if provider or model_name:
        details = f"（provider={provider or '-'}, model={model_name or '-'}）"
    return (
        "模型请求失败，当前没有生成可保存的结果。"
        f"{details}\n\n"
        f"错误信息：{error or 'empty LLM response'}"
    )

def _skill_display_name(skill: dict) -> str:
    return str(skill.get("name") or skill.get("skill_id") or "skill").strip()



def _looks_truncated_design_output(answer: str) -> bool:
    text = (answer or "").rstrip()
    if not text:
        return False

    lowered = text.lower()
    if text.count("```") % 2 == 1:
        return True
    if "<html" in lowered and "</html>" not in lowered:
        return True
    if "<style" in lowered and "</style>" not in lowered:
        return True

    truncated_endings = (
        "transform:",
        "background:",
        "color:",
        "padding:",
        "margin:",
        "width:",
        "height:",
        "top:",
        "left:",
        "right:",
        "bottom:",
        "opacity:",
        "font-size:",
        "line-height:",
        "{",
        ":",
        "=",
    )
    return any(text.endswith(item) for item in truncated_endings)


def _is_design_request(user_text: str) -> bool:
    """Check if the user's question is actually about design or page creation."""
    normalized = (user_text or "").strip().lower()
    if not normalized:
        return False

    design_keywords = {
        "设计", "design", "页面", "page", "website", "首页", "主页", "首頁",
        "前端", "frontend", "网站", "web", "homepage", "布局", "layout",
        "样式", "style", "ui", "ux", "界面", "interface", "创建", "create",
        "制作", "make", "建立", "build", "开发", "develop", "卖", "售", "花",
    }
    return any(keyword in normalized for keyword in design_keywords)


def _repair_truncated_design_output(answer: str) -> str:
    text = (answer or "").rstrip()
    if not text:
        return text

    if "\n" in text:
        text = text.rsplit("\n", 1)[0].rstrip()

    lowered = text.lower()
    suffix_parts: list[str] = []
    if "<style" in lowered and "</style>" not in lowered:
        suffix_parts.append("}")
        suffix_parts.append("</style>")
    if "<body" in lowered and "</body>" not in lowered:
        suffix_parts.append("</body>")
    if "<html" in lowered and "</html>" not in lowered:
        suffix_parts.append("</html>")
    if text.count("```") % 2 == 1:
        suffix_parts.append("```")

    if suffix_parts:
        text = f"{text}\n" + "\n".join(suffix_parts)
    return text


def _build_design_skill_brief(user_text: str, bound_skills: list[dict]) -> str:
    subject = (user_text or "").strip() or "高端品牌网站首页"

    brief = [
        "Frontend-design artifact mode: create the final downloadable page, not a chat explanation.",
        "Client brief: " + subject,
        "Follow the activated frontend-design SKILL.md as the operating manual. Treat it as a design process, not decorative context.",
        "Before writing code, internally complete the skill's two-pass process: subject grounding, compact token system, layout concept, signature element, critique against generic AI defaults, revise, then build. Do not reveal this planning.",
        "Output exactly one complete standalone HTML document. Start with <!DOCTYPE html> and end with </html>. No markdown fences, no labels, no prose before or after the file.",
        "The HTML must include complete <head>, <style>, and <body> sections, responsive CSS, accessible focus states, and prefers-reduced-motion handling if animation is used.",
        "Make the page content rich enough for a real homepage: navigation, a distinctive hero, product/service proof, several subject-specific sections, calls to action, and a footer. Do not return a sparse hero-only mockup.",
        "Ground every visible detail in the user's subject. Infer audience, offering, materials, vocabulary, imagery direction, and interactions from the request. Avoid generic copy like 'clear proposition', 'complete structure', or 'can continue iterating'.",
        "Avoid the common default looks unless the brief truly asks for them: warm cream plus terracotta serif, near-black with neon accent, and broadsheet hairline newspaper layout. Choose a palette, typography, and signature visual specific to this subject.",
        "Use CSS/code-native visuals or inline SVG only when they directly express the subject. Do not depend on external network assets for core rendering.",
        "Spend boldness in one memorable place, keep the rest disciplined, and make the first viewport feel finished and intentional on desktop and mobile.",
    ]
    return "\n\n".join(brief)

def _skill_name_matches(names: list[str], candidates: set[str]) -> bool:
    return any(str(name).strip().lower() in candidates for name in names)
def _is_front_design_active(names: list[str]) -> bool:
    return _skill_name_matches(names, {"frontend-design", "front-design"})


def _select_skill_code_runner_candidate(
    bound_skills: list[dict],
    activated_skill_names: list[str],
    user_text: str,
    referenced_files: list[str],
) -> dict | None:
    activated = {str(name).strip().lower() for name in activated_skill_names}
    if not activated:
        return None
    for skill in bound_skills:
        name = _skill_display_name(skill).lower()
        if name in activated and should_attempt_skill_code_runner(skill, user_text, referenced_files):
            return skill
    return None


def _strip_markdown_code_fence(text: str) -> str:
    value = (text or "").strip()
    fence = re.match(r"^```[a-zA-Z0-9_-]*\s*([\s\S]*?)\s*```$", value)
    if fence:
        return fence.group(1).strip()
    return value


def _extract_html_artifact(answer: str) -> str:
    text = _strip_markdown_code_fence(answer)
    text = re.sub(r"^\s*(html|copy|html\s+copy)\s*\n+", "", text, flags=re.IGNORECASE)
    text = text.replace("```html", "").replace("```css", "").replace("```", "")

    lowered = text.lower()
    start_match = re.search(r"<!doctype\s+html|<html[\s>]", lowered)
    if start_match:
        text = text[start_match.start():]

    lowered = text.lower()
    if "<html" not in lowered:
        return ""
    if "</html>" in lowered:
        end = lowered.rfind("</html>") + len("</html>")
        text = text[:end]
    else:
        text = _repair_truncated_design_output(text)

    return text.strip()


def _derive_artifact_title(user_text: str, fallback: str = "artifact") -> str:
    text = re.sub(r"\s+", " ", (user_text or "").strip())
    text = re.sub(r"(?i)\buse\s+[\w-]+\s+skill\b", "", text)
    text = re.sub(r"使用\s*[\w\-\u4e00-\u9fff]+\s*skill\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(帮我|请|生成|创建|制作|设计|写一个|做一个|一个|一份|左右|即可)", "", text)
    text = re.sub(r"[，。,.!?！？；;:：].*$", "", text).strip()
    return text[:40] or fallback


def _safe_artifact_filename(title: str, suffix: str) -> str:
    safe = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", title).strip("_")
    safe = safe[:48] or "artifact"
    return f"{safe}.{suffix.lstrip('.')}"


def _html_escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _build_front_design_fallback_html(user_text: str) -> str:
    title = _derive_artifact_title(user_text, fallback="品牌首页")
    escaped_title = _html_escape(title)
    escaped_brief = _html_escape((user_text or title).strip())
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escaped_title}</title>
<style>
:root{{--ink:#17201b;--paper:#fbf7ef;--muted:#6c756c;--line:#d8dfd0;--moss:#5b7450;--rose:#c46a55;--amber:#d8a43a;--night:#202f34;--milk:#fffdf8}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:"Segoe UI","Noto Sans SC",system-ui,sans-serif;letter-spacing:0}}a{{color:inherit;text-decoration:none}}a:focus-visible,button:focus-visible{{outline:3px solid rgba(196,106,85,.45);outline-offset:4px}}.shell{{min-height:100vh;background:radial-gradient(circle at 82% 18%,rgba(216,164,58,.22),transparent 28%),linear-gradient(115deg,#fbf7ef 0%,#fffdf8 48%,#eef3e8 100%)}}.nav{{height:76px;display:flex;align-items:center;justify-content:space-between;padding:0 clamp(22px,5vw,72px);border-bottom:1px solid rgba(23,32,27,.12);backdrop-filter:blur(18px);position:sticky;top:0;z-index:20;background:rgba(251,247,239,.82)}}.brand{{display:flex;align-items:center;gap:13px;font-weight:850;font-size:20px}}.mark{{width:38px;height:38px;border-radius:40% 60% 50% 50%;background:linear-gradient(135deg,var(--moss),var(--amber));box-shadow:inset 0 0 0 1px rgba(255,255,255,.35)}}.links{{display:flex;gap:28px;color:var(--muted);font-size:14px}}.hero{{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(340px,.95fr);gap:clamp(32px,6vw,92px);align-items:center;padding:clamp(48px,7vw,96px) clamp(22px,5vw,72px) clamp(52px,7vw,88px)}}.eyebrow{{font-size:12px;font-weight:850;text-transform:uppercase;color:var(--rose);letter-spacing:.18em}}h1{{font-family:Georgia,"Times New Roman","Noto Serif SC",serif;font-size:clamp(44px,7vw,94px);line-height:.96;margin:18px 0 22px;max-width:820px;font-weight:650}}.lede{{font-size:clamp(17px,2vw,21px);line-height:1.85;color:#576156;max-width:720px}}.actions{{display:flex;gap:14px;flex-wrap:wrap;margin-top:34px}}.btn{{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:0 20px;border:1px solid rgba(23,32,27,.28);border-radius:999px;font-weight:800;background:rgba(255,255,255,.5)}}.btn.primary{{background:var(--night);color:white;border-color:var(--night)}}.visual{{min-height:560px;position:relative;overflow:hidden;border-radius:34px;background:linear-gradient(155deg,var(--night),#496358 48%,#e1bb63);box-shadow:0 34px 90px rgba(32,47,52,.23)}}.visual:before{{content:"";position:absolute;inset:24px;border:1px solid rgba(255,255,255,.32);border-radius:26px}}.ribbon{{position:absolute;left:34px;right:34px;bottom:38px;padding:24px;border-radius:22px;background:rgba(255,253,248,.86);backdrop-filter:blur(18px);display:grid;grid-template-columns:1fr auto;gap:18px;align-items:end}}.ribbon strong{{display:block;font-size:26px;font-family:Georgia,"Noto Serif SC",serif}}.ribbon span{{color:#66705f;line-height:1.7}}.sig{{position:absolute;width:54%;aspect-ratio:1;border-radius:44% 56% 58% 42%;right:8%;top:10%;background:radial-gradient(circle at 35% 28%,#fff7df 0 12%,#e5bd55 13% 35%,#c46a55 36% 54%,#5b7450 55% 100%);box-shadow:0 28px 80px rgba(0,0,0,.28);animation:float 8s ease-in-out infinite}}.grain{{position:absolute;inset:0;background:repeating-linear-gradient(90deg,rgba(255,255,255,.08) 0 1px,transparent 1px 14px);mix-blend-mode:soft-light}}.sections{{padding:20px clamp(22px,5vw,72px) 82px;display:grid;gap:26px}}.band{{display:grid;grid-template-columns:.42fr 1fr;gap:34px;padding:34px 0;border-top:1px solid var(--line)}}.band h2{{font-size:clamp(28px,4vw,52px);line-height:1.05;margin:0;font-family:Georgia,"Noto Serif SC",serif}}.copygrid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}}.item{{background:rgba(255,255,255,.58);border:1px solid rgba(23,32,27,.1);border-radius:18px;padding:22px;min-height:180px}}.item b{{font-size:18px}}.item p{{color:#66705f;line-height:1.75;margin:12px 0 0}}.strip{{padding:44px clamp(22px,5vw,72px);background:var(--night);color:white;display:grid;grid-template-columns:1fr auto;gap:24px;align-items:center}}.strip p{{margin:8px 0 0;color:rgba(255,255,255,.72);line-height:1.7}}footer{{padding:34px clamp(22px,5vw,72px);display:flex;justify-content:space-between;gap:20px;color:#66705f}}@keyframes float{{0%,100%{{transform:translateY(0) rotate(-3deg)}}50%{{transform:translateY(18px) rotate(3deg)}}}}@media(prefers-reduced-motion:reduce){{.sig{{animation:none}}}}@media(max-width:880px){{.links{{display:none}}.hero{{grid-template-columns:1fr;padding-top:42px}}.visual{{min-height:430px}}.band{{grid-template-columns:1fr}}.copygrid{{grid-template-columns:1fr}}.strip{{grid-template-columns:1fr}}footer{{display:block}}}}
</style>
</head>
<body>
<div class="shell">
<nav class="nav"><a class="brand" href="#top"><span class="mark" aria-hidden="true"></span><span>{escaped_title}</span></a><div class="links"><a href="#signature">特色</a><a href="#experience">体验</a><a href="#contact">联系</a></div></nav>
<main id="top">
<section class="hero"><div><div class="eyebrow">crafted homepage direction</div><h1>{escaped_title}</h1><p class="lede">{escaped_brief}</p><div class="actions"><a class="btn primary" href="#contact">预约了解</a><a class="btn" href="#signature">查看亮点</a></div></div><div class="visual" aria-label="主题品牌视觉"><div class="grain"></div><div class="sig"></div><div class="ribbon"><div><strong>围绕真实主题建立记忆点</strong><span>把用户请求转译为首屏视觉、内容模块和行动路径，而不是只摆放通用卡片。</span></div><a class="btn" href="#experience">浏览</a></div></div></section>
<section class="sections" id="signature"><div class="band"><h2>一个可被记住的首页，不从模板开始。</h2><div class="copygrid"><article class="item"><b>主题化主视觉</b><p>用色彩、形态和版式回应页面对象，让第一屏就能看出这个品牌在卖什么、服务谁。</p></article><article class="item"><b>完整内容节奏</b><p>从品牌承诺到产品/服务亮点，再到信任理由和行动入口，形成可浏览的真实首页结构。</p></article><article class="item"><b>克制的高级感</b><p>把视觉风险集中在一个标志性元素上，其余区域用留白、层级和细节承担质感。</p></article></div></div><div class="band" id="experience"><h2>为后续真实素材和业务信息预留空间。</h2><div class="copygrid"><article class="item"><b>精选展示</b><p>适合替换为产品系列、服务套餐、案例图片或核心卖点。</p></article><article class="item"><b>购买路径</b><p>清晰的 CTA 与栏目锚点，用户能快速进入咨询、下单或查看更多内容。</p></article><article class="item"><b>移动端友好</b><p>布局在窄屏下自然堆叠，按钮、文字和视觉元素保持可读。</p></article></div></div></section>
<section class="strip" id="contact"><div><strong>{escaped_title}</strong><p>这个文件是可直接预览和继续编辑的单文件 HTML，可在 My Files 下载后替换真实文案与素材。</p></div><a class="btn primary" href="#top">回到顶部</a></section>
</main>
<footer><span>{escaped_title}</span><span>Generated with frontend-design Skill artifact pipeline</span></footer>
</div>
</body>
</html>"""

def _extract_generated_files_payload(answer: str) -> list[dict]:
    text = (answer or "").strip()
    if not text:
        return []

    try:
        payload = json.loads(text)
        if isinstance(payload, dict) and isinstance(payload.get("generated_files"), list):
            return payload["generated_files"]
    except Exception:
        pass

    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, flags=re.IGNORECASE)
    if match:
        try:
            payload = json.loads(match.group(1))
            if isinstance(payload, dict) and isinstance(payload.get("generated_files"), list):
                return payload["generated_files"]
        except Exception:
            return []
    return []


def _decode_code_result(code_result: dict | str) -> tuple[str, list[str], list[dict[str, str]], bool]:
    text = code_result.get("text", "") if isinstance(code_result, dict) else str(code_result)
    used_tools = list(code_result.get("used_tools", [])) if isinstance(code_result, dict) else []
    used_mcps = list(code_result.get("used_mcps", [])) if isinstance(code_result, dict) else []
    return str(text), used_tools, used_mcps, llm_service.code_requests_llm(str(text))


@router.get("/agents/{agent_id}/debug", tags=["debug"])
def debug_agent_config(
    agent_id: str,
    project_id: str = Query(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    """Debug endpoint: return agent config and associated resources."""
    agent = store.get_agent_resource_for_project(db, project_id, agent_id)
    config = dict(agent.config or {})
    mcp_ids = list(config.get("mcp_ids") or [])
    
    # Ensure mcp_ids is a list of strings
    mcp_ids = [str(mid) for mid in mcp_ids if mid]
    
    mcps = store.list_mcp_resources_for_project(db, project_id=project_id, mcp_ids=mcp_ids, actor=user_id)
    
    tools_preview: list[dict] = []
    for mcp_spec in mcps:
        mcp_name = str(mcp_spec.get("name") or "")
        try:
            client = get_mcp_client(mcp_spec)
            tools = client.list_tools()
            tools_preview.append({
                "mcp_name": mcp_name,
                "mcp_id": mcp_spec.get("id"),
                "endpoint_url": mcp_spec.get("endpoint_url"),
                "transport": mcp_spec.get("transport"),
                "tool_count": len(tools),
                "tools": [{"name": t.get("name"), "description": t.get("description", "")} for t in tools[:3]],  # first 3
            })
        except Exception as exc:
            tools_preview.append({
                "mcp_name": mcp_name,
                "mcp_id": mcp_spec.get("id"),
                "error": str(exc),
            })
    
    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "model_provider": agent.model_provider,
        "model_name": agent.model_name,
        "run_mode": config.get("run_mode", "llm"),
        "system_prompt": config.get("system_prompt", ""),
        "mcp_ids_in_config": mcp_ids,
        "mcps_count": len(mcps),
        "mcps": tools_preview,
    }


@router.get("/code-execution-audits", response_model=list[CodeExecutionAuditRecord])
def list_code_execution_audits(
    project_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    return store.list_code_execution_audits(db, user_id=user_id, project_id=project_id, limit=limit)


@router.post("/projects/{project_id}/sessions")
def create_chat_session(
    project_id: str,
    payload: ChatSessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> dict:
    return store.create_chat_session(db, project_id, user_id, payload.title)


@router.get("/projects/{project_id}/sessions", response_model=list[ChatSessionRecord])
def list_chat_sessions(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    return store.list_chat_sessions(db, project_id, user_id, limit=limit)


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageRecord])
def list_chat_messages(
    session_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    return store.list_chat_messages_for_user(db, session_id, user_id, limit=limit)


@router.get("/sessions/{session_id}/runs", response_model=list[RuntimeRunRecord])
def list_runtime_runs(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    return store.list_runtime_runs_for_session(db, session_id, user_id, limit=limit)


@router.get("/runs/{run_id}/events", response_model=list[RuntimeRunEventRecord])
def list_runtime_run_events(
    run_id: str,
    limit: int = Query(default=500, ge=1, le=1000),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[dict]:
    return store.list_runtime_run_events(db, run_id, user_id, limit=limit)


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: str,
    payload: ChatMessageRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    print(f"[send_message] ✓ Request received: session_id={session_id}, agent_id={payload.agent_id}, text={payload.text[:50]}")
    logger.info(f"[send_message] ✓ Request received: session_id={session_id}, agent_id={payload.agent_id}, text={payload.text[:50]}")
    session = store.get_chat_session_for_user(db, session_id, user_id)
    run = store.create_runtime_run(
        db=db,
        session=session,
        user_id=user_id,
        input_text=payload.text,
        agent_id=payload.agent_id,
    )
    store.append_runtime_run_event(
        db=db,
        run_id=run.id,
        stage="runtime",
        status="running",
        message="Runtime execution started",
        payload={"session_id": session.id},
    )

    model_provider: str | None = None
    model_name: str | None = None
    provider_profile: str | None = None
    provider_connection_id: str | None = None
    provider_connection: dict | None = None
    system_prompt: str | None = None
    run_mode = "llm"
    custom_code = ""
    agent_config: dict = {}
    tools: list[dict] = []
    mcps: list[dict] = []
    bound_skills: list[dict] = []
    activated_skill_names: list[str] = []
    skill_activation_reasons: list[dict] = []
    design_skill_active = False
    executable_skill_results: list[dict] = []
    direct_skill_artifact_paths: list[str] = []
    referenced_file_paths: list[str] = extract_referenced_file_paths(payload.text)
    used_knowledge_bases: list[str] = []  # initialize before agent_id block
    agent_name: str | None = None
    if payload.agent_id:
        agent_resource = store.get_agent_resource_for_project(db, session.project_id, payload.agent_id)
        agent_name = agent_resource.name
        model_provider = agent_resource.model_provider
        model_name = agent_resource.model_name
        agent_config = dict(agent_resource.config or {})
        logger.info(f"[send_message] Agent resource loaded: id={payload.agent_id}, raw_config={agent_resource.config}")
        # Override agent config with request parameters if provided
        if payload.engine_type:
            agent_config["engine_type"] = payload.engine_type
        if payload.provider_profile:
            agent_config["provider_profile"] = payload.provider_profile
        if payload.temperature is not None:
            agent_config["temperature"] = payload.temperature
        if payload.max_iterations is not None:
            agent_config["max_iterations"] = payload.max_iterations
        if payload.mcp_ids is not None:
            agent_config["mcp_ids"] = payload.mcp_ids
        provider_profile = agent_config.get("provider_profile")
        provider_connection_id = agent_config.get("provider_connection_id")
        if provider_connection_id:
            provider_connection = store.get_provider_connection_runtime_config(
                db,
                connection_id=provider_connection_id,
                actor=user_id,
            )
        system_prompt = agent_config.get("system_prompt")
        run_mode = str(agent_config.get("run_mode") or "llm").strip().lower()
        custom_code = str(agent_config.get("custom_code") or "")
        tools = store.list_tool_resources_for_project(
            db,
            project_id=session.project_id,
            tool_ids=list(agent_config.get("tool_ids") or []),
            actor=user_id,
        )
        # Ensure mcp_ids is a list of strings; convert from string if needed
        raw_mcp_ids = agent_config.get("mcp_ids") or []
        mcp_ids_list: list[str] = []
        if isinstance(raw_mcp_ids, str):
            # Handle case where mcp_ids was stored as a single string
            mcp_ids_list = [raw_mcp_ids] if raw_mcp_ids else []
        else:
            mcp_ids_list = [str(mid) for mid in raw_mcp_ids if mid]
        
        logger.info(f"[send_message] Agent {payload.agent_id} config: {agent_config}")
        logger.info(f"[send_message] Agent {payload.agent_id} has mcp_ids (raw): {raw_mcp_ids}")
        logger.info(f"[send_message] Agent {payload.agent_id} has mcp_ids (list): {mcp_ids_list}")
        
        mcps = store.list_mcp_resources_for_project(
            db,
            project_id=session.project_id,
            mcp_ids=mcp_ids_list,
            actor=user_id,
        )
        logger.info(f"[send_message] Loaded {len(mcps)} MCPs: {[m.get('name') for m in mcps]}")

        bound_skills = store.list_skill_resources_for_agent(
            db,
            project_id=session.project_id,
            agent_id=payload.agent_id,
            actor=user_id,
        )

        config_skill_ids = [str(item) for item in (agent_config.get("skill_ids") or []) if item]
        config_skills = store.list_skill_resources_for_project(
            db,
            project_id=session.project_id,
            skill_ids=config_skill_ids,
            actor=user_id,
        )

        merged: dict[str, dict] = {}
        for item in bound_skills + config_skills:
            skill_key = str(item.get("skill_id") or "")
            if not skill_key:
                continue
            if skill_key not in merged:
                merged[skill_key] = item
        bound_skills = list(merged.values())
        logger.info(
            f"[send_message] Loaded {len(bound_skills)} bound skills: "
            f"{[s.get('name') for s in bound_skills]}"
        )

        if bound_skills:
            skill_activation = skill_activation_engine.activate(payload.text, bound_skills)
            skill_prompt = skill_activation.discovery_prompt
            activated_skill_names = skill_activation.activated_names
            skill_activation_reasons = skill_activation.activation_reasons
            design_skill_active = any(
                str(name).strip().lower() in {"frontend-design", "front-design"}
                for name in activated_skill_names
            )
            is_design_req = _is_design_request(payload.text)
            print(f"[send_message] Design skill detection: design_skill_active={design_skill_active}, is_design_request={is_design_req}, text={payload.text[:50]}")
            logger.info(f"[send_message] Design skill detection: design_skill_active={design_skill_active}, is_design_request={is_design_req}, text={payload.text[:50]}")
            if design_skill_active and is_design_req:
                print(f"[send_message] ✓ Design brief injected!")
                logger.info(f"[send_message] ✓ Design brief injected!")
                skill_prompt += "\n" + _build_design_skill_brief(payload.text, bound_skills)
            else:
                print(f"[send_message] ✗ Design brief NOT injected (active={design_skill_active}, request={is_design_req})")
                logger.info(f"[send_message] ✗ Design brief NOT injected (active={design_skill_active}, request={is_design_req})")
            if system_prompt:
                system_prompt = f"{system_prompt}\n\n{skill_prompt}"
            else:
                system_prompt = skill_prompt
            store.append_runtime_run_event(
                db=db,
                run_id=run.id,
                stage="skill",
                status="activated" if activated_skill_names else "discovered",
                message="Skill discovery and progressive disclosure applied",
                payload={"available_skills": [_skill_display_name(s) for s in bound_skills], "activated_skills": activated_skill_names, "activation_reasons": skill_activation_reasons},
            )

            if activated_skill_names:
                skill_runtime = SkillRuntime(db)
                activated_name_set = {str(name).strip().lower() for name in activated_skill_names}
                for skill in bound_skills:
                    skill_name = _skill_display_name(skill)
                    if skill_name.lower() not in activated_name_set:
                        continue
                    if not skill_runtime.can_execute(skill):
                        store.append_runtime_run_event(
                            db=db,
                            run_id=run.id,
                            stage="skill_runtime",
                            status="skipped",
                            message=f"Skill has no executable entrypoint: {skill_name}",
                            payload={"skill": skill_name, "entrypoint": skill.get("entrypoint") or ""},
                        )
                        continue

                    safe_runtime_skill_name = re.sub(r"[^\w\-]+", "_", skill_name)
                    runtime_output_dir = f"generated/{safe_runtime_skill_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    runtime_result = skill_runtime.execute(
                        skill=skill,
                        input_data={
                            "text": payload.text,
                            "input_text": payload.text,
                            "files": referenced_file_paths,
                            "project_id": session.project_id,
                            "session_id": session.id,
                            "agent_id": payload.agent_id,
                            "user_id": user_id,
                            "config": agent_config,
                        },
                        context={
                            "project_id": session.project_id,
                            "session_id": session.id,
                            "agent_id": payload.agent_id,
                            "user_id": user_id,
                            "files": referenced_file_paths,
                        },
                        timeout_seconds=int((skill.get("instance_config") or {}).get("timeout_seconds") or 30),
                        user_id=user_id,
                        output_base_dir=runtime_output_dir,
                    )
                    executable_skill_results.append({"skill": skill_name, **runtime_result})
                    store.append_runtime_run_event(
                        db=db,
                        run_id=run.id,
                        stage="skill_runtime",
                        status=runtime_result.get("status") or "unknown",
                        message=f"SkillRuntime executed: {skill_name}",
                        payload={
                            "skill": skill_name,
                            "entrypoint": skill.get("entrypoint") or "",
                            "status": runtime_result.get("status"),
                            "saved_files": runtime_result.get("saved_files") or [],
                            "error": runtime_result.get("error_message"),
                            "execution_id": runtime_result.get("execution_id"),
                        },
                    )
        # RAG: Load and retrieve from knowledge bases
        knowledge_base_ids = list(agent_config.get("knowledge_base_ids") or [])
        rag_context = ""
        used_knowledge_bases = []
        
        if knowledge_base_ids:
            logger.info(f"[send_message] Agent has {len(knowledge_base_ids)} knowledge bases: {knowledge_base_ids}")
            try:
                # Generate embedding for user query (optional - text search fallback if fails)
                query_embedding = None
                try:
                    emb_result = await KnowledgeService.get_embeddings(
                        texts=[payload.text],
                        model="embedding-3",
                        embedding_provider="openai",
                    )
                    if emb_result and len(emb_result) > 0:
                        query_embedding = emb_result[0]
                except Exception as emb_err:
                    logger.warning(f"[send_message] Embedding failed, using text search: {emb_err}")

                # Build RAG context (vector search if embedding available, else text search)
                rag_context = await KnowledgeService.build_rag_context(
                    db=db,
                    agent_id=payload.agent_id,
                    query_text=payload.text,
                    query_embedding=query_embedding,
                    knowledge_base_ids=knowledge_base_ids,
                )
                
                if rag_context.strip():
                    logger.info(f"[send_message] RAG context retrieved: {len(rag_context)} chars")
                    # Inject RAG context into system prompt
                    kb_prompt = f"""
You have access to the following knowledge base content relevant to the user's query:

{rag_context}

Use this information to provide accurate and informed responses. When relevant, cite the source documents."""
                    
                    if system_prompt:
                        system_prompt = f"{system_prompt}\n\n{kb_prompt}"
                    else:
                        system_prompt = kb_prompt
                    
                    # Track which knowledge bases were used
                    used_knowledge_bases = knowledge_base_ids
                else:
                    logger.info(f"[send_message] No relevant content found in knowledge bases for this query")
            except Exception as e:
                logger.warning(f"[send_message] Failed to retrieve RAG context: {str(e)}", exc_info=True)
        
        store.append_runtime_run_event(
            db=db,
            run_id=run.id,
            stage="agent",
            status="selected",
            message="Agent selected for runtime",
            payload={
                "agent_id": payload.agent_id,
                "model_provider": model_provider,
                "model_name": model_name,
                "provider_connection_id": provider_connection_id,
                "run_mode": run_mode,
                "used_knowledge_bases": used_knowledge_bases,
            },
        )
    else:
        # No agent_id provided, apply request parameters to agent_config
        if payload.engine_type:
            agent_config["engine_type"] = payload.engine_type
        if payload.provider_profile:
            agent_config["provider_profile"] = payload.provider_profile
        if payload.temperature is not None:
            agent_config["temperature"] = payload.temperature
        if payload.max_iterations is not None:
            agent_config["max_iterations"] = payload.max_iterations
        if payload.mcp_ids is not None:
            agent_config["mcp_ids"] = payload.mcp_ids

    try:
        store.append_chat_message(db, session_id, role="user", text=payload.text, agent_id=payload.agent_id)
        used_tools: list[str] = []
        used_mcps: list[dict[str, str]] = []
        used_skills: list[str] = []

        is_skill_inventory_query = _is_skill_listing_query(payload.text)
        mentioned_skills = _extract_mentioned_skills(payload.text, bound_skills) if bound_skills else []

        if is_skill_inventory_query:
            answer = _render_bound_skills(bound_skills)
            used_skills = [str(item.get("name") or item.get("skill_id")) for item in bound_skills]
            store.append_runtime_run_event(
                db=db,
                run_id=run.id,
                stage="skill",
                status="succeeded",
                message="Returned bound skill inventory",
                payload={"skills": used_skills},
            )
        elif run_mode != "code" and (code_runner_skill := _select_skill_code_runner_candidate(
            bound_skills,
            activated_skill_names,
            payload.text,
            referenced_file_paths,
        )):
            skill_name = _skill_display_name(code_runner_skill)
            code_runner_result = skill_code_runner.run(
                skill=code_runner_skill,
                user_text=payload.text,
                user_id=user_id,
                referenced_files=referenced_file_paths,
                output_base_dir=f"generated/{re.sub('[^A-Za-z0-9_-]+', '_', skill_name).strip('_') or 'skill'}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                model_provider=model_provider,
                model_name=model_name,
                provider_profile=provider_profile,
                provider_connection_id=provider_connection_id,
                provider_connection=provider_connection,
                timeout_seconds=int((code_runner_skill.get("instance_config") or {}).get("code_timeout_seconds") or 90),
            )
            answer = code_runner_result.answer
            used_skills = [skill_name]
            direct_skill_artifact_paths.extend(code_runner_result.saved_files)
            for event in code_runner_result.events:
                store.append_runtime_run_event(
                    db=db,
                    run_id=run.id,
                    stage=event.get("stage") or "skill_code_runner",
                    status=event.get("status") or code_runner_result.status,
                    message=event.get("message") or "Skill Code Runner executed",
                    payload=event.get("payload") or {},
                )
            if not answer:
                answer = f"已激活 {skill_name} Skill，但通用 Skill Code Runner 没有返回结果。"
        elif (artifact_result := run_artifact_skill_pipelines(
            user_id=user_id,
            user_text=payload.text,
            active_skill_names=activated_skill_names,
            bound_skills=bound_skills,
        )).handled:
            answer = artifact_result.answer
            direct_skill_artifact_paths.extend(artifact_result.saved_files)
            used_skills = artifact_result.used_skills
            for event in artifact_result.runtime_events:
                store.append_runtime_run_event(
                    db=db,
                    run_id=run.id,
                    stage=event.get("stage") or "skill_artifact",
                    status=event.get("status") or "unknown",
                    message=event.get("message") or "Artifact Skill Runtime executed",
                    payload=event.get("payload") or {},
                )
        elif run_mode == "code":
            started = perf_counter()
            preview = payload.text[:200]
            store.append_runtime_run_event(
                db=db,
                run_id=run.id,
                stage="code_execution",
                status="running",
                message="Code execution started",
                payload={"input_preview": preview},
            )
            code_result = code_runtime_executor.run(
                payload.text,
                custom_code=custom_code,
                context={
                    "project_id": session.project_id,
                    "session_id": session.id,
                    "user_id": user_id,
                    "agent_id": payload.agent_id,
                    "config": agent_config,
                },
                tools=tools,
                mcps=mcps,
            )
            code_text, used_tools, used_mcps, use_llm = _decode_code_result(code_result)

            if use_llm:
                if provider_connection or model_provider or model_name:
                    llm_response = llm_service.generate(
                        LLMRequest(
                            text=payload.text,
                            model_provider=model_provider,
                            model_name=model_name,
                            provider_profile=provider_profile,
                            provider_connection_id=provider_connection_id,
                            provider_connection=provider_connection,
                            system_prompt=system_prompt,
                            max_tokens=12000 if design_skill_active else None,
                        )
                    )
                    answer = _llm_answer_or_error(llm_response)
                    store.append_runtime_run_event(
                        db=db,
                        run_id=run.id,
                        stage="llm",
                        status="succeeded" if llm_response.ok else "failed",
                        message="LLM fallback executed from code mode",
                        payload={
                            "provider": llm_response.provider,
                            "model_name": llm_response.model_name,
                            "used_fallback": llm_response.used_fallback,
                            "error": llm_response.error,
                        },
                    )
                else:
                    answer = "[code-fallback-skipped] use_llm requested but model provider/model name is not configured"
            else:
                answer = code_text

            duration_ms = int((perf_counter() - started) * 1000)
            store.append_runtime_run_event(
                db=db,
                run_id=run.id,
                stage="code_execution",
                status="succeeded",
                message="Code execution succeeded",
                payload={
                    "duration_ms": duration_ms,
                    "input_preview": preview,
                    "output_length": len(answer),
                    "used_tools": used_tools,
                    "used_mcps": used_mcps,
                },
            )
        else:
            # ------------------------------------------------------------------
            # NEW: ReAct Engine (Phase 1 - supports any OpenAI-compatible model)
            # ------------------------------------------------------------------
            engine_type = str(agent_config.get("engine_type", "legacy")).strip().lower()
            
            # Auto-enable ReAct engine if MCPs are present
            if not engine_type or engine_type == "legacy":
                mcp_ids_check = agent_config.get("mcp_ids") or []
                if mcp_ids_check and len(mcp_ids_check) > 0:
                    engine_type = "react"
                    logger.info(f"[send_message] Auto-enabling ReAct engine due to presence of MCPs")
            
            logger.info(f"[send_message] engine_type resolved to: '{engine_type}'")
            
            if engine_type == "react":
                logger.info(f"[send_message] ✓ Using ReAct Agent Engine (agent={payload.agent_id})")
                try:
                    # Initialize ReAct Agent
                    llm_wrapper = LangChainLLMWrapper(
                        llm_service=llm_service,
                        model_name=model_name or "gpt-4o-mini",
                        temperature=float(agent_config.get("temperature", 0.2)),
                        provider=model_provider or "openai",
                        provider_profile=provider_profile,
                        provider_connection_id=provider_connection_id,
                        provider_connection=provider_connection,
                    )
                    tool_manager = ToolManager()
                    agent = ReActAgent(
                        llm=llm_wrapper,
                        tool_manager=tool_manager,
                        max_iterations=int(agent_config.get("max_iterations", 10)),
                    )
                    
                    # Prepare context for agent
                    agent_context = {
                        "mcps": {m.get("id"): m for m in mcps},
                        "tools": {t.get("id"): t for t in tools},
                        "skills": {
                            s.get("skill_id"): {
                                **s,
                                "_runtime_context": {
                                    "project_id": session.project_id,
                                    "session_id": session.id,
                                    "agent_id": payload.agent_id,
                                    "user_id": user_id,
                                    "output_base_dir": f"generated/{re.sub('[^A-Za-z0-9_-]+', '_', _skill_display_name(s)).strip('_') or 'skill'}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                                    "timeout_seconds": int((s.get("instance_config") or {}).get("timeout_seconds") or 30),
                                },
                            }
                            for s in bound_skills
                            if s.get("skill_id")
                        },
                        "knowledge_bases": {},  # TODO: Phase 2
                    }

                    agent_config = {
                        **agent_config,
                        "skill_ids": [s.get("skill_id") for s in bound_skills],
                    }
                    
                    # Run agent
                    answer, agent_events = await agent.run(
                        user_input=payload.text,
                        agent_config=agent_config,
                        context=agent_context,
                        system_prompt=system_prompt,
                    )
                    
                    # Record agent events in RuntimeRunEvent
                    for event in agent_events:
                        store.append_runtime_run_event(
                            db=db,
                            run_id=run.id,
                            stage=f"agentic_{event['stage']}",
                            status="succeeded" if event.get("error") is None else "failed",
                            message=f"Agent step: {event['stage']} (iteration {event.get('iteration', 0)})",
                            payload=event,
                        )
                        tool_name = str(event.get("tool_name") or "")
                        if event.get("stage") == "observation" and tool_name == "load_skill":
                            store.append_runtime_run_event(
                                db=db,
                                run_id=run.id,
                                stage="skill",
                                status="loaded",
                                message="Skill loaded via load_skill tool",
                                payload={"tool": tool_name, "result_preview": str(event.get("tool_result") or "")[:2000]},
                            )
                        if event.get("stage") == "observation" and tool_name.startswith("skill_"):
                            result_payload = event.get("tool_result")
                            try:
                                result_payload = json.loads(str(result_payload))
                            except Exception:
                                result_payload = {"raw": str(result_payload)}
                            store.append_runtime_run_event(
                                db=db,
                                run_id=run.id,
                                stage="skill_runtime",
                                status=(result_payload.get("status") if isinstance(result_payload, dict) else None) or "succeeded",
                                message=f"Skill tool executed: {tool_name}",
                                payload={"tool": tool_name, "result": result_payload},
                            )                    
                    logger.info(f"[send_message] ReAct Agent completed with {len(agent_events)} events")
                    
                except Exception as e:
                    logger.error(f"[send_message] ReAct Agent failed: {str(e)}", exc_info=True)
                    answer = f"[ReAct Agent Error] {str(e)}"
                    store.append_runtime_run_event(
                        db=db,
                        run_id=run.id,
                        stage="agent",
                        status="failed",
                        message="ReAct Agent execution failed",
                        payload={"error": str(e)},
                    )
            else:
                # ------------------------------------------------------------------
                # LEGACY: Original agentic loop (function calling based)
                # ------------------------------------------------------------------
                logger.info(f"[send_message] ✗ Using LEGACY engine (engine_type={engine_type}, agent={payload.agent_id})")
                # Check if model supports function calling.
                # ------------------------------------------------------------------
                supports_fc = _supports_function_calling(model_name or "")
                logger.info(f"[send_message] Model {model_name} supports function calling: {supports_fc}")
                
                if not supports_fc and mcps:
                    # Model doesn't support function calling. Fallback to direct LLM call.
                    logger.info(f"[send_message] Model doesn't support function calling. Calling LLM without tools.")
                    llm_response = llm_service.generate(
                        LLMRequest(
                            text=payload.text,
                            model_provider=model_provider,
                            model_name=model_name,
                            provider_profile=provider_profile,
                            provider_connection_id=provider_connection_id,
                            provider_connection=provider_connection,
                            system_prompt=system_prompt,
                            messages=None,  # Use simple single-turn
                            tools=None,  # Don't send tools
                        )
                    )
                    answer = _llm_answer_or_error(llm_response)
                    store.append_runtime_run_event(
                        db=db,
                        run_id=run.id,
                        stage="llm",
                        status="succeeded" if llm_response.ok else "failed",
                        message="LLM generation completed (model doesn't support function calling)",
                        payload={
                            "provider": llm_response.provider,
                            "model_name": llm_response.model_name,
                            "note": f"MCPs available but not used: {[m.get('name') for m in mcps]}",
                        },
                    )
                else:
                    # ------------------------------------------------------------------
                    # Fetch tool definitions from associated MCPs (best-effort).
                    # ------------------------------------------------------------------
                    openai_tools: list[dict] = []
                    # Maps OpenAI tool name → (mcp_spec, original_tool_name)
                    tool_to_mcp: dict[str, tuple[dict, str]] = {}
                    mcp_names_for_prompt: list[str] = []
                    skill_loader_available = bool(bound_skills)
                    if skill_loader_available:
                        openai_tools.append({
                            "type": "function",
                            "function": {
                                "name": "load_skill",
                                "description": "Load the full SKILL.md instructions and attached script list for one bound Agent Skill by name. Use before following a Skill workflow.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "skill_name": {
                                            "type": "string",
                                            "description": "The exact Agent Skill name or alias, for example xlsx or front-design.",
                                        }
                                    },
                                    "required": ["skill_name"],
                                },
                            },
                        })

                    for mcp_spec in mcps:
                        mcp_name = str(mcp_spec.get("name") or "")
                        try:
                            mcp_c = get_mcp_client(mcp_spec)
                            tools_list = mcp_c.list_tools()
                            logger.info(f"[send_message] MCP {mcp_name} has {len(tools_list)} tools")
                            if tools_list:
                                mcp_names_for_prompt.append(mcp_name)
                            for tool in tools_list:
                                openai_def = mcp_tool_to_openai(mcp_name, tool)
                                fn_name = openai_def["function"]["name"]
                                openai_tools.append(openai_def)
                                tool_to_mcp[fn_name] = (mcp_spec, str(tool.get("name") or ""))
                        except Exception as exc:
                            # Log but don't fail; other MCPs may still work
                            logger.warning(f"[send_message] Failed to load MCP {mcp_name}: {exc}")

                    # ------------------------------------------------------------------
                    # Augment system prompt with available tools info.
                    # ------------------------------------------------------------------
                    final_system_prompt = system_prompt or "You are a helpful assistant."
                    prompt_additions: list[str] = []
                    if mcp_names_for_prompt:
                        tools_list_text = ", ".join(mcp_names_for_prompt)
                        prompt_additions.append(f"You have access to the following MCP tools/services: {tools_list_text}. When appropriate, use these tools to answer user questions and get real-time information.")
                    if skill_loader_available:
                        prompt_additions.append(
                            "Available Agent Skills (catalog only):\n"
                            + build_skill_catalog_text(bound_skills)
                            + "\nUse the load_skill tool to load full SKILL.md instructions before following a Skill workflow."
                        )
                    augmented_prompt = final_system_prompt
                    if prompt_additions:
                        augmented_prompt = f"{final_system_prompt}\n\n" + "\n\n".join(prompt_additions)
                    # ------------------------------------------------------------------
                    # Build initial conversation messages.
                    # ------------------------------------------------------------------
                    conv_messages: list[dict] = []
                    conv_messages.append({"role": "system", "content": augmented_prompt})
                    conv_messages.append({"role": "user", "content": payload.text})

                    # ------------------------------------------------------------------
                    # Agentic loop: call LLM → execute tool calls → repeat.
                    # ------------------------------------------------------------------
                    _MAX_TOOL_ITERATIONS = 10
                    answer = ""
                    llm_response = None
                    
                    logger.info(f"[send_message] Starting agentic loop with {len(openai_tools)} tools, prompt includes: {mcp_names_for_prompt}")

                    for _iter in range(_MAX_TOOL_ITERATIONS):
                        logger.debug(f"[send_message] Agentic iteration {_iter + 1}")
                        llm_response = llm_service.generate(
                            LLMRequest(
                                text=payload.text,
                                model_provider=model_provider,
                                model_name=model_name,
                                provider_profile=provider_profile,
                                provider_connection_id=provider_connection_id,
                                provider_connection=provider_connection,
                                system_prompt=system_prompt,
                                messages=conv_messages,
                                tools=openai_tools if openai_tools else None,
                                max_tokens=12000 if design_skill_active else None,
                            )
                        )
                        
                        if llm_response.tool_calls:
                            logger.info(f"[send_message] LLM requested {len(llm_response.tool_calls)} tool calls")
                            conv_messages.append({
                                "role": "assistant",
                                "content": llm_response.text or None,
                                "tool_calls": [
                                    {
                                        "id": tc["id"],
                                        "type": "function",
                                        "function": {
                                            "name": tc["name"],
                                            "arguments": json.dumps(tc["arguments"]),
                                    },
                                }
                                for tc in llm_response.tool_calls
                            ],
                            })

                            # Execute each requested tool call.
                            for tc in llm_response.tool_calls:
                                fn_name = tc["name"]
                                fn_args = tc["arguments"]
                                logger.debug(f"[send_message] Executing tool: {fn_name}")
                                if fn_name == "load_skill":
                                    requested_skill = str(fn_args.get("skill_name") or fn_args.get("name") or "")
                                    loaded_skill = find_skill(bound_skills, requested_skill)
                                    if loaded_skill:
                                        loaded_skill_name = _skill_display_name(loaded_skill)
                                        result_text = render_loaded_skill(loaded_skill)
                                        if loaded_skill_name not in used_skills:
                                            used_skills.append(loaded_skill_name)
                                        store.append_runtime_run_event(
                                            db=db,
                                            run_id=run.id,
                                            stage="skill",
                                            status="loaded",
                                            message=f"Skill loaded via load_skill: {loaded_skill_name}",
                                            payload={"skill": loaded_skill_name, "requested": requested_skill},
                                        )
                                    else:
                                        available = ", ".join(_skill_display_name(item) for item in bound_skills)
                                        result_text = f"Skill not found: {requested_skill}. Available Skills: {available or '-'}"
                                        store.append_runtime_run_event(
                                            db=db,
                                            run_id=run.id,
                                            stage="skill",
                                            status="failed",
                                            message="load_skill requested unknown Skill",
                                            payload={"requested": requested_skill, "available": available},
                                        )
                                elif fn_name in tool_to_mcp:
                                    mcp_spec, orig_tool = tool_to_mcp[fn_name]
                                    mcp_res_name = str(mcp_spec.get("name") or "")
                                    try:
                                        raw = get_mcp_client(mcp_spec).call_tool(orig_tool, fn_args)
                                        result_text = extract_tool_result_text(raw)
                                        used_mcps.append({"mcp": mcp_res_name, "tool": orig_tool})
                                        logger.info(f"[send_message] Tool call succeeded: {mcp_res_name}/{orig_tool}")
                                        store.append_runtime_run_event(
                                            db=db, run_id=run.id, stage="mcp", status="succeeded",
                                            message=f"MCP tool called: {mcp_res_name}/{orig_tool}",
                                            payload={"mcp": mcp_res_name, "tool": orig_tool},
                                        )
                                    except Exception as exc:
                                        result_text = f"[error calling {fn_name}: {exc}]"
                                        logger.error(f"[send_message] Tool call failed: {fn_name}, error: {exc}")
                                        store.append_runtime_run_event(
                                            db=db, run_id=run.id, stage="mcp", status="failed",
                                            message=f"MCP tool failed: {fn_name}",
                                            payload={"error": str(exc)},
                                        )
                                else:
                                    result_text = f"[unknown tool: {fn_name}]"
                                    logger.warning(f"[send_message] Unknown tool: {fn_name}")

                                conv_messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": result_text,
                                })
                        else:
                            answer = _llm_answer_or_error(llm_response)
                            logger.info(f"[send_message] LLM returned final answer (iteration {_iter + 1})")
                            break
                    else:
                        answer = _llm_answer_or_error(llm_response) if llm_response else "[max tool iterations reached]"

                    store.append_runtime_run_event(
                        db=db,
                        run_id=run.id,
                        stage="llm",
                        status="succeeded" if (llm_response and llm_response.ok) else "failed",
                        message="LLM generation completed",
                        payload={
                            "provider": llm_response.provider if llm_response else "",
                            "model_name": llm_response.model_name if llm_response else "",
                            "used_fallback": llm_response.used_fallback if llm_response else False,
                            "error": llm_response.error if llm_response else None,
                            "tool_iterations": _iter + 1,
                        "mcp_calls": len(used_mcps),
                    },
                )
        generated_files = _extract_generated_files_payload(answer)
        saved_file_paths: list[str] = list(direct_skill_artifact_paths)

        if design_skill_active and not answer.startswith("[runtime-fallback:"):
            for continuation_index in range(3):
                if not _looks_truncated_design_output(answer):
                    break

                continuation_prompt = (
                    "Continue the previous HTML document from the exact point it stopped. "
                    "Do not repeat earlier content. Finish open CSS, body content, scripts, and close all tags. "
                    "Output only the continuation text, with no markdown fences or commentary.\n\n"
                    f"Previous output:\n{answer}\n\nContinuation:"
                )
                continuation = llm_service.generate(
                    LLMRequest(
                        text=continuation_prompt,
                        model_provider=model_provider,
                        model_name=model_name,
                        provider_profile=provider_profile,
                        provider_connection_id=provider_connection_id,
                        provider_connection=provider_connection,
                        system_prompt=system_prompt,
                        max_tokens=2000,
                    )
                )
                if not continuation.ok or not continuation.text:
                    break

                answer = f"{answer}{continuation.text.lstrip()}"
                store.append_runtime_run_event(
                    db=db,
                    run_id=run.id,
                    stage="llm_continuation",
                    status="succeeded",
                    message=f"Continued truncated design output (pass {continuation_index + 1})",
                    payload={"continuation_length": len(continuation.text)},
                )

            if _looks_truncated_design_output(answer):
                repaired_answer = _repair_truncated_design_output(answer)
                if repaired_answer != answer:
                    answer = repaired_answer
                    store.append_runtime_run_event(
                        db=db,
                        run_id=run.id,
                        stage="llm_repair",
                        status="succeeded",
                        message="Repaired truncated design output",
                        payload={"repaired_length": len(answer)},
                    )

        if not used_skills and activated_skill_names:
            used_skills = activated_skill_names
        if not used_skills and mentioned_skills:
            used_skills = mentioned_skills

        if used_skills and not is_skill_inventory_query:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            safe_skill_name = re.sub(r"[^\w\-]+", "_", used_skills[0]) if used_skills else "skill"
            artifact_base_dir = f"generated/{safe_skill_name}_{timestamp}"
            try:
                runtime_saved_files = [
                    path
                    for result in executable_skill_results
                    for path in (result.get("saved_files") or [])
                ]
                runtime_completed = [
                    result.get("skill")
                    for result in executable_skill_results
                    if result.get("status") == "completed"
                ]
                if saved_file_paths:
                    pass
                elif runtime_saved_files:
                    saved_file_paths.extend(runtime_saved_files)
                    answer = (
                        f"已使用 {', '.join(str(item) for item in runtime_completed if item)} Skill 执行脚本并生成文件。\n\n"
                        "文件已保存到 My Files：\n"
                        + "\n".join(f"- {path}" for path in saved_file_paths)
                        + "\n\n请到 My Files 中下载。"
                    )
                elif design_skill_active:
                    html = _extract_html_artifact(answer)
                    if not html or "<body" not in html.lower():
                        retry_prompt = (
                            "The previous front-design response was not a complete savable HTML artifact. "
                            "Regenerate from scratch and follow the activated frontend-design Skill instructions strictly.\n\n"
                            + _build_design_skill_brief(payload.text, bound_skills)
                            + "\n\nPrevious response is diagnostic context only; do not continue it or copy generic fallback content.\n"
                            + f"Previous response preview:\n{answer[:2500]}"
                        )
                        retry_response = llm_service.generate(
                            LLMRequest(
                                text=retry_prompt,
                                model_provider=model_provider,
                                model_name=model_name,
                                provider_profile=provider_profile,
                                provider_connection_id=provider_connection_id,
                                provider_connection=provider_connection,
                                system_prompt=system_prompt,
                                max_tokens=12000,
                            )
                        )
                        retry_html = _extract_html_artifact(retry_response.text if retry_response and retry_response.ok else "")
                        if retry_html and "<body" in retry_html.lower():
                            html = retry_html
                            store.append_runtime_run_event(
                                db=db,
                                run_id=run.id,
                                stage="llm_repair",
                                status="succeeded",
                                message="Recovered complete front-design HTML on retry",
                                payload={"html_length": len(html)},
                            )

                    if not html or "<body" not in html.lower():
                        html = _build_front_design_fallback_html(payload.text)
                        store.append_runtime_run_event(
                            db=db,
                            run_id=run.id,
                            stage="skill_artifact",
                            status="fallback",
                            message="Generated local fallback HTML because front-design model output was not savable",
                            payload={"original_answer_length": len(answer or ""), "html_length": len(html)},
                        )

                    html_path = f"{artifact_base_dir}/homepage.html"
                    user_file_service.save_text_file(user_id, html_path, html)
                    saved_file_paths.append(html_path)
                    answer = (
                        "已使用 front-design Skill 生成网站首页文件。\n\n"
                        "文件已保存到 My Files：\n"
                        f"- {html_path}\n\n"
                        "请到 My Files 中下载或预览该 HTML 文件。"
                    )
                else:
                    artifact_result = run_artifact_skill_pipelines(
                        user_id=user_id,
                        user_text=payload.text,
                        active_skill_names=used_skills,
                        bound_skills=bound_skills,
                    )
                    if artifact_result.handled:
                        saved_file_paths.extend(artifact_result.saved_files)
                        answer = artifact_result.answer
                        for event in artifact_result.runtime_events:
                            store.append_runtime_run_event(
                                db=db,
                                run_id=run.id,
                                stage=event.get("stage") or "skill_artifact",
                                status=event.get("status") or "unknown",
                                message=event.get("message") or "Artifact Skill Runtime executed",
                                payload=event.get("payload") or {},
                            )
                    elif generated_files:
                        saved_file_paths.extend(
                            user_file_service.save_generated_files(
                                user_id=user_id,
                                base_dir=artifact_base_dir,
                                generated_files=generated_files,
                            )
                        )
                        answer = (
                            f"已使用 {', '.join(used_skills)} Skill 生成文件。\n\n"
                            "文件已保存到 My Files：\n"
                            + "\n".join(f"- {path}" for path in saved_file_paths)
                            + "\n\n请到 My Files 中下载。"
                        )
                    else:
                        summary_path = f"chat_outputs/{safe_skill_name}_{timestamp}.md"
                        user_file_service.save_text_file(user_id, summary_path, answer)
                        saved_file_paths.append(summary_path)

                if saved_file_paths:
                    store.append_runtime_run_event(
                        db=db,
                        run_id=run.id,
                        stage="file_library",
                        status="succeeded",
                        message="Saved Skill artifacts to user file library",
                        payload={"files": saved_file_paths},
                    )
            except Exception as file_exc:
                store.append_runtime_run_event(
                    db=db,
                    run_id=run.id,
                    stage="file_library",
                    status="failed",
                    message="Failed to persist file library artifacts",
                    payload={"error": str(file_exc)},
                )

        artifact_saved = bool(saved_file_paths) and (bool(used_skills) or bool(generated_files))
        if used_skills and not is_skill_inventory_query and not artifact_saved and "使用的 Skill:" not in answer:
            print(f"[send_message] Adding used_skills to answer: {used_skills}")
            answer = f"{answer}\n\n使用的 Skill: {', '.join(used_skills)}"
        else:
            print(f"[send_message] NOT adding used_skills (used_skills={used_skills}, is_inventory={is_skill_inventory_query}, artifact_saved={artifact_saved}, has_already={'使用的 Skill:' in answer})")
        store.append_chat_message(db, session_id, role="assistant", text=answer, agent_id=payload.agent_id)
        store.finish_runtime_run(
            db=db,
            run_id=run.id,
            status="succeeded",
            output_text=answer,
            error=None,
        )
        store.append_runtime_run_event(
            db=db,
            run_id=run.id,
            stage="runtime",
            status="succeeded",
            message="Runtime execution completed",
            payload={"output_length": len(answer)},
        )
        print(f"[send_message] Returning assistant response: chars={len(answer)}, used_skills={used_skills}", flush=True)
        logger.info(f"[send_message] Returning assistant response: chars={len(answer)}, used_skills={used_skills}")
        return ChatMessageResponse(
            session_id=session_id,
            role="assistant",
            agent_id=payload.agent_id,
            agent_name=agent_name,
            text=answer,
            run_id=run.id,
            used_tools=used_tools,
            used_mcps=used_mcps,
            used_knowledge_bases=used_knowledge_bases,
            used_skills=used_skills,
        )
    except Exception as exc:
        error_text = str(exc)
        if run_mode == "code":
            store.append_runtime_run_event(
                db=db,
                run_id=run.id,
                stage="code_execution",
                status="failed",
                message="Code execution failed",
                payload={
                    "error": error_text,
                    "input_preview": payload.text[:200],
                },
            )
        store.finish_runtime_run(
            db=db,
            run_id=run.id,
            status="failed",
            output_text=None,
            error=error_text,
        )
        store.append_runtime_run_event(
            db=db,
            run_id=run.id,
            stage="runtime",
            status="failed",
            message="Runtime execution failed",
            payload={"error": error_text},
        )
        raise

