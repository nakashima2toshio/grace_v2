# backend/app/schemas.py
"""API のリクエスト/レスポンス/イベントの Pydantic スキーマ。

`SupportResult`（backend/app/core/support_agent.py の dataclass）を JSON 化した
ものが `SupportResultModel`。ステップ進捗は SSE（GET /api/support/stream/{job_id}）
で `SupportEventModel` 形式の JSON として逐次配信される。
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from config import get_selectable_models


def _validate_model_choice(v: Optional[str]) -> Optional[str]:
    """`model` フィールドの共通バリデーション（ヘッダーのモデルセレクタ）。

    `config.get_selectable_models()` に無い値は 422 で弾く。未知のモデル名を
    そのまま Anthropic へ投げるとジョブが起動してから 404（`NotFoundError`）で
    落ち、原因が分かりにくい（姉妹リポジトリで Detect 33 回が全滅した実例が
    `backend/app/core/review_gates.py::detect_model` の docstring にある）。
    受付の時点で弾く。

    空文字・None は「サーバーの既定値を使う」の意味なので None へ正規化する。

    ⚠️ Embedding はここに関係しない。Embedding は Gemini
    （`config.py::ModelConfig.EMBEDDING_MODEL`）固定で、選択の対象外（CLAUDE.md §3 プロバイダ方針）。
    """
    if v is None or v == "":
        return None
    return _require_model_choice(v)


def _require_model_choice(v: str) -> str:
    """必須の `model` フィールド用（チャンキング / Q/A 生成）。

    こちらは空文字を許さない。データ準備側の `model` はスキーマ既定値を持つ
    必須フィールドで、フロントは**未選択なら `model` キーごと落として**送る
    （`frontend/src/state/dataParams.ts::modelOverride`）。空文字が届くのは
    送信側のバグなので、既定値へ黙って倒さず 422 にする。
    """
    choices = get_selectable_models()
    if v not in choices:
        raise ValueError(f"未対応のモデルです: {v}（選択可能: {', '.join(choices)}）")
    return v


class QueryRequest(BaseModel):
    """POST /api/support/query（CLI 引数と 1:1 対応）。"""

    query: str = Field(min_length=1, description="問い合わせ内容（チャット入力）")
    vertical: Optional[Literal["gov", "saas", "ec"]] = Field(
        default=None, description="業界プロファイル（--vertical 相当）")
    model: Optional[str] = Field(
        default=None,
        description=(
            "使用する LLM（GET /api/models の選択肢から 1 つ。未指定は既定値 "
            "＝ config/grace_config.yml の llm.model）"
        ),
    )
    dry_run: bool = Field(default=True, description="アクションのドライラン（既定 ON）")
    use_web: bool = Field(default=True, description="Web フォールバック（--no-web 相当の逆）")
    do_action: bool = Field(default=True, description="アクション実行（--no-action 相当の逆）")
    verbose: bool = Field(default=False, description="詳細ログ（-v 相当）")
    identity: Optional[Dict[str, str]] = Field(
        default=None,
        description=(
            "本人確認の識別子（--identity KEY=VALUE 相当。例 {\"order_id\": \"1001\", "
            "\"email\": \"a@example.com\"}）。実際に照合されるのは "
            "require_identity のプロファイル（ec）かつ dry_run=False かつ "
            "SUPPORT_IDENTITY_FILE 設定時のみ"
        ),
    )

    _validate_model = field_validator("model")(_validate_model_choice)


class QueryAccepted(BaseModel):
    """ジョブ受付レスポンス。"""

    job_id: str
    stream_url: str


class ConfirmRequest(BaseModel):
    """POST /api/support/confirm/{job_id}（HITL CONFIRM への応答）。"""

    intervention_id: str
    approve: bool
    selected_option: Optional[str] = Field(
        default=None,
        description=(
            "選択肢つきの介入（0-(A) 入力・質問分析の主質問選択）で選ばれた値。"
            "**省略可**。既存のアクション承認モーダルは選択肢を持たないため "
            "従来どおり intervention_id + approve だけで動く"
        ),
    )


class ConfirmResponse(BaseModel):
    status: Literal["resolved", "not_found", "not_waiting"]


class ActionRequestModel(BaseModel):
    action_type: str
    args: Dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = True


class QuestionClusterModel(BaseModel):
    """1 つの主質問と、それに従属する関連質問のまとまり（複数質問クエリの採用単位）。

    設計: `backend/docs/support_flow.md` §6.9。
    実体は `backend/app/core/support_agent.py::QuestionCluster`。
    """

    main: str
    related: List[str] = Field(default_factory=list)


class SupportResultModel(BaseModel):
    """`SupportResult` の JSON 表現（GET /api/support/result/{job_id}）。"""

    answer: Optional[str] = None
    citations: List[str] = Field(default_factory=list)
    groundedness: float = 0.0
    groundedness_decided: int = 0
    decision: Literal["answer", "escalate"] = "escalate"
    warning: bool = False
    used_web: bool = False
    source_agreement: Optional[float] = None
    contradiction: bool = False
    action: Optional[ActionRequestModel] = None
    action_result: Optional[str] = None
    vertical: Optional[str] = None
    overall_confidence: float = 0.0
    intent: Optional[str] = None
    forced_escalate: bool = False
    identity_checked: bool = False
    no_info_detected: bool = False
    web_reused: bool = False

    # --- 複数質問クエリ（`backend/docs/support_flow.md` §6.4）---------------
    # ⚠️ すべて optional。単一質問では既定値のままで、旧クライアントは壊れない。
    is_multi_question: bool = False
    question_clusters: List[QuestionClusterModel] = Field(default_factory=list)
    adopted_cluster_index: Optional[int] = None
    reconstructed_query: Optional[str] = None
    deferred_questions: List[str] = Field(default_factory=list)
    # 担当範囲外と判定した主質問と、それに添える窓口案内（`deferred` とは別物）。
    out_of_scope_questions: List[str] = Field(default_factory=list)
    out_of_scope_guidance: str = ""


class JobStatusResponse(BaseModel):
    """GET /api/support/result/{job_id}。"""

    job_id: str
    status: Literal["running", "completed", "failed"]
    result: Optional[SupportResultModel] = None

    # --- 実行時刻（サーバ時計・エポック秒）------------------------------------
    # フロントは通常 SSE イベントの ts から開始・完了時刻を組み立てるが、
    # ストリームを購読していない経路（結果だけを引く・リロード直後）でも
    # 所要時間を出せるよう、ジョブ側の実測値をそのまま返す。
    created_at: Optional[float] = None
    finished_at: Optional[float] = None


class SupportEventModel(BaseModel):
    """SSE で配信される進捗イベント（core.SupportEvent ＋ 通し番号/時刻）。"""

    seq: int
    ts: float
    type: Literal["step", "log", "intervention", "result", "error"]
    step: Optional[str] = None
    status: Optional[str] = None
    title: str = ""
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)


class VerticalInfo(BaseModel):
    """GET /api/verticals の 1 要素。"""

    id: str
    name: str
    collections: List[str]
    escalate_keywords: List[str]
    action_map: Dict[str, str]
    require_identity: bool
    notify_th: Optional[float] = None
    confirm_th: Optional[float] = None
    prompt_addendum: str = ""


# =============================================================================
# GRACE-Review（文書レビュー）
#
# 設計: `backend/docs/api_contract.md`。`QueryAccepted` / `ConfirmRequest` /
# `ConfirmResponse` は Support と共用し、結果の型だけ新設する。
# =============================================================================

# 入力段のガード。セグメント数 × ルール数の LLM 呼び出しが発散しないようにする
# （コア側の MAX_SEGMENTS / MAX_LLM_CALLS と二重に効かせる）。超過は 422。
MAX_DOCUMENT_CHARS = 50_000

Severity = Literal["high", "medium", "low"]
FindingStatus = Literal["confirmed", "review_required", "suppressed"]


class ReviewRequest(BaseModel):
    """POST /api/review/submit（CLI 引数と 1:1 対応）。"""

    document: str = Field(
        min_length=1, max_length=MAX_DOCUMENT_CHARS, description="点検対象の文書")
    document_title: str = Field(default="無題", description="表示用タイトル")
    ruleset: Optional[Literal["ec_ad"]] = Field(
        default="ec_ad", description="適用するルールセット")
    model: Optional[str] = Field(
        default=None,
        description=(
            "使用する LLM（GET /api/models の選択肢から 1 つ。未指定は既定値 "
            "＝ config/grace_config.yml の llm.model）"
        ),
    )
    # Support（既定 ON）と違い既定は OFF。文書レビューは条文が一次情報であり、
    # Web 検索は速度・コストに対して得るものが小さい。
    use_web: bool = Field(default=False, description="Web で法改正を裏取り（既定 OFF）")
    do_action: bool = Field(default=True, description="アクション実行（--no-action 相当の逆）")
    dry_run: bool = Field(default=True, description="アクションのドライラン（既定 ON）")
    verbose: bool = Field(default=False, description="詳細ログ（-v 相当）")

    _validate_model = field_validator("model")(_validate_model_choice)


class SegmentModel(BaseModel):
    """検査単位。`start` / `end` は**原文**の文字オフセット（UI のハイライト用）。"""

    segment_id: str
    text: str
    start: int
    end: int
    kind: str = "paragraph"


class ReviewFindingModel(BaseModel):
    """1 件の指摘（UI の指摘カード 1 枚）。"""

    finding_id: str
    segment_id: str
    excerpt: str
    start: int
    end: int

    rule_id: str
    rule_title: str
    category: str
    law: str
    article: str

    message: str
    suggestion: str

    severity: Severity = "medium"
    confidence: float = 0.0
    citations: List[str] = Field(default_factory=list)

    status: FindingStatus = "review_required"
    forced: bool = False
    suppress_reason: Optional[str] = None
    web_checked: bool = False


class FindingSummaryModel(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0
    confirmed: int = 0
    review_required: int = 0
    suppressed: int = 0


class ReviewResultModel(BaseModel):
    """`ReviewResult` の JSON 表現（GET /api/review/result/{job_id}）。"""

    document_title: str
    ruleset: Optional[str] = None
    segments: List[SegmentModel] = Field(default_factory=list)
    findings: List[ReviewFindingModel] = Field(default_factory=list)
    summary: FindingSummaryModel = Field(default_factory=FindingSummaryModel)
    used_web: bool = False
    action: Optional[ActionRequestModel] = None
    action_result: Optional[str] = None
    # --- KPI 計測用メタデータ ---
    segments_total: int = 0
    rules_evaluated: int = 0
    detected_raw: int = 0
    rescued: int = 0
    forced_high: int = 0
    truncated: bool = False


class ReviewJobStatusResponse(BaseModel):
    """GET /api/review/result/{job_id}。"""

    job_id: str
    status: Literal["running", "completed", "failed"]
    result: Optional[ReviewResultModel] = None

    # --- 実行時刻（サーバ時計・エポック秒）------------------------------------
    # フロントは通常 SSE イベントの ts から開始・完了時刻を組み立てるが、
    # ストリームを購読していない経路（結果だけを引く・リロード直後）でも
    # 所要時間を出せるよう、ジョブ側の実測値をそのまま返す。
    created_at: Optional[float] = None
    finished_at: Optional[float] = None


class RuleSetInfo(BaseModel):
    """GET /api/rulesets の 1 要素（`VerticalInfo` と同型の位置づけ）。"""

    id: str
    name: str
    collections: List[str]
    rule_count: int
    always_check_count: int
    laws: List[str]
    critical_keywords: List[str]
    action_map: Dict[str, str]
    notify_th: float
    confirm_th: float
    prompt_addendum: str = ""


class ModelChoice(BaseModel):
    """GET /api/models の 1 要素。ヘッダーのモデルセレクタ用。

    `config.py::get_selectable_models()`（= `ModelConfig.SELECTABLE_MODELS`）で
    絞り込み済みの一覧を返す。旧既定（`claude-sonnet-4-6`）や日付指定エイリアス
    （`claude-haiku-4-5-20251001`）は**選択肢に出さない**。
    """

    id: str
    # $/1K tokens。画面で単価差（haiku < sonnet < opus）を示すために返す
    input_price: float
    output_price: float
    # コンテキスト長 / 1 応答の出力上限（tokens）
    context_window: int
    max_output: int


class ModelInfo(BaseModel):
    """GET /api/model。サーバーが既定として使うモデルの解決結果。

    UI の「（既定値）」表示に実名を出すために使う。ここに出るのは
    `config/grace_config.yml` → 環境変数 → `GraceConfig` を通した**解決後**の値
    なので、画面と実挙動がずれない。
    """

    model: str
    # 判定系（意図分類・情報なし判定・RAG 適合性）に使う軽量モデル。
    light_model: str
    # 論理層（計画生成・推論・根拠検証）の上位モデル。""（空）= model と同じ。
    heavy_model: str = ""
    # データ準備側の既定。**エージェントの既定（`model`）とは別物**で、
    # チャンク化は軽量モデルを使う。データ管理タブの「（既定値: …）」に
    # `model` を出すと、実際に走るモデルと違う名前を表示してしまう。
    chunking_model: str = ""
    qa_model: str = ""
    # 検索・Qdrant 登録に使う Embedding（`config.py::ModelConfig`）。選択の対象外で、
    # データ管理タブの「③ Qdrant 登録」の注記に実名を出すためだけに返す。
    embedding_model: str = ""
    embedding_dims: int = 0


# =============================================================================
# データ準備パイプライン（チャンキング → Q/A 生成 → Qdrant 登録 → コレクション管理）
#
# エージェント 2 種とは別系統の「データを準備する」側の API。
# 実処理は chunking/ qa_generation/ qa_qdrant/ services/qdrant_service.py が持ち、
# ここはその入出力を JSON で表現するだけ。
# =============================================================================


class QdrantHealth(BaseModel):
    """GET /api/qdrant/health。Qdrant が起動しているかの確認。"""

    available: bool
    message: str
    url: Optional[str] = None
    collections_count: Optional[int] = None


class CollectionInfo(BaseModel):
    """GET /api/qdrant/collections の 1 要素（一覧表示用の最小情報）。"""

    name: str
    points_count: int = 0
    status: str = "unknown"


class CollectionDetail(BaseModel):
    """GET /api/qdrant/collections/{name}。

    `vector_size` / `distance` は Named vectors 構成だと dict になりうるため
    型を緩めてある（`QdrantDataFetcher.fetch_collection_info` の実装に合わせる）。
    """

    name: str
    points_count: int = 0
    vectors_count: Optional[int] = None
    indexed_vectors: Optional[int] = None
    status: str = "unknown"
    vector_size: Any = None
    distance: Any = None
    # payload の source を集計したデータ元情報（fetch_collection_source_info）
    sources: Dict[str, Any] = Field(default_factory=dict)
    sample_size: int = 0
    error: Optional[str] = None


class CollectionPoints(BaseModel):
    """GET /api/qdrant/collections/{name}/points。

    payload のキーはコレクションごとに異なるため、列は固定できない。
    `columns` に出現順の列名を、`rows` に素の dict を返し、
    画面側は `columns` の順で描画する。
    """

    name: str
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    limit: int = 50


class InputFileInfo(BaseModel):
    """GET /api/files の 1 要素。"""

    name: str
    # 'ディレクトリ名/ファイル名' 形式。絶対パスは返さない
    path: str
    size: int
    modified: float
    suffix: str


class InputFileListResponse(BaseModel):
    """GET /api/files。"""

    dir: str
    allowed_dirs: List[str]
    files: List[InputFileInfo] = Field(default_factory=list)


class ChunkingRequest(BaseModel):
    """POST /api/chunking/run（CLI 引数と 1:1 対応）。"""

    # 'ディレクトリ名/ファイル名' 形式。許可ディレクトリ外は 400
    input_file: str = Field(min_length=1, description="入力ファイル（--input-file 相当）")
    output_dir: str = Field(default="output_chunked", description="出力先（--output 相当）")
    model: str = Field(
        default="claude-haiku-4-5",
        description="チャンク化に使う LLM（GET /api/models の選択肢から 1 つ）",
    )
    workers: int = Field(default=8, ge=1, le=32, description="並列ワーカー数")
    block_size: int = Field(default=1000, ge=100, le=8000, description="ブロックサイズ（文字）")
    text_column: Optional[str] = Field(default=None, description="CSV のテキストカラム名")
    max_rows: Optional[int] = Field(default=None, ge=1, description="最大処理行数（CSV）")
    combine_rows: bool = Field(default=False, description="CSV 全行を結合する")
    resume: Optional[str] = Field(default=None, description="再開するジョブ ID")
    verbose: bool = False

    _validate_model = field_validator("model")(_require_model_choice)


class QaGenerationRequest(BaseModel):
    """POST /api/qa/generate。

    入力は**チャンク済み CSV**（`chunking` ジョブの出力）。`text` /
    `Combined_Text` / `content` / `chunk_text` のいずれかのカラムが要る。

    ⚠️ 承認（HITL CONFIRM）は発生しない。出力はタイムスタンプ付きの
    新規ファイルなので、既存の Q/A CSV を壊さない。
    """

    input_file: str = Field(
        min_length=1, description="チャンク済み CSV（'ディレクトリ名/ファイル名'）"
    )
    # ⚠️ 既定は `qa_output` 直下。入れ子にすると GET /api/files が拾わず、
    #    「③ Qdrant 登録」の選択肢に出てこない（`QaGenerationParams` と同じ理由）
    output_dir: str = Field(default="qa_output", description="Q/A CSV・JSON の出力先")
    model: str = Field(
        default="claude-sonnet-5",
        description="Q/A 生成に使う LLM（GET /api/models の選択肢から 1 つ）",
    )
    max_docs: Optional[int] = Field(
        default=None, ge=1, description="処理する最大チャンク数（テスト用）"
    )
    # ⚠️ True にするなら Celery ワーカーが起動していること
    use_celery: bool = Field(default=False, description="Celery 並列処理を使う")
    concurrency: int = Field(default=8, ge=1, le=32, description="Celery の並列タスク数")
    batch_chunks: int = Field(
        default=3, ge=1, le=20, description="1 回の LLM 呼び出しで処理するチャンク数"
    )
    analyze_coverage: bool = Field(default=True, description="カバレージ分析を実行する")
    verbose: bool = False

    _validate_model = field_validator("model")(_require_model_choice)


class RegisterRequest(BaseModel):
    """POST /api/qdrant/register。

    ⚠️ `recreate=True` は既存コレクションを削除して作り直す。
    その場合のみ HITL CONFIRM（intervention イベント）が発生する。
    """

    input_file: str = Field(min_length=1, description="Q/A CSV（'ディレクトリ名/ファイル名'）")
    collection: str = Field(min_length=1, description="登録先コレクション名")
    recreate: bool = Field(default=False, description="既存を削除して作り直す（要承認）")
    batch_size: int = Field(default=100, ge=1, le=1000)
    embed_workers: int = Field(default=2, ge=1, le=16)
    text_col: Optional[str] = None
    domain: Optional[str] = None
    max_docs: Optional[int] = Field(default=None, ge=1)
    # Embedding は Gemini（CLAUDE.md のプロバイダ方針）
    provider: str = Field(default="gemini")
    normalize_filename: bool = True
    create_ui_csv: bool = True
    ui_output_dir: str = "qa_output"
    verbose: bool = False


class DeleteCollectionsRequest(BaseModel):
    """POST /api/qdrant/delete。**必ず HITL CONFIRM を通る。**

    単発の DELETE エンドポイントにしていないのは、誤操作で不可逆に消えるのを
    防ぐため（承認を経ずに削除する経路を用意しない）。
    """

    collections: List[str] = Field(min_length=1, description="削除するコレクション名")
    verbose: bool = False


class DataJobStatusResponse(BaseModel):
    """GET /api/data/result/{job_id}。

    結果の形はジョブ種別（chunking / qa / register / delete）で異なるため、
    `result` は素の dict にして `kind` で判別させる。
    """

    job_id: str
    kind: str
    status: Literal["running", "completed", "failed"]
    result: Optional[Dict[str, Any]] = None

    # --- 実行時刻（サーバ時計・エポック秒）------------------------------------
    # フロントは通常 SSE イベントの ts から開始・完了時刻を組み立てるが、
    # ストリームを購読していない経路（結果だけを引く・リロード直後）でも
    # 所要時間を出せるよう、ジョブ側の実測値をそのまま返す。
    created_at: Optional[float] = None
    finished_at: Optional[float] = None
