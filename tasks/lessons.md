# Lessons Learned

## Worktree Environment Setup

**Problem:** New worktrees don't have a `.venv` or `.env` file. Attempting to run tests, migrations, or the dev server without these fails immediately with confusing errors (e.g. pydantic validation errors for missing `DATABASE_URL`, or `command not found: alembic`).

**Rule:** At the start of any session in a worktree, set up both backend and frontend environments:

```bash
# === Backend Setup ===

# 1. Create backend .env if missing
cp .env.example .env  # then adjust values if needed

# 2. Create venv and install deps if missing
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..

# 3. Ensure Postgres is running
docker compose up -d

# 4. Ensure test database exists (one-time per Postgres volume)
docker compose exec db psql -U project_memory -d project_memory -c "CREATE DATABASE project_memory_test;"
docker compose exec db psql -U project_memory -d project_memory_test -c "CREATE EXTENSION IF NOT EXISTS vector;"

# === Frontend Setup ===

# 5. Install node_modules
cd frontend
npm install

# 6. Create frontend .env.local (enables MSW mock server)
echo "NEXT_PUBLIC_ENABLE_MSW=true" > .env.local
```

**Why:** Worktrees share the git repo but not generated artifacts like `.venv`, `.env`, `.env.local`, or `node_modules/` (all are gitignored). Missing any of these causes confusing errors — backend commands fail with pydantic validation errors, frontend fails with `next: command not found`, and API calls fail with `ERR_CONNECTION_REFUSED` if MSW isn't enabled.

**How to apply:** Before running any commands in a new worktree, check for these files:
- `backend/.venv/bin/activate` — if missing, create venv and install deps
- `.env` — if missing, copy from `.env.example`
- `frontend/node_modules/` — if missing, run `npm install`
- `frontend/.env.local` — if missing, create with `NEXT_PUBLIC_ENABLE_MSW=true`

---
