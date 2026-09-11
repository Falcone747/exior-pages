#!/usr/bin/env bash
set -euo pipefail

ROOT=/opt/exior
cd "$ROOT"

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "Run as root" >&2
  exit 1
fi

if [ -z "${RUNPOD_API_KEY:-}" ]; then
  if [ -r /dev/tty ]; then
    read -rsp 'RunPod read-only API key: ' RUNPOD_API_KEY </dev/tty
    printf '\n' >/dev/tty
  else
    echo 'No interactive terminal available. Run with RUNPOD_API_KEY set.' >&2
    exit 1
  fi
fi

ENVFILE="$ROOT/.env"
touch "$ENVFILE"
chmod 600 "$ENVFILE"
python3 - "$ENVFILE" "$RUNPOD_API_KEY" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); key=sys.argv[2]
lines=p.read_text().splitlines() if p.exists() else []
out=[]; seen=False
for line in lines:
    if line.startswith('RUNPOD_API_KEY='):
        out.append('RUNPOD_API_KEY='+key); seen=True
    else:
        out.append(line)
if not seen: out.append('RUNPOD_API_KEY='+key)
p.write_text('\n'.join(out)+'\n')
PY

mkdir -p gpu-router
cat > gpu-router/Dockerfile <<'EOF'
FROM python:3.12-slim
RUN pip install --no-cache-dir fastapi uvicorn httpx
WORKDIR /app
COPY app.py /app/app.py
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","9000"]
EOF

cat > gpu-router/app.py <<'PY'
import os, time
from typing import Optional
import httpx
from fastapi import FastAPI, Request, Response

app = FastAPI(title="EXIOR GPU Router", version="1.0")
RUNPOD_GRAPHQL = "https://api.runpod.io/graphql"
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY", "").strip()
STATIC_BASE = os.getenv("QWEN_BASE_URL", "").rstrip("/")
MATCH_IMAGE = os.getenv("EXIOR_GPU_IMAGE_MATCH", "exior-gpu").lower()
CACHE_TTL = int(os.getenv("GPU_DISCOVERY_TTL", "15"))
_cache = {"base": None, "ts": 0.0}

async def discover_runpod_base() -> Optional[str]:
    if not RUNPOD_API_KEY:
        return None
    now = time.time()
    if _cache["base"] and now - _cache["ts"] < CACHE_TTL:
        return _cache["base"]
    query = """query { myself { pods { id name desiredStatus imageName } } }"""
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(RUNPOD_GRAPHQL, json={"query": query}, headers=headers)
        r.raise_for_status()
        pods = r.json().get("data", {}).get("myself", {}).get("pods", []) or []
    candidates = [p for p in pods if MATCH_IMAGE in (p.get("imageName") or "").lower() and (p.get("desiredStatus") or "").upper() in {"RUNNING", "CREATED"}]
    for p in reversed(candidates):
        base = f"https://{p['id']}-8000.proxy.runpod.net"
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                h = await client.get(base + "/health")
            if h.status_code == 200:
                _cache.update({"base": base, "ts": now})
                return base
        except Exception:
            continue
    _cache.update({"base": None, "ts": now})
    return None

async def backend_base() -> str:
    dynamic = await discover_runpod_base()
    if dynamic:
        return dynamic
    if STATIC_BASE:
        return STATIC_BASE[:-3] if STATIC_BASE.endswith("/v1") else STATIC_BASE
    raise RuntimeError("No GPU backend available")

@app.get("/health")
async def health():
    try:
        base = await backend_base()
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(base + "/health")
        return {"ok": r.status_code == 200, "backend": base, "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.api_route("/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"])
async def proxy(path: str, request: Request):
    base = await backend_base()
    target = f"{base}/{path}"
    body = await request.body()
    headers = {k:v for k,v in request.headers.items() if k.lower() not in {"host","content-length"}}
    async with httpx.AsyncClient(timeout=1200) as client:
        r = await client.request(request.method, target, content=body, headers=headers, params=request.query_params)
    passthrough = {k:v for k,v in r.headers.items() if k.lower() not in {"content-encoding","transfer-encoding","connection"}}
    return Response(content=r.content, status_code=r.status_code, headers=passthrough, media_type=r.headers.get("content-type"))
PY

cat > litellm_config.yaml <<'EOF'
model_list:
  - model_name: exior-qwen
    litellm_params:
      model: openai/Qwen/Qwen3-30B-A3B-Instruct-2507-FP8
      api_base: http://gpu-router:9000/v1
      api_key: none
router_settings:
  routing_strategy: usage-based-routing-v2
  enable_pre_call_checks: true
  num_retries: 2
  retry_after: 1
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
EOF

python3 - <<'PY'
from pathlib import Path
p=Path('compose.yaml')
s=p.read_text()
if '\n  gpu-router:' not in s:
    marker='\n  litellm:\n'
    block='''\n  gpu-router:\n    build: ./gpu-router\n    restart: unless-stopped\n    environment:\n      RUNPOD_API_KEY: ${RUNPOD_API_KEY:-}\n      QWEN_BASE_URL: ${QWEN_BASE_URL:-}\n      EXIOR_GPU_IMAGE_MATCH: ${EXIOR_GPU_IMAGE_MATCH:-exior-gpu}\n      GPU_DISCOVERY_TTL: ${GPU_DISCOVERY_TTL:-15}\n    networks: [exior]\n\n  litellm:\n'''
    s=s.replace(marker, block)
p.write_text(s)
PY

docker compose up -d --build --force-recreate gpu-router litellm exior-worker
sleep 5

echo '=== EXIOR HEALTH ==='
curl -fsS http://127.0.0.1:8001/health || true
echo

echo '=== EXIOR BRAIN ==='
curl -fsS -X POST http://127.0.0.1:8001/brain/test || true
echo
