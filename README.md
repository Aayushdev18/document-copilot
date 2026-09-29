# Document Copilot

An internal AI chatbot that lets analysts query a corpus of documents in plain English and get sourced, citable answers.

## The client

**Driftwood Capital** — fictional independent investment research firm. Their analysts spend half their week reading 10-Ks and 10-Qs before they can produce any original analysis. Document Copilot eats that intake work so they can skip straight to insight.

Full brief: [docs/client-brief.md](docs/client-brief.md)

## Stack

| Layer              | Choice                                               |
| ------------------ | ---------------------------------------------------- |
| Backend            | Python + FastAPI                                     |
| Frontend           | Vite + React SPA + TypeScript                        |
| Database           | Supabase Postgres (users, chats, documents, chunks)  |
| Migrations         | SQLAlchemy models + Alembic                          |
| Retrieval          | Supabase `pgvector` + Postgres full-text search      |
| Auth               | Supabase Auth (email only)                           |
| Hosting            | Railway                                              |
| LLM + embeddings   | OpenAI                                               |

## Repo layout

```text
document-copilot/
├── AGENTS.md           # agent instructions (read first)
├── README.md           # this file
├── data/               # local corpus + download script (payloads gitignored)
├── docs/
│   └── client-brief.md # the client one-pager
├── backend/            # FastAPI service
└── frontend/           # React SPA (Vite)
```

## Prerequisites

Install these before setting up `backend/` or `frontend/`:

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.12+ | Backend runtime | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + `data/download.py` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need accounts/keys for external services once the app is wired up. Start with [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) (account + project), then create an [OpenAI API key](https://platform.openai.com/api-keys) when the LLM layer is wired up.

## Running locally

The desk runs without Supabase or an OpenAI key. Select Apple, Microsoft, NVIDIA, Amazon, or Alphabet. The latest 10-K passages are already loaded from SEC EDGAR (`backend/app/corpus/seed.json`), and annual figures for revenue, net income, operating income, EPS, cash, and debt come from the matching 10-K XBRL facts (`backend/app/corpus/financials.json`), with the prior year and the change beside them. Item 1A risks and the analyst brief each point back to a section and paragraph. Chat answers stay on the selected company: a filing question cites the passage, a figure cites the accession and EDGAR URL, and a question the corpus does not cover is refused. Set `OPENAI_API_KEY` in `backend/.env` (and optionally `OPENAI_MODEL`, default `gpt-4o-mini`) to have a model write the prose. Sign in with any email. That session stays on this machine.

```bash
# backend — from the repo root
cd backend
uv sync
# without uv: pip install -r requirements.txt
uv run uvicorn app.main:app --host 0.0.0.0 --port 43124

# frontend — second terminal
cd frontend
pnpm install
pnpm dev
```

Open [http://127.0.0.1:43123](http://127.0.0.1:43123). The Vite dev server proxies `/api` to the backend.

Refresh the filing excerpts with `python backend/ingest/build_seed.py` (SEC requires a descriptive User-Agent; edit it at the top of that script). Restart the backend so it reloads an empty database, or delete `backend/document_copilot.db` first.

`AUTH_MODE=supabase` is reserved for the hosted auth path in the architecture notes. The process refuses to start in that mode until the Supabase settings are present. Alembic, pgvector, and model-written answers are the next steps in [docs/architecture.md](docs/architecture.md); they are not required to use the desk.

Setup guides:

- [Supabase](docs/guides/supabase-setup.md) — account, hosted project (dashboard or CLI)
- [Backend](docs/guides/backend-setup.md)
- [Frontend](docs/guides/frontend-setup.md)

Check the backend with `cd backend && uv run pytest && uv run ruff check .`. Check the frontend with `cd frontend && pnpm exec tsc -b --noEmit && pnpm lint`.

## Sample SEC data

Use the standalone downloader to fetch a small local 10-K sample from SEC EDGAR.
Edit the params at the top of `data/download.py`, especially `USER_AGENT`, then run:

```bash
uv run data/download.py
```

By default this downloads the latest 5 10-K filings for AAPL, MSFT, NVDA, AMZN, and GOOGL into year folders under `data/downloads/` and writes a `manifest.json`.
Downloaded files are gitignored; the `data/` folder itself stays in git for the script and notes.
