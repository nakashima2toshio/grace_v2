#!/bin/bash
# ==============================================================
# SessionStart hook — Claude Code on the web（クラウド VM）専用
# ==============================================================
# やること（すべて冪等。何度走っても同じ状態になる）:
#   1. backend テスト用の依存（requirements-test.txt）を .venv へ入れる
#   2. frontend の依存（npm install）を入れる
#   3. dockerd を起動し、docker-compose/docker-compose.yml の
#      Qdrant（:6333）と Redis（:6379）を立ち上げる
#      → backend/tests/integration/ の結合テストが VM 内で走るようになる
#   4. 環境変数 GRACE_E2E_SNAPSHOT_URL があれば、E2E 用の追加依存（requirements-e2e.txt）
#      を入れ、Mac から持ってきた実データのスナップショットを Qdrant へ復元する
#      （scripts/qdrant_snapshot.py restore。既存のコレクションは上書きしない）
#      → backend/tests/e2e/ が実データで走るようになる（GRACE_E2E=1 で実行）
#
# ローカル（Mac）では何もしない（CLAUDE_CODE_REMOTE が無いので即 exit 0）。
# Mac では従来どおり Docker Desktop で `docker compose ... up -d` する。
#
# ⚠️ 失敗してもセッション開始は止めない（set -e を使わない）。
#    どこで失敗したかは stdout の 1 行サマリと $LOG_DIR のログに残す。
#    SessionStart hook の stdout は Claude のコンテキストに入るので、
#    サマリは短く保つ（詳細はログへ）。
# ==============================================================
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0

LOG_DIR="${TMPDIR:-/tmp}/grace-session-start"
mkdir -p "$LOG_DIR"
COMPOSE_FILE="docker-compose/docker-compose.yml"
export PATH="$HOME/.local/bin:$PATH"

status=()

# --------------------------------------------------------------
# 1. backend テスト依存（CI と同じ requirements-test.txt）
# --------------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
  if { [ -x .venv/bin/python ] || uv venv -q .venv; } \
     && uv pip install -q --python .venv/bin/python -r requirements-test.txt \
        >"$LOG_DIR/uv.log" 2>&1; then
    status+=("python-deps:ok")
  else
    status+=("python-deps:FAILED(see $LOG_DIR/uv.log)")
  fi
else
  status+=("python-deps:skipped(no uv)")
fi

# --------------------------------------------------------------
# 2. frontend 依存（npm install はキャッシュが効くので npm ci より速い）
# --------------------------------------------------------------
if command -v npm >/dev/null 2>&1 && [ -f frontend/package.json ]; then
  if (cd frontend && npm install --no-audit --no-fund >"$LOG_DIR/npm.log" 2>&1); then
    status+=("frontend-deps:ok")
  else
    status+=("frontend-deps:FAILED(see $LOG_DIR/npm.log)")
  fi
fi

# --------------------------------------------------------------
# 3. Qdrant / Redis（docker compose）
# --------------------------------------------------------------
wait_for() {  # wait_for <秒> <コマンド...>
  local secs=$1; shift
  for _ in $(seq 1 "$secs"); do
    "$@" >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}

qdrant_ready() { curl -sf -o /dev/null --noproxy '*' http://localhost:6333/readyz; }
redis_ready() { (exec 3<>/dev/tcp/127.0.0.1/6379 && printf 'PING\r\n' >&3 && head -c5 <&3 | grep -q PONG); }

if command -v docker >/dev/null 2>&1; then
  if ! docker info >/dev/null 2>&1; then
    # ツール呼び出しやフック終了で子プロセスごと落ちないよう、setsid で切り離す
    setsid nohup dockerd >"$LOG_DIR/dockerd.log" 2>&1 </dev/null &
    wait_for 60 docker info || status+=("dockerd:FAILED(see $LOG_DIR/dockerd.log)")
  fi
  if docker info >/dev/null 2>&1; then
    if docker compose -f "$COMPOSE_FILE" up -d >"$LOG_DIR/compose.log" 2>&1; then
      wait_for 60 qdrant_ready && status+=("qdrant:localhost:6333") \
        || status+=("qdrant:NOT_READY(see $LOG_DIR/compose.log)")
      wait_for 30 redis_ready && status+=("redis:localhost:6379") \
        || status+=("redis:NOT_READY(see $LOG_DIR/compose.log)")
    else
      status+=("compose:FAILED(see $LOG_DIR/compose.log)")
    fi
  fi
else
  status+=("docker:not-installed")
fi

# Docker が使えない環境でも Redis だけはネイティブで立てられることがある
if ! redis_ready && command -v redis-server >/dev/null 2>&1; then
  redis-server --daemonize yes --port 6379 >"$LOG_DIR/redis.log" 2>&1 \
    && wait_for 10 redis_ready && status+=("redis:native")
fi

# --------------------------------------------------------------
# 4. E2E の実データ（GRACE_E2E_SNAPSHOT_URL があるときだけ）
# --------------------------------------------------------------
if [ -n "${GRACE_E2E_SNAPSHOT_URL:-}" ]; then
  if ! uv pip install -q --python .venv/bin/python -r requirements-e2e.txt >"$LOG_DIR/uv-e2e.log" 2>&1; then
    status+=("e2e-deps:FAILED(see $LOG_DIR/uv-e2e.log)")
  fi
  # 同じコンテナで 2 回目以降（resume など）は、復元済みならダウンロードし直さない。
  # Qdrant のデータも同じコンテナの docker volume にあるので、目印と食い違わない。
  marker="$LOG_DIR/e2e-restored-$(printf '%s' "$GRACE_E2E_SNAPSHOT_URL" | sha256sum | cut -c1-16)"
  if [ -f "$marker" ]; then
    status+=("e2e-data:restored(earlier)")
  elif ! qdrant_ready; then
    status+=("e2e-data:SKIPPED(no qdrant)")
  elif .venv/bin/python scripts/qdrant_snapshot.py restore >"$LOG_DIR/restore.log" 2>&1; then
    touch "$marker"
    status+=("e2e-data:$(grep -c 'restored:' "$LOG_DIR/restore.log") restored,$(grep -c 'skipped:' "$LOG_DIR/restore.log") skipped")
  else
    status+=("e2e-data:FAILED(see $LOG_DIR/restore.log)")
  fi
  for key in ANTHROPIC_API_KEY GOOGLE_API_KEY; do
    [ -n "${!key:-}" ] || status+=("e2e:${key}-missing")
  done
fi

echo "[grace session-start] ${status[*]}"
echo "[grace session-start] 結合テスト: uv run --no-sync pytest backend/tests/integration -q -rs"
exit 0
