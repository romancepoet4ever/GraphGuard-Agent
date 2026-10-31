from __future__ import annotations

import streamlit as st


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
          --gg-bg: #f5f7fb;
          --gg-panel: #ffffff;
          --gg-border: #dbe4ef;
          --gg-text: #172033;
          --gg-muted: #5b677a;
          --gg-blue: #2563eb;
          --gg-cyan: #0f766e;
          --gg-red: #dc2626;
          --gg-amber: #b45309;
          --gg-green: #15803d;
        }
        .stApp { background: var(--gg-bg); color: var(--gg-text); }
        .block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1280px; }
        h1, h2, h3 { color: var(--gg-text); letter-spacing: 0; }
        p, li, .stMarkdown { color: var(--gg-text); }
        div[data-testid="stMetric"] {
          background: var(--gg-panel);
          border: 1px solid var(--gg-border);
          border-radius: 8px;
          padding: 12px 14px;
          box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
        }
        div[data-testid="stMetric"] label { color: var(--gg-muted); }
        .gg-hero {
          border: 1px solid #cfe0f5;
          border-radius: 8px;
          padding: 26px 30px;
          background:
            radial-gradient(circle at 20% 15%, rgba(37, 99, 235, 0.12), transparent 28%),
            linear-gradient(135deg, #ffffff 0%, #edf7ff 55%, #f6fbf8 100%);
          box-shadow: 0 16px 40px rgba(15, 23, 42, 0.07);
        }
        .gg-hero h1 { margin: 0 0 8px 0; font-size: 2.45rem; }
        .gg-hero p { margin: 0; color: #334155; font-size: 1.05rem; line-height: 1.7; }
        .gg-card {
          background: var(--gg-panel);
          border: 1px solid var(--gg-border);
          border-radius: 8px;
          padding: 16px 18px;
          box-shadow: 0 8px 24px rgba(15, 23, 42, 0.045);
          min-height: 128px;
        }
        .gg-card h3 { margin-top: 0; font-size: 1.05rem; }
        .gg-card p { color: var(--gg-muted); line-height: 1.65; }
        .gg-section {
          margin-top: 22px;
          margin-bottom: 8px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .gg-section .bar {
          width: 5px;
          height: 22px;
          border-radius: 4px;
          background: linear-gradient(180deg, var(--gg-blue), var(--gg-cyan));
        }
        .gg-section h2 { margin: 0; font-size: 1.35rem; }
        .gg-muted { color: var(--gg-muted); }
        .gg-pill {
          display: inline-block;
          border-radius: 999px;
          padding: 4px 10px;
          font-size: 0.84rem;
          border: 1px solid var(--gg-border);
          background: #f8fafc;
          color: #334155;
          margin-right: 6px;
          margin-bottom: 6px;
        }
        .gg-pill-risk { background: #fef2f2; border-color: #fecaca; color: #991b1b; }
        .gg-pill-ok { background: #f0fdf4; border-color: #bbf7d0; color: #166534; }
        .gg-pill-warn { background: #fffbeb; border-color: #fde68a; color: #92400e; }
        .gg-explain {
          border-left: 4px solid var(--gg-blue);
          background: #eff6ff;
          padding: 12px 14px;
          border-radius: 8px;
          color: #1e3a8a;
          line-height: 1.65;
        }
        .gg-callout {
          background: #ffffff;
          border: 1px solid var(--gg-border);
          border-radius: 8px;
          padding: 14px 16px;
        }
        .stButton > button {
          border-radius: 8px;
          font-weight: 600;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
          border-radius: 8px 8px 0 0;
          padding: 10px 14px;
          background: #eef2f7;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, caption: str | None = None) -> None:
    st.markdown(
        f"""
        <div class="gg-section">
          <div class="bar"></div>
          <div>
            <h2>{title}</h2>
            {f'<div class="gg-muted">{caption}</div>' if caption else ''}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pill(text: str, tone: str = "neutral") -> str:
    cls = {
        "risk": "gg-pill gg-pill-risk",
        "ok": "gg-pill gg-pill-ok",
        "warn": "gg-pill gg-pill-warn",
    }.get(tone, "gg-pill")
    return f"<span class='{cls}'>{text}</span>"
