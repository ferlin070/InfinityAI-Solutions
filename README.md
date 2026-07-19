---
title: Sistem AI Ghazwah
emoji: 🤖
colorFrom: blue
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---

# AI Command Center — Sistem Orkestrasi 8-Agent

Platform orkestrasi multi-agent AI: pengguna beri arahan kepada **Claudia (Manager)**, dan dia mengagihkan tugasan kepada 7 agent pakar (marketing, sales, finance, content, teknikal, latihan, operasi). Dibina dengan **FastAPI** + **NVIDIA NIM (Llama 3.1 / Kimi)**, storan hasil kerja ke **Google Drive**.

## Mula Pantas

### Pra-syarat
1. Copy `.env.example` → `.env` dan isi kunci API (lihat `docs/deployment.md` §2 — `OPENAI_API_KEY` untuk lapisan AI semasa; `NVIDIA_NIM_API_KEY` legacy sahaja)
2. Python 3.10+ (untuk backend), Node 20+ (untuk build dashboard), atau Docker

### Cara Menjalankan

| Cara | Arahan |
|---|---|
| **Docker Compose** (disyorkan) | `docker-compose up -d` — tapi build dashboard dulu sekali (lihat nota di bawah) |
| **Manual Python** | Build dashboard dulu, kemudian `cd backend && pip install -r requirements.txt && python -m src.main` |
| **Windows Batch** | Klik dua kali `setup_dan_run.bat` (jika tersedia) |

**Nota penting:** `frontend/src/` (yang disajikan oleh backend sebagai dashboard) ialah **build output**, bukan source — ia gitignored sejak repo ini dibersihkan. Untuk `docker-compose up` atau `python -m src.main` berjaya papar dashboard, build dulu:

```bash
cd frontend-react && npm ci && npm run build
```

Deployment Docker (root `Dockerfile`) buat langkah ni secara automatik dalam satu stage Node — lihat bahagian Deployment di bawah.

Dashboard: `http://localhost:7860`

Rujuk [backend/README.md](backend/README.md) dan [frontend/README.md](frontend/README.md) untuk setup terperinci.

## Struktur Repo

```
├── backend/
│   ├── src/
│   │   ├── main.py                  # FastAPI app
│   │   ├── api/routes.py            # Endpoints
│   │   ├── core/                    # Config, middleware, constants
│   │   ├── services/                # LLM, Drive, logging, orchestrator
│   │   ├── schemas/                 # Pydantic models
│   │   └── agents/                  # Agent system
│   ├── tests/                       # Pytest
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
├── frontend-react/                  # SOURCE dashboard — React 19 + Vite + Tailwind
│   └── src/
│       ├── App.jsx                  # Tab shell (Dashboard/WorkOrder/WhatsApp/...)
│       └── components/workspace/    # Agent Workspace UI (streaming timeline)
├── frontend/
│   ├── src/                         # GENERATED build output (gitignored) — see frontend/README.md
│   └── README.md
├── gateway/                         # Node.js WhatsApp gateway (v2 future)
├── docs/
│   ├── architecture/                # senibina semasa, proposal-v2, agent-workspace-ui
│   ├── business/                    # Dokumentasi produk
│   ├── frontend/                    # Design system
│   ├── development/                 # Audit reports
│   └── archive/                     # Dokumen lama
├── docker-compose.yml               # Local dev orchestration (bukan untuk Railway/Render)
├── .env.example                     # Environment template
└── Dockerfile                       # Root Dockerfile — builds frontend-react + backend as one monolith image (recommended for Railway; also works for Render if Root Directory = repo root)
```

## Struktur Baru (Monorepo)

Projek telah direfaktor menjadi **monorepo terstruktur** untuk skalabiliti v2:

- **`backend/src/`** — FastAPI modular (core, services, api, schemas, agents)
- **`frontend-react/src/`** — dashboard sebenar: React 19 + Vite + Tailwind, termasuk Agent Workspace UI (streaming timeline, tool-call cards, approval flow)
- **`frontend/src/`** — build output `frontend-react` (gitignored, dijana oleh `npm run build` atau stage Docker)
- **`gateway/`** — Node.js WhatsApp gateway (sedia untuk v2)

Lihat [backend/README.md](backend/README.md) dan [frontend/README.md](frontend/README.md) untuk detail. `backend/Dockerfile` (context `backend/` sahaja) ialah image **API-only** — untuk monolith yang sajikan dashboard sekali, guna root `Dockerfile`.

## Dokumentasi

- [Senibina & panduan teknikal sistem semasa](docs/architecture/sistem-semasa.md)
- [Cadangan senibina v2 — multi-tenant SaaS](docs/architecture/proposal-v2.md) — **status: DRAF, menunggu approval**
- [Design system dashboard ("dokumen pejabat")](docs/frontend/dashboard-design.md)
- [Dokumentasi perniagaan (untuk client)](docs/business/dokumentasi-perniagaan.md)
- [Laporan audit keselamatan (Julai 2026)](docs/development/audit-report-2026-07.md)

## Deployment

Rujuk [docs/deployment.md](docs/deployment.md) untuk panduan penuh (Railway/Render untuk backend, Vercel untuk frontend, setup Supabase, senarai environment variables).

⚠️ Auto-deploy ke Hugging Face Spaces (`sync_to_hf.yml`) telah **dibuang** (commit `6c10c5a`) — push ke `main` tidak lagi deploy ke mana-mana secara automatik.
