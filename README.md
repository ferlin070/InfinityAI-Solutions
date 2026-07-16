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
1. Copy `.env.example` → `.env` dan isi kunci API NVIDIA
2. Python 3.10+ (untuk backend) atau Docker

### Cara Menjalankan

| Cara | Arahan |
|---|---|
| **Docker Compose** (disyorkan) | `docker-compose up -d` |
| **Manual Python** | `cd backend && pip install -r requirements.txt && python -m src.main` |
| **Windows Batch** | Klik dua kali `setup_dan_run.bat` (jika tersedia) |

Dashboard: `http://localhost:7860` 

Rujuk [backend/README.md](backend/README.md) untuk setup terperinci.

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
├── frontend/
│   ├── src/
│   │   ├── index.html               # Main dashboard HTML
│   │   ├── css/                     # Design tokens + component styles
│   │   └── js/                      # API client, logger, UI
│   └── README.md
├── gateway/                         # Node.js WhatsApp gateway (v2 future)
├── docs/
│   ├── architecture/                # senibina semasa, proposal-v2
│   ├── business/                    # Dokumentasi produk
│   ├── frontend/                    # Design system
│   ├── development/                 # Audit reports
│   └── archive/                     # Dokumen lama
├── docker-compose.yml               # Local dev orchestration (bukan untuk Railway/Render)
├── .env.example                     # Environment template
└── Dockerfile                       # Root Dockerfile (deprecated — use backend/Dockerfile)
```

## Struktur Baru (Monorepo)

Projek telah direfaktor menjadi **monorepo terstruktur** untuk skalabiliti v2:

- **`backend/src/`** — FastAPI modular (core, services, api, schemas, agents)
- **`frontend/src/`** — HTML/CSS/JS terpisah (CSS tokens, JS modules)
- **`gateway/`** — Node.js WhatsApp gateway (sedia untuk v2)

Lihat [backend/README.md](backend/README.md) dan [frontend/README.md](frontend/README.md) untuk detail.

## Dokumentasi

- [Senibina & panduan teknikal sistem semasa](docs/architecture/sistem-semasa.md)
- [Cadangan senibina v2 — multi-tenant SaaS](docs/architecture/proposal-v2.md) — **status: DRAF, menunggu approval**
- [Design system dashboard ("dokumen pejabat")](docs/frontend/dashboard-design.md)
- [Dokumentasi perniagaan (untuk client)](docs/business/dokumentasi-perniagaan.md)
- [Laporan audit keselamatan (Julai 2026)](docs/development/audit-report-2026-07.md)

## Deployment

Rujuk [docs/deployment.md](docs/deployment.md) untuk panduan penuh (Railway/Render untuk backend, Vercel untuk frontend, setup Supabase, senarai environment variables).

⚠️ Auto-deploy ke Hugging Face Spaces (`sync_to_hf.yml`) telah **dibuang** (commit `6c10c5a`) — push ke `main` tidak lagi deploy ke mana-mana secara automatik.
