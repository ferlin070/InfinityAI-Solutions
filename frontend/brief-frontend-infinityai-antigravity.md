# BRIEF ANTIGRAVITY — Frontend Development
## Projek: InfinityAI-Solutions (AI Command Center — Sistem Orkestrasi 8-Agent)
Repo: https://github.com/ferlin070/InfinityAI-Solutions

---

## 0. KONTEKS PROJEK (baca dulu sebelum mula)

Dashboard vanilla HTML/CSS/JS untuk platform orkestrasi multi-agent AI (Claudia = manager, 7 agent pakar). Frontend **bukan** React/Vue — struktur sedia ada:

```
frontend/src/
├── index.html           # HTML struktur sahaja
├── css/
│   ├── tokens.css       # Design tokens — load PERTAMA
│   ├── letterhead.css   # Header, tajuk
│   ├── forms.css        # Input, butang, borang
│   ├── table.css        # Log, jadual, chips
│   ├── layout.css       # Grid, roster staf, footer
│   └── responsive.css   # Breakpoint 960px & 440px
└── js/
    ├── main.js          # Entry point, DOM init
    ├── api.js           # fetchExecute, fetchHistory
    ├── logger.js        # addLog, escapeHtml
    ├── history.js       # updateHistory
    └── ui.js            # executeTask, interaction handlers
```

Konsep visual: **"Dokumen Pejabat"** — dashboard ini direka sebagai *pejabat maya*, bukan "sci-fi mission control". Borang tugasan = Borang Arahan Kerja, log = Log Perhubungan, hasil = Minit Kerja (dengan cop getah merah), sejarah = Buku Log Aktiviti.

Backend: FastAPI, endpoint `POST /api/execute` dan `GET /api/history` (polling 10s). Frontend **diservis oleh backend** — tiada build step.

---

## 1. GUARDRAILS — BACA DAN PATUHI SEBELUM TULIS SATU BARIS KOD

**Dilarang sama sekali (jangan buat walau atas sebab apa):**
- Jangan hardcode warna hex baru di luar `tokens.css`. Semua warna WAJIB guna CSS variable sedia ada (`--paper`, `--card`, `--ink`, `--ink-soft`, `--ink-faint`, `--rule`, `--rule-soft`, `--stamp`, `--green`, `--green-soft`).
- Jangan tambah gradient, glassmorphism/`backdrop-filter`, glow/`box-shadow` berwarna.
- Jangan tambah "dark mode navy" generik — jika buat dark mode, ia mesti kekal dalam bahasa visual dokumen pejabat (kertas gelap, bukan sci-fi).
- Jangan tambah framework CSS (Tailwind dsb). Vanilla CSS sahaja. Satu-satunya dependency luar dibenarkan: Google Fonts (IBM Plex).
- Jangan tambah font selain IBM Plex Sans Condensed / IBM Plex Sans / IBM Plex Mono.
- `border-radius` maksimum 3px di seluruh UI.
- Jangan ubah ID elemen yang jadi kontrak dengan backend tanpa kelulusan saya dahulu: `terminal`, `historyBody`, `userPrompt`, `modelSelect`, `sendBtn`, `resultBox`, `agentBadge`, `speedBadge`, `finalOutput`, `totalTasks`, `completedTasks`, `tarikh`, `refNo`. Ubah salah satu ID ini = wajib beritahu saya (kena selaras dengan `main.py` di backend).
- Jangan buang atau lemahkan `escapeHtml()` / `textContent` untuk sebarang data dari server — ini pembaikan XSS dari audit keselamatan Julai 2026 (`docs/development/audit-report-2026-07.md`). Sebarang HTML string baru daripada data server MESTI melalui `escapeHtml()`.
- Jangan buang `:focus-visible` outline 2px `--stamp` pada mana-mana elemen interaktif.
- Jangan abaikan `prefers-reduced-motion` — semua animation/transition baru mesti hormati setting ini.
- Copywriting UI dalam Bahasa Melayu, register pejabat rasmi tapi mesra (panggilan pengguna kekal "Bos"). Butang nyatakan tindakan sebenar (cth: "Hantar Arahan ke Claudia"), bukan generik "Submit".
- **Jangan install dependency baru, jangan merge, jangan deploy** tanpa pengesahan saya dahulu. Setiap push ke `main` auto-deploy (force push) ke Hugging Face Spaces — sebarang perubahan MESTI diuji tempatan dulu.
- Edit yang bersasar (targeted edit) diutamakan berbanding refactor besar-besaran, melainkan saya arah sebaliknya.

---

## 2. STRUKTUR KERJA — FASA BERURUTAN (jangan lompat fasa)

Antigravity kerja satu fasa pada satu masa. Selesai satu fasa → stop → tunggu review/confirm saya sebelum ke fasa seterusnya. Jangan gabung fasa dalam satu commit/PR.

### FASA 0 — Audit Baseline (WAJIB dulu, tiada perubahan kod)
1. Baca `frontend/README.md`, `docs/frontend/dashboard-design.md`, dan `docs/development/audit-report-2026-07.md` sepenuhnya.
2. Jalankan dashboard tempatan (`cd backend && python -m src.main`, buka `http://localhost:7860`) dan sahkan ia berfungsi seperti sedia ada.
3. Laporkan kepada saya: (a) sebarang percanggahan antara kod sebenar dan dokumentasi di atas, (b) sebarang isu keselamatan/aksesibiliti yang masih ada selepas audit Julai 2026, disusun ikut severity (Critical → High → Medium → Low).
4. **Checkpoint:** tunggu saya semak laporan sebelum sambung ke Fasa 1.

### FASA 1 — Dark Mode Toggle
- Tambah token warna gelap baharu di `tokens.css` (guna prinsip sama: satu aksen `--stamp` sahaja, tiada navy generik — reka sebagai "kertas gelap/dokumen malam", bukan tema sci-fi).
- Toggle disimpan state di JS (bukan localStorage — rujuk sekatan storan di bawah), atau `data-theme` attribute pada `<html>`.
- Semua komponen sedia ada (`.card`, `.btn-stamp`, `.cop`, `.chip`, `.log-line`) mesti berfungsi betul dalam kedua-dua mod.
- **Checkpoint:** demo/screenshot kedua-dua mod sebelum saya luluskan.

### FASA 2 — Component Library Extraction
- Asingkan komponen berulang (`.card`, `.btn-stamp`, `.cop`, `.chip`) menjadi seksyen jelas dalam CSS dengan komen dokumentasi ringkas di atas setiap komponen (guna, kontrak class, contoh).
- Tiada perubahan visual — ini refactor struktur CSS sahaja, bukan redesign.
- **Checkpoint:** diff CSS untuk semakan saya sebelum sambung.

### FASA 3 — Internationalization (i18n)
- Cadangkan pendekatan (contoh: `data-i18n` attribute + kamus JS mudah, tanpa library luaran) — bentangkan cadangan kepada saya dahulu sebelum laksana, sebab ini keputusan seni bina.
- Bahasa Melayu kekal sebagai default/bahasa utama.
- **Checkpoint:** saya luluskan pendekatan sebelum implementasi penuh.

### FASA 4 — PWA Support
- Tambah `manifest.json` + service worker asas (cache static assets sahaja buat masa ini, bukan offline data).
- Jangan ubah tingkah laku polling `GET /api/history` (10s).
- **Checkpoint:** sahkan install prompt & manifest berfungsi di Chrome/Edge sebelum sambung.

### FASA 5 — Offline Capability
- Hanya mula selepas Fasa 4 diluluskan. Bentangkan skop (apa yang perlu berfungsi offline vs tidak) kepada saya dahulu — jangan andaikan skop sendiri.

---

## 3. SEKATAN TEKNIKAL KHUSUS

- **Storan data**: jangan guna `localStorage`/`sessionStorage` untuk apa-apa state kritikal tanpa berbincang dengan saya dulu — nyatakan sebab dan fallback jika perlu.
- **Tiada build step** kekal sebagai keperluan (no bundler, no npm build) melainkan saya secara eksplisit arah sebaliknya untuk projek v2.
- Semua kod output mesti **lengkap dan sedia copy-paste** — jangan tinggalkan placeholder atau `// TODO: implement`.

---

## 4. KRITERIA PENERIMAAN (setiap fasa)

- Tiada regresi pada fungsi sedia ada (`executeTask`, `fetchHistory`, `addLog`, polling).
- Responsive kekal: 2 kolum → 1 kolum di bawah 960px; roster 4→2→1; jadual dibungkus `.ledger-wrap` dengan `overflow-x: auto`.
- WCAG AA contrast dikekalkan pada semua token warna baharu.
- Tiada console error/warning baharu di DevTools.

---

**Nota untuk Antigravity:** Ikut struktur ini secara berurutan. Jangan mula fasa seterusnya tanpa pengesahan saya. Jika tidak pasti tentang sebarang keputusan seni bina (bukan sekadar kod), tanya dulu — jangan andaikan.
