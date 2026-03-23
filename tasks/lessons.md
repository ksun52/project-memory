# Lessons Learned

## Worktree Environment Setup

**Problem:** New worktrees don't have a `.venv` or `.env` file. Attempting to run tests, migrations, or the dev server without these fails immediately with confusing errors (e.g. pydantic validation errors for missing `DATABASE_URL`, or `command not found: alembic`).

**Rule:** At the start of any session in a worktree, before running any backend commands, verify and set up the environment:

```bash
# 1. Create .env if missing
cp .env.example .env  # then adjust values if needed

# 2. Create venv and install deps if missing
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Ensure Postgres is running
docker compose up -d

# 4. Ensure test database exists (one-time per Postgres volume)
docker compose exec db psql -U project_memory -d project_memory -c "CREATE DATABASE project_memory_test;"
docker compose exec db psql -U project_memory -d project_memory_test -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Why:** Worktrees share the git repo but not generated artifacts like `.venv` or `.env` (both are gitignored). This cost a full cycle of debugging this session.

**How to apply:** Check for `.venv/bin/activate` and `.env` existence before running any `pytest`, `alembic`, `uvicorn`, or `python -m scripts.*` commands. If either is missing, set them up first.

---
