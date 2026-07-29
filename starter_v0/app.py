from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import (
    ARTIFACTS_DIR,
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
TRANSCRIPTS_DIR = ROOT / "transcripts"
RUNS_DIR = ROOT / "runs"

PROVIDERS = ["groq", "gemini", "openrouter", "openai", "anthropic"]
PROVIDER_LABELS = {
    "groq": "Groq",
    "gemini": "Gemini",
    "openrouter": "OpenRouter",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
}


# -----------------------------------------------------------------------------
# App configuration + visual system
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Lumi Research",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --pink-50: #fff7fb;
            --pink-100: #ffe8f3;
            --pink-200: #ffcfe3;
            --pink-300: #f9a8cc;
            --pink-400: #f472b6;
            --pink-500: #ec4899;
            --pink-600: #db2777;
            --pink-700: #be185d;
            --rose-900: #4a1533;
            --ink: #2d1b27;
            --muted: #806575;
            --panel: rgba(255, 255, 255, 0.78);
            --panel-strong: rgba(255, 255, 255, 0.94);
            --border: rgba(236, 72, 153, 0.16);
            --shadow: 0 18px 50px rgba(190, 24, 93, 0.09);
        }

        .stApp {
            background:
                radial-gradient(circle at 8% 4%, rgba(244, 114, 182, 0.13), transparent 28rem),
                radial-gradient(circle at 92% 9%, rgba(216, 180, 254, 0.16), transparent 30rem),
                linear-gradient(180deg, #fffafd 0%, #fff7fb 48%, #fff 100%);
            color: var(--ink);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stToolbar"] {
            right: 0.8rem;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(255,255,255,.94), rgba(255,247,251,.96));
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.1rem;
        }

        .block-container {
            max-width: 1120px;
            padding-top: 1.25rem;
            padding-bottom: 7.5rem;
        }

        .lumi-brand {
            display: flex;
            align-items: center;
            gap: .8rem;
            margin: .15rem 0 1.35rem;
        }

        .lumi-logo {
            width: 42px;
            height: 42px;
            display: grid;
            place-items: center;
            border-radius: 15px;
            background: linear-gradient(135deg, #f472b6, #db2777 58%, #a855f7);
            box-shadow: 0 10px 25px rgba(219, 39, 119, .22);
            color: white;
            font-size: 1.25rem;
            font-weight: 800;
        }

        .lumi-brand-title {
            font-weight: 760;
            letter-spacing: -.025em;
            font-size: 1.08rem;
            color: #3a2031;
            line-height: 1.1;
        }

        .lumi-brand-subtitle {
            color: var(--muted);
            font-size: .77rem;
            margin-top: .22rem;
        }

        .hero {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(236, 72, 153, .14);
            border-radius: 28px;
            padding: 1.65rem 1.8rem;
            margin-bottom: 1rem;
            background:
                linear-gradient(125deg, rgba(255,255,255,.96), rgba(255,240,247,.88)),
                radial-gradient(circle at 90% 10%, rgba(168,85,247,.14), transparent 18rem);
            box-shadow: var(--shadow);
        }

        .hero::after {
            content: "✦";
            position: absolute;
            right: 2rem;
            top: .75rem;
            font-size: 5.4rem;
            color: rgba(219, 39, 119, .075);
            transform: rotate(12deg);
        }

        .hero-kicker {
            color: var(--pink-600);
            font-size: .78rem;
            font-weight: 760;
            letter-spacing: .1em;
            text-transform: uppercase;
            margin-bottom: .45rem;
        }

        .hero h1 {
            color: #351b2b;
            font-size: clamp(1.75rem, 4vw, 2.75rem);
            line-height: 1.04;
            letter-spacing: -.05em;
            margin: 0;
            max-width: 780px;
        }

        .hero p {
            color: var(--muted);
            margin: .8rem 0 0;
            max-width: 680px;
            line-height: 1.62;
        }

        .meta-strip {
            display: flex;
            flex-wrap: wrap;
            gap: .5rem;
            margin: .9rem 0 1.35rem;
        }

        .meta-pill {
            display: inline-flex;
            align-items: center;
            gap: .38rem;
            padding: .42rem .72rem;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: rgba(255,255,255,.76);
            color: #664457;
            font-size: .77rem;
            box-shadow: 0 4px 16px rgba(190,24,93,.04);
        }

        .meta-dot {
            width: 7px;
            height: 7px;
            border-radius: 999px;
            background: #22c55e;
            box-shadow: 0 0 0 4px rgba(34,197,94,.1);
        }

        [data-testid="stChatMessage"] {
            border: 0;
            background: transparent;
            padding: .35rem 0;
            gap: .75rem;
        }

        [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
            border-radius: 22px;
            border: 1px solid rgba(236, 72, 153, .12);
            background: rgba(255,255,255,.86);
            box-shadow: 0 8px 30px rgba(83, 33, 60, .055);
            padding: .9rem 1.05rem;
            line-height: 1.67;
        }

        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
        [data-testid="stChatMessageContent"] {
            background: linear-gradient(135deg, #ec4899, #db2777);
            color: #fff;
            border-color: transparent;
            box-shadow: 0 12px 30px rgba(219, 39, 119, .18);
        }

        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
        [data-testid="stChatMessageContent"] p,
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"])
        [data-testid="stChatMessageContent"] li {
            color: #fff;
        }

        [data-testid="chatAvatarIcon-user"],
        [data-testid="chatAvatarIcon-assistant"] {
            border-radius: 14px;
        }

        [data-testid="stChatInput"] {
            background: rgba(255, 255, 255, .9);
            border: 1px solid rgba(236,72,153,.22);
            border-radius: 24px;
            box-shadow: 0 18px 45px rgba(190, 24, 93, .12);
            backdrop-filter: blur(18px);
        }

        [data-testid="stChatInput"] textarea {
            font-size: .98rem;
        }

        [data-testid="stChatInputSubmitButton"] {
            border-radius: 14px;
            background: linear-gradient(135deg, #ec4899, #db2777);
            color: white;
        }

        .empty-state {
            margin: 1.35rem auto 1.6rem;
            padding: 1.6rem;
            max-width: 760px;
            text-align: center;
            border: 1px dashed rgba(236,72,153,.22);
            border-radius: 24px;
            background: rgba(255,255,255,.58);
        }

        .empty-orb {
            width: 58px;
            height: 58px;
            border-radius: 20px;
            display: grid;
            place-items: center;
            margin: 0 auto .85rem;
            color: white;
            font-size: 1.55rem;
            background: linear-gradient(135deg, #f9a8d4, #ec4899 55%, #a855f7);
            box-shadow: 0 14px 35px rgba(219,39,119,.2);
        }

        .empty-state h3 {
            margin: 0;
            color: #46263a;
            letter-spacing: -.02em;
        }

        .empty-state p {
            color: var(--muted);
            margin: .55rem auto 0;
            max-width: 560px;
            line-height: 1.55;
        }

        .trace-title {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: .75rem;
            padding: .2rem 0 .4rem;
        }

        .trace-name {
            font-weight: 720;
            color: #49293b;
        }

        .trace-status-ok,
        .trace-status-error {
            border-radius: 999px;
            padding: .2rem .5rem;
            font-size: .68rem;
            font-weight: 750;
            text-transform: uppercase;
            letter-spacing: .055em;
        }

        .trace-status-ok {
            color: #16743d;
            background: #e9f9ef;
        }

        .trace-status-error {
            color: #b42318;
            background: #fff0ee;
        }

        div[data-testid="stExpander"] {
            border: 1px solid rgba(236,72,153,.14);
            border-radius: 16px;
            background: rgba(255,255,255,.66);
            overflow: hidden;
        }

        div[data-testid="stMetric"] {
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: .7rem .85rem;
            background: var(--panel);
            box-shadow: 0 8px 24px rgba(190,24,93,.05);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 18px;
            overflow: hidden;
            box-shadow: 0 10px 32px rgba(190,24,93,.055);
        }

        .section-title {
            color: #3d2232;
            margin: 0;
            font-size: 1.75rem;
            letter-spacing: -.035em;
        }

        .section-copy {
            color: var(--muted);
            margin: .35rem 0 1.15rem;
        }

        .sidebar-section {
            color: #95647f;
            font-size: .69rem;
            font-weight: 780;
            letter-spacing: .12em;
            text-transform: uppercase;
            margin: 1.2rem 0 .45rem;
        }

        .sidebar-note {
            padding: .75rem .82rem;
            border-radius: 16px;
            color: #755268;
            background: rgba(255,232,243,.66);
            border: 1px solid rgba(236,72,153,.12);
            font-size: .76rem;
            line-height: 1.45;
            margin-top: .8rem;
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #ec4899, #db2777);
            border: none;
            box-shadow: 0 8px 22px rgba(219,39,119,.18);
        }

        .stButton > button {
            border-radius: 14px;
        }

        code {
            border-radius: 8px;
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: .85rem;
                padding-right: .85rem;
            }
            .hero {
                border-radius: 22px;
                padding: 1.25rem;
            }
            .hero::after {
                display: none;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Domain helpers
# -----------------------------------------------------------------------------
def ensure_directories() -> None:
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def new_transcript(
    provider_name: str,
    version: str,
    model: str | None,
) -> tuple[Path, dict[str, Any]]:
    prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    artifact = build_artifact_version(version, prompt_path, tools_path)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = f"{safe_slug(version)}_{safe_slug(provider_name)}_ui_{stamp}"
    path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    data = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact),
        "provider": provider_name,
        "model": model,
        "system_prompt": str(prompt_path),
        "tools": str(tools_path),
        "history_window": 5,
        "max_tool_rounds": 4,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "source": "streamlit_ui",
        "turns": [],
    }
    return path, data


def reset_session() -> None:
    for key in [
        "history",
        "turns",
        "transcript",
        "transcript_path",
        "session_config",
    ]:
        st.session_state.pop(key, None)


def initialize_session(
    provider_name: str,
    version: str,
    model: str | None,
) -> None:
    config = (provider_name, version, model)
    if st.session_state.get("session_config") == config:
        return

    path, transcript = new_transcript(provider_name, version, model)
    st.session_state.update(
        session_config=config,
        history=[],
        turns=[],
        transcript=transcript,
        transcript_path=path,
    )


def assistant_avatar() -> str:
    return "✨"


def render_brand() -> None:
    st.markdown(
        """
        <div class="lumi-brand">
            <div class="lumi-logo">✦</div>
            <div>
                <div class="lumi-brand-title">Lumi Research</div>
                <div class="lumi-brand-subtitle">Agent workspace</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[str, str, str | None, int, str]:
    with st.sidebar:
        render_brand()

        page = st.radio(
            "Điều hướng",
            ["Chat", "Eval evidence"],
            format_func=lambda value: "✦  Chat" if value == "Chat" else "◫  Eval evidence",
            label_visibility="collapsed",
        )

        st.markdown('<div class="sidebar-section">Model configuration</div>', unsafe_allow_html=True)
        provider_name = st.selectbox(
            "Provider",
            PROVIDERS,
            format_func=lambda value: PROVIDER_LABELS[value],
        )
        model = st.text_input(
            "Model override",
            value="",
            placeholder="Dùng model mặc định",
        )

        st.markdown('<div class="sidebar-section">Agent settings</div>', unsafe_allow_html=True)
        version = st.text_input("Artifact label", value="v3")
        max_rounds = st.slider("Max tool rounds", 1, 6, 4)

        if st.button("＋ New conversation", type="primary", width="stretch"):
            reset_session()
            st.rerun()

        st.markdown(
            """
            <div class="sidebar-note">
                Mỗi cuộc trò chuyện được gắn artifact version và lưu transcript JSON để audit hoặc chạy eval.
            </div>
            """,
            unsafe_allow_html=True,
        )

    return provider_name, version, model or None, max_rounds, page


def render_trace(turn: dict[str, Any]) -> None:
    rounds = turn.get("rounds") or []
    if not rounds:
        return

    total_calls = sum(len(item.get("tool_calls") or []) for item in rounds)
    with st.expander(f"◈ Tool activity · {total_calls} call(s)", expanded=False):
        for round_item in rounds:
            calls = round_item.get("tool_calls") or []
            results = round_item.get("tool_results") or []
            st.caption(f"Round {round_item.get('round')} · {len(calls)} tool call(s)")

            for index, call in enumerate(calls):
                result = results[index].get("result") if index < len(results) else None
                error = result.get("error") if isinstance(result, dict) else None
                status_class = "trace-status-error" if error else "trace-status-ok"
                status_label = "error" if error else "success"
                tool_name = html.escape(str(call.get("name") or "unknown_tool"))

                st.markdown(
                    f"""
                    <div class="trace-title">
                        <span class="trace-name">{tool_name}</span>
                        <span class="{status_class}">{status_label}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                left, right = st.columns(2)
                with left:
                    st.caption("Arguments")
                    st.json(call.get("args") or {}, expanded=False)
                with right:
                    st.caption("Result")
                    st.json(result, expanded=False)


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-orb">✦</div>
            <h3>Xin chào, mình là Lumi</h3>
            <p>
                Đặt câu hỏi nghiên cứu, yêu cầu phân tích hoặc giao cho agent sử dụng tool.
                Mọi vòng gọi tool đều được lưu lại để bạn kiểm tra.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    prompts = [
        "Tổng hợp một chủ đề",
        "So sánh các phương án",
        "Phân tích bằng tool",
    ]
    cols = st.columns(3)
    for col, suggestion in zip(cols, prompts):
        with col:
            st.button(suggestion, width="stretch", disabled=True)


def render_chat_header(provider_name: str, model: str | None) -> None:
    transcript = st.session_state.transcript
    artifact = transcript["artifact_version"]
    model_label = model or "default model"

    st.markdown(
        """
        <section class="hero">
            <div class="hero-kicker">AI research workspace</div>
            <h1>Khám phá ý tưởng.<br/>Kiểm chứng bằng công cụ.</h1>
            <p>
                Trò chuyện trực tiếp với research agent, theo dõi tool calls và lưu lại transcript có version cho từng phiên làm việc.
            </p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="meta-strip">
            <span class="meta-pill"><span class="meta-dot"></span> Agent ready</span>
            <span class="meta-pill">Provider · {html.escape(PROVIDER_LABELS[provider_name])}</span>
            <span class="meta-pill">Model · {html.escape(model_label)}</span>
            <span class="meta-pill">Artifact · {html.escape(str(artifact))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_conversation() -> None:
    turns = st.session_state.turns
    if not turns:
        render_empty_state()
        return

    for turn in turns:
        with st.chat_message("user", avatar="👤"):
            st.markdown(turn["user"])

        with st.chat_message("assistant", avatar=assistant_avatar()):
            if turn.get("assistant_text"):
                st.markdown(turn["assistant_text"])
            elif turn.get("error"):
                st.error(turn["error"])
            render_trace(turn)


def execute_chat_turn(
    prompt: str,
    provider_name: str,
    model: str | None,
    max_rounds: int,
) -> None:
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    system_prompt = (ARTIFACTS_DIR / "system_prompt.md").read_text(encoding="utf-8")
    declarations = load_tool_declarations(ARTIFACTS_DIR / "tools.yaml")
    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history, 5),
        {"role": "user", "content": prompt},
    ]

    turn: dict[str, Any] = {
        "turn_index": len(st.session_state.turns) + 1,
        "started_at": now_iso(),
        "user": prompt,
        "status": "started",
        "rounds": [],
        "tool_events": [],
    }

    with st.chat_message("assistant", avatar=assistant_avatar()):
        status = st.status("Lumi đang suy nghĩ…", expanded=True)
        try:
            status.write("Đang chuẩn bị context và tool declarations")
            result = run_model_tool_loop(
                provider=make_provider(provider_name),
                messages=messages,
                tools=to_openai_tools(declarations),
                model=model,
                max_tool_rounds=max_rounds,
            )

            turn.update(result)
            status.update(label="Hoàn tất", state="complete", expanded=False)
            st.markdown(result["assistant_text"])
            render_trace(turn)

            st.session_state.history.extend(
                [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": result["assistant_text"]},
                ]
            )
        except Exception as exc:
            turn.update(
                status="provider_error",
                error=f"{type(exc).__name__}: {exc}",
            )
            status.update(label="Có lỗi khi gọi provider", state="error", expanded=False)
            st.error(turn["error"])

    turn["ended_at"] = now_iso()
    st.session_state.turns.append(turn)
    st.session_state.transcript["turns"].append(turn)
    st.session_state.transcript["updated_at"] = now_iso()
    write_transcript(
        st.session_state.transcript_path,
        st.session_state.transcript,
    )


def chat_page(
    provider_name: str,
    version: str,
    model: str | None,
    max_rounds: int,
) -> None:
    initialize_session(provider_name, version, model)
    render_chat_header(provider_name, model)
    render_conversation()

    prompt = st.chat_input("Hỏi Lumi bất cứ điều gì…")
    if prompt:
        execute_chat_turn(prompt, provider_name, model, max_rounds)
        st.rerun()


# -----------------------------------------------------------------------------
# Evidence dashboard
# -----------------------------------------------------------------------------
def load_run_payloads() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    payloads: dict[str, Any] = {}

    for path in sorted(RUNS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        payloads[path.name] = data
        summary = data.get("summary") or {}
        rows.append(
            {
                "run": path.name,
                "version": data.get("version"),
                "artifact_version": data.get("artifact_version"),
                "suite": data.get("suite"),
                "case_accuracy": summary.get("case_accuracy"),
                "routing": summary.get("tool_routing_accuracy"),
                "arguments": summary.get("argument_accuracy"),
                "provider_errors": summary.get("provider_error_cases"),
            }
        )

    return rows, payloads


def evidence_page() -> None:
    st.markdown('<h1 class="section-title">Eval evidence</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-copy">Theo dõi chất lượng routing, arguments và lỗi provider theo từng artifact version.</p>',
        unsafe_allow_html=True,
    )

    rows, payloads = load_run_payloads()
    if not rows:
        st.warning("Chưa có run JSON trong thư mục `runs/`.")
        return

    latest = rows[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Case accuracy", latest.get("case_accuracy") or "—")
    col2.metric("Tool routing", latest.get("routing") or "—")
    col3.metric("Arguments", latest.get("arguments") or "—")
    col4.metric("Provider errors", latest.get("provider_errors") or 0)

    st.markdown("### Run history")
    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        column_config={
            "case_accuracy": st.column_config.ProgressColumn(
                "Case accuracy",
                min_value=0.0,
                max_value=1.0,
                format="%.1f%%",
            ),
            "routing": st.column_config.ProgressColumn(
                "Routing",
                min_value=0.0,
                max_value=1.0,
                format="%.1f%%",
            ),
            "arguments": st.column_config.ProgressColumn(
                "Arguments",
                min_value=0.0,
                max_value=1.0,
                format="%.1f%%",
            ),
        },
    )

    selected = st.selectbox("Inspect run", list(payloads))
    with st.expander("Raw JSON payload", expanded=False):
        st.json(payloads[selected], expanded=True)


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
def main() -> None:
    ensure_directories()
    inject_styles()
    provider_name, version, model, max_rounds, page = render_sidebar()

    if page == "Chat":
        chat_page(provider_name, version, model, max_rounds)
    else:
        evidence_page()


if __name__ == "__main__":
    main()
