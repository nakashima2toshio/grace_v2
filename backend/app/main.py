# backend/app/main.py
"""GRACE-Support Web API（FastAPI）。

`agent_support_example.py`（CLI）と同じコアサービス
（backend/app/core/support_agent.py）を Web から呼ぶための API。
ローカル開発専用（認証なし）。フロントエンドは frontend/（Vite + React + TS）。

起動（リポジトリルートで）::

    uvicorn backend.app.main:app --reload --port 8000

前提: `.env` に ANTHROPIC_API_KEY / GOOGLE_API_KEY、Qdrant 起動済み
（docker-compose -f docker-compose/docker-compose.yml up -d）。
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import meta, support

# .env から ANTHROPIC_API_KEY / GOOGLE_API_KEY 等を読み込む（未導入でも続行）
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

app = FastAPI(
    title="GRACE-Support API",
    description="業界特化・自律型サポートエージェント（内部RAG＋Web裏取り＋HITL アクション）",
    version="1.0.0",
)

# ローカル開発: Vite dev サーバ（既定 5173）からのアクセスを許可
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(support.router)
app.include_router(meta.router)
