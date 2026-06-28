# ♟ Nebula Chess

> **Premium online chess platform** — server-authoritative, real-time, beautifully crafted.  
> Built to stand alongside chess.com in architecture and UX quality.

![Nebula Chess](https://img.shields.io/badge/version-1.0.0-7c63e8?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=for-the-badge&logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-dc382d?style=for-the-badge&logo=redis)

---

## ✨ Features

| Category | Features |
|---|---|
| **Gameplay** | 1v1 online, vs Stockfish AI (5 difficulty levels), spectate, invite links, rematch |
| **Real-time** | WebSocket rooms, Redis pub/sub (multi-worker), reconnect, draw offers, resign |
| **Chess** | server-authoritative validation, legal move highlights, check/checkmate/stalemate, PGN/FEN, promotion picker |
| **UI/UX** | drag & drop, touch support, animated pieces, eval bar, move list, clocks, chat, 4 board themes |
| **Auth** | JWT + refresh token rotation, bcrypt hashing, WebSocket auth |
| **Rating** | ELO system with K=32, per-format ratings (bullet/blitz/rapid/classical) |
| **Anti-cheat** | Statistical engine-correlation analysis, time anomaly detection, suspicion scores, review workflow |
| **Puzzles** | Daily puzzle with hint system, interactive solving |
| **Analysis** | Free-form board with PGN/FEN import, move-by-move navigation, eval bar |
| **Leaderboard** | Global rankings by ELO with win-rate and country |
| **Monitoring** | Prometheus metrics, Grafana dashboards, health endpoint |
| **Infra** | Docker Compose, Nginx reverse proxy with WS support, horizontal scaling with Redis |

---

## 🏗 Architecture

```
Client (React SPA)
    │
    ├── HTTPS/WSS
    │
Nginx (reverse proxy + rate limiting)
    │
    ├── /api/*     ──→  FastAPI Backend (uvicorn, 4 workers)
    ├── /ws/*      ──→  FastAPI WebSocket (same process)
    └── /*         ──→  Static files (React build)
                              │
                   ┌──────────┴──────────┐
              PostgreSQL              Redis
           (persistent data)    (game state + pub/sub)
                              │
                         Stockfish
                       (AI + analysis)
```

**Key Design Decisions:**
- **Server-authoritative**: All chess move validation happens on the backend with `python-chess`. The client UI never determines legality.
- **Redis pub/sub**: Game state is synced across multiple backend workers via Redis channels, enabling true horizontal scaling.
- **Stateless workers**: Each FastAPI worker can handle any WS connection; game state is shared via Redis.
- **ELO per format**: Separate ratings for bullet/blitz/rapid/classical.

---

## 🚀 Quick Start (Docker — Recommended)

### Prerequisites
- Docker 24+ and Docker Compose v2
- ~2 GB RAM minimum

### 1. Clone and configure

```bash
git clone https://github.com/your-org/nebula-chess.git
cd nebula-chess

# Create environment file
cp .env.example .env

# Edit .env — at minimum, set a strong SECRET_KEY:
# SECRET_KEY=$(openssl rand -hex 32)
nano .env
```

### 2. Start all services

```bash
docker compose up -d
```

This starts:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **Backend API** on port 8000
- **Frontend** (built + served by nginx) on port 80
- **Prometheus** on port 9090
- **Grafana** on port 3000

### 3. Run database migrations

```bash
docker compose run --rm migrator
```

### 4. Open the app

```
http://localhost
```

---

## 💻 Local Development (No Docker)

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- Stockfish (`apt install stockfish` / `brew install stockfish`)

### Backend setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp ../.env.example .env
# Edit DATABASE_URL and REDIS_URL to point to your local services

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

Backend API is now at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/api/docs`

### Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (proxies /api and /ws to localhost:8000)
npm run dev
```

Frontend is now at `http://localhost:5173`

---

## 🧪 Testing Multiplayer

**Method 1: Two browser tabs**
1. Open `http://localhost:5173` in Tab 1
2. Register user `alice` and create a game → copy the invite code
3. Open `http://localhost:5173` in a private/incognito Tab 2
4. Register user `bob` → click "Join Game" → paste invite code
5. Both players are now connected in real-time

**Method 2: AI game (single player)**
1. Log in as any user
2. Click "vs Computer" → choose difficulty → click "Play vs Computer"
3. Stockfish responds automatically after each of your moves

**Method 3: WebSocket CLI test**
```bash
# Install wscat
npm i -g wscat

# Connect to a game
wscat -c "ws://localhost:8000/ws/game/GAME_ID?token=YOUR_JWT"

# Send a move
{"type":"move","data":{"uci":"e2e4"}}

# Send chat
{"type":"chat","data":{"message":"Good game!"}}

# Offer draw
{"type":"offer_draw"}

# Resign
{"type":"resign"}
```

---

## 🗄 Database

### Schema overview

| Table | Purpose |
|---|---|
| `users` | Accounts, ELO, stats, preferences |
| `games` | Game records with FEN, PGN, clocks, results |
| `moves` | Per-move log with timing and analysis data |
| `chat_messages` | In-game chat history |
| `cheat_flags` | Anti-cheat suspicion reports per game |
| `refresh_tokens` | JWT refresh token rotation |
| `friendships` | Friend requests and blocking |
| `tournaments` | Tournament definitions |
| `tournament_participants` | Per-player tournament state |
| `achievements` | Achievement catalog |
| `user_achievements` | Earned achievements |

### Useful queries

```sql
-- Top 10 players by ELO
SELECT username, elo, games_played, games_won FROM users
ORDER BY elo DESC LIMIT 10;

-- Recent games for a player
SELECT id, result, move_count, finished_at FROM games
WHERE white_id = 'USER_UUID' OR black_id = 'USER_UUID'
ORDER BY finished_at DESC LIMIT 20;

-- Anti-cheat pending reviews
SELECT cf.*, u.username FROM cheat_flags cf
JOIN users u ON u.id = cf.user_id
WHERE cf.status = 'pending'
ORDER BY cf.overall_suspicion_score DESC;
```

### Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "add_something"

# Rollback one step
alembic downgrade -1
```

---

## ⚙️ Configuration Reference

All configuration is via environment variables (`.env` file).

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | **Required.** JWT signing key (use `openssl rand -hex 32`) |
| `DATABASE_URL` | `postgresql+asyncpg://nebula:nebula@localhost:5432/nebula_chess` | PostgreSQL connection URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `ENVIRONMENT` | `development` | `development` or `production` |
| `STOCKFISH_PATH` | `/usr/games/stockfish` | Path to Stockfish binary |
| `STOCKFISH_DEPTH` | `15` | Engine analysis depth |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token TTL |
| `ELO_K_FACTOR` | `32` | ELO K-factor for rating changes |
| `ANTICHEAT_ENGINE_CORRELATION_THRESHOLD` | `0.85` | Flag if engine match rate > this |
| `ANTICHEAT_ACCURACY_THRESHOLD` | `0.92` | Flag if accuracy > this |
| `AUTH_RATE_LIMIT` | `10/minute` | Rate limit for auth endpoints |
| `API_RATE_LIMIT` | `100/minute` | Rate limit for general API |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `GRAFANA_PASSWORD` | `nebula_admin` | Grafana admin password |

---

## 🔌 API Reference

### Authentication

```
POST /api/auth/register   { username, email, password }
POST /api/auth/login      { username_or_email, password }
POST /api/auth/refresh    { refresh_token }
POST /api/auth/logout     { refresh_token }
```

### Games

```
POST /api/games/create               Create a new game
POST /api/games/join/{invite_code}   Join by invite code
GET  /api/games/{id}/state           Get current game state
GET  /api/games/{id}/legal-moves     Get all legal moves (FEN-based)
GET  /api/games/{id}/moves           Full move history from DB
GET  /api/games/history/me           My game history
```

### Users & Leaderboard

```
GET   /api/users/me           My profile
PATCH /api/users/me           Update my profile/settings
GET   /api/users/{username}   Any player's public profile
GET   /api/leaderboard/       Top players by ELO
```

### Puzzles

```
GET /api/puzzles/daily   Today's puzzle
GET /api/puzzles/        Puzzle list
```

### WebSocket Protocol

Connect to: `ws://localhost:8000/ws/game/{game_id}?token=ACCESS_TOKEN`

**Client → Server messages:**

```json
{ "type": "move",         "data": { "uci": "e2e4" } }
{ "type": "chat",         "data": { "message": "Good game!" } }
{ "type": "resign" }
{ "type": "offer_draw" }
{ "type": "accept_draw" }
{ "type": "decline_draw" }
{ "type": "ping" }
{ "type": "request_state" }
```

**Server → Client messages:**

```json
{ "type": "game_state",         "data": { ...full state... } }
{ "type": "move",               "data": { "uci": "e2e4", "san": "e4", "fen": "...", ... } }
{ "type": "move_rejected",      "data": { "reason": "Illegal move" } }
{ "type": "chat",               "data": { "username": "alice", "message": "hi", "ts": "..." } }
{ "type": "game_over",          "data": { "result": "white_wins", "termination": "checkmate" } }
{ "type": "draw_offered",       "data": { "by": "alice", "role": "white" } }
{ "type": "draw_declined",      "data": { "by": "bob" } }
{ "type": "player_disconnected","data": { "username": "alice", "role": "white" } }
{ "type": "room_info",          "data": { "players": [...], "spectators": [...], "count": 3 } }
{ "type": "pong",               "ts": 1234567890 }
```

---

## 📊 Monitoring

### Prometheus
Access at `http://localhost:9090`

Key metrics available via `/metrics`:
- `http_requests_total` — request counts by method, handler, status
- `http_request_duration_seconds` — latency histograms
- Python process metrics (memory, CPU, GC)

### Grafana
Access at `http://localhost:3000`  
Default credentials: `admin` / `nebula_admin` (set `GRAFANA_PASSWORD` to change)

Pre-configured dashboard: **Nebula Chess — Live Metrics**

---

## 📈 Scaling Notes

**Horizontal scaling (multiple backend workers):**
```bash
# Scale to 4 backend replicas
docker compose up -d --scale backend=4
```
Game state is stored in Redis, so all workers share state automatically via pub/sub.

**Nginx WebSocket tip:**  
When load-balancing WebSocket connections behind nginx, use `ip_hash` or sticky sessions, or rely fully on Redis pub/sub (the default). Our architecture handles both.

**Load test (k6):**
```javascript
// k6 load test sketch
import ws from 'k6/ws'
export default function() {
  ws.connect('ws://localhost/ws/game/GAME_ID?token=TOKEN', {}, (socket) => {
    socket.on('open', () => socket.send(JSON.stringify({ type: 'ping' })))
    socket.on('message', (d) => console.log(d))
  })
}
// k6 run --vus 100 --duration 30s script.js
```

**Redis memory:**  
Each game state is ~2KB in Redis. With 10,000 concurrent games: ~20MB. Very efficient.

---

## 🛡 Security

- **Server-authoritative**: All move validation on the server — client cannot cheat by sending illegal moves
- **JWT rotation**: Refresh tokens are rotated on each use and stored hashed
- **Rate limiting**: Auth endpoints at 10/min, API at 100/min via slowapi
- **CORS**: Strict origin whitelist
- **CSP headers**: Set by nginx
- **Input validation**: Pydantic schemas on all API inputs
- **SQL injection**: Protected by SQLAlchemy ORM (parameterized queries)
- **XSS**: React escapes all rendered content

---

## 🔬 Anti-Cheat System

The anti-cheat engine runs post-game analysis:

1. **Engine correlation**: What % of moves matched Stockfish's top choice?
2. **Accuracy score**: Average centipawn loss (perfect = 0)
3. **Time anomaly**: % of moves played unusually fast (< 800ms)

**Scoring:**
```
overall_score = 0.45 × engine_correlation
              + 0.30 × accuracy_score
              + 0.25 × time_anomaly_score
```

**Safe flow:**
```
auto-flag → pending review → human moderator review → confirmed/dismissed/appeal
```

No automatic bans. All flags require human review.

---

## 📁 Project Structure

```
nebula-chess/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial.py
│   └── app/
│       ├── main.py           ← FastAPI app, middleware, routes
│       ├── config.py         ← Settings (pydantic-settings)
│       ├── database.py       ← Async SQLAlchemy engine
│       ├── redis_client.py   ← Redis connection
│       ├── api/
│       │   ├── auth.py       ← Register, login, refresh, logout
│       │   ├── deps.py       ← get_current_user dependency
│       │   ├── games.py      ← Create, join, history, legal moves
│       │   ├── users.py      ← Profile, settings
│       │   ├── leaderboard.py
│       │   ├── tournaments.py
│       │   └── puzzles.py
│       ├── core/
│       │   ├── security.py   ← JWT, hashing, tokens
│       │   ├── chess_engine.py ← python-chess wrapper (server authority)
│       │   ├── elo.py        ← ELO calculation
│       │   └── anti_cheat.py ← Statistical cheat detection
│       ├── models/
│       │   ├── user.py       ← User, RefreshToken, Friendship
│       │   ├── game.py       ← Game, GameInvitation
│       │   ├── move.py       ← Move (per-move record)
│       │   ├── chat.py       ← ChatMessage
│       │   ├── tournament.py ← Tournament, TournamentParticipant
│       │   ├── achievement.py
│       │   └── anti_cheat.py ← CheatFlag
│       ├── services/
│       │   ├── game_service.py    ← Redis game state, move application, ELO
│       │   └── stockfish_service.py ← AI moves + analysis
│       └── websocket/
│           ├── manager.py    ← WS connection manager + Redis pub/sub
│           └── handlers.py   ← WS message handlers (move, chat, resign…)
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx           ← Router setup
│       ├── index.css         ← Tailwind + custom CSS (nebula theme)
│       ├── api/
│       │   └── client.ts     ← Axios + all API calls
│       ├── store/
│       │   ├── authStore.ts  ← Zustand auth state
│       │   └── gameStore.ts  ← Zustand game state
│       ├── hooks/
│       │   └── useGameWebSocket.ts ← WS connection + message handling
│       ├── types/
│       │   └── index.ts      ← TypeScript types for all entities
│       └── components/
│           ├── Board/
│           │   ├── ChessBoard.tsx  ← Drag & drop board with highlights
│           │   └── EvalBar.tsx     ← Position evaluation bar
│           ├── Game/
│           │   ├── GamePage.tsx    ← Main game view
│           │   ├── Clock.tsx       ← Countdown timer
│           │   └── MoveList.tsx    ← SAN move notation list
│           ├── Chat/
│           │   └── ChatPanel.tsx   ← In-game chat
│           ├── Lobby/
│           │   └── LobbyPage.tsx   ← Game creation & joining
│           ├── Auth/
│           │   └── LoginPage.tsx   ← Login + Register
│           ├── Profile/
│           │   ├── ProfilePage.tsx ← Player stats & history
│           │   └── SettingsPage.tsx
│           ├── Leaderboard/
│           │   └── LeaderboardPage.tsx
│           ├── Puzzle/
│           │   └── PuzzlePage.tsx  ← Daily puzzle solver
│           ├── Analysis/
│           │   └── AnalysisPage.tsx ← PGN/FEN import + eval board
│           └── Layout/
│               └── Layout.tsx      ← Navbar + page wrapper
│
├── nginx/
│   └── nginx.conf            ← Reverse proxy + WS + rate limiting
│
└── monitoring/
    ├── prometheus.yml
    └── grafana/
        ├── datasources/
        │   └── prometheus.yml
        └── dashboards/
            ├── dashboard.yml
            └── nebula_chess.json
```

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feat/amazing-feature`
5. Open a Pull Request

---

## 🗺 Roadmap

- [ ] Full tournament system (Swiss + Arena)
- [ ] Friend system and private messaging
- [ ] Mobile app (React Native)
- [ ] Game analysis with Stockfish (post-game)
- [ ] Opening explorer
- [ ] Achievements system
- [ ] Correspondence chess
- [ ] Blindfold chess mode
- [ ] Streamer/spectator mode with delay
- [ ] Club system

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <strong>Built with ♟ by the Nebula Chess Team</strong><br>
  <em>Server-authoritative. Real-time. Premium.</em>
</div>
