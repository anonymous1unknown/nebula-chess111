#!/usr/bin/env bash
# ─── Nebula Chess — Local Development Quick Start ────────────────────────────
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${CYAN}[nebula]${NC} $1"; }
ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }

echo ""
echo -e "${CYAN}  ♟  Nebula Chess — Quick Start${NC}"
echo ""

# ── Check dependencies ────────────────────────────────────────────────────────
command -v python3 &>/dev/null || fail "Python 3.12+ required"
command -v node    &>/dev/null || fail "Node.js 20+ required"
command -v psql    &>/dev/null || warn "PostgreSQL client not found (needed for DB creation)"
command -v redis-cli &>/dev/null || warn "Redis CLI not found"

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log "Python $PYTHON_VER"

# ── Environment ────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    log "Creating .env from .env.example…"
    cp .env.example .env
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i.bak "s/change-me-please-use-openssl-rand-hex-32-for-production/$SECRET/" .env && rm .env.bak
    ok ".env created with random SECRET_KEY"
else
    ok ".env already exists"
fi

# ── Backend ────────────────────────────────────────────────────────────────────
log "Setting up backend…"
cd backend

if [ ! -d .venv ]; then
    python3 -m venv .venv
    ok "Virtual environment created"
fi

source .venv/bin/activate
pip install -q -r requirements.txt
ok "Backend dependencies installed"

log "Running database migrations…"
alembic upgrade head || warn "Migration failed — is PostgreSQL running?"

cd ..

# ── Frontend ───────────────────────────────────────────────────────────────────
log "Setting up frontend…"
cd frontend
npm install --silent
ok "Frontend dependencies installed"
cd ..

# ── Launch ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Nebula Chess is ready to launch!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Start backend:   cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
echo "  Start frontend:  cd frontend && npm run dev"
echo ""
echo "  API docs:        http://localhost:8000/api/docs"
echo "  App:             http://localhost:5173"
echo ""

# ── Docker alternative ─────────────────────────────────────────────────────────
if command -v docker &>/dev/null; then
    echo -e "  ${CYAN}Or run everything with Docker:${NC}"
    echo "  docker compose up -d && docker compose run --rm migrator"
    echo "  Then open: http://localhost"
    echo ""
fi
