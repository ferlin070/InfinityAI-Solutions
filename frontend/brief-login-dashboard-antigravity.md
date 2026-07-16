# BRIEF ANTIGRAVITY — Login Page + Dashboard
## Projek: InfinityAI-Solutions (AI Command Center)
Repo: https://github.com/ferlin070/InfinityAI-Solutions

---

## 0. KONTEKS

Dashboard sedia ada (`frontend/src/index.html`) **tiada mekanisme login** — buat masa ini sesiapa yang akses `http://localhost:7860` terus nampak dashboard penuh (borang arahan kerja ke Claudia, log, sejarah). Tugasan ini adalah untuk **tambah Login Page sebagai pintu masuk**, dan pastikan Dashboard sedia ada berfungsi sebagai skrin selepas log masuk sahaja.

Ini bukan redesign — Login Page mesti sambung terus daripada design system "Dokumen Pejabat" yang sama supaya kelihatan satu produk, bukan dua UI berlainan.

Struktur sedia ada (JANGAN buang, tambah sahaja):
```
frontend/src/
├── index.html
├── css/ (tokens.css, letterhead.css, forms.css, table.css, layout.css, responsive.css)
└── js/  (main.js, api.js, logger.js, history.js, ui.js)
```

---

## 1. GUARDRAILS — WAJIB PATUH

**Reka bentuk (tak boleh langgar):**
- Login Page WAJIB guna `tokens.css` sedia ada — jangan cipta palet warna baharu. Warna: `--paper` latar, `--card` untuk kad borang, `--ink`/`--ink-soft` teks, `--stamp` (#B23A2C) sebagai satu-satunya aksen (butang utama, ralat, fokus).
- Font kekal IBM Plex sahaja (Condensed untuk tajuk/butang, Sans untuk body, Mono untuk data/ref no).
- `border-radius` maksimum 3px. Tiada gradient, glassmorphism, `box-shadow` berwarna.
- Bahasa borang: Bahasa Melayu register pejabat rasmi ("Log Masuk", "Nombor Kakitangan"/"E-mel", "Kata Laluan" — bukan "Login"/"Password" dalam UI).
- Konsep "Borang Rasmi": Login Page boleh guna bahasa visual sama seperti Borang Arahan Kerja sedia ada (kad bersempadan 1px `--rule`, tajuk condensed caps, no. rujukan/tarikh di penjuru jika berkaitan).
- Butang utama guna class `.btn-stamp` sedia ada — jangan cipta butang gaya baharu.

**Keselamatan (kritikal — jangan regres):**
- **JANGAN simpan password dalam plaintext di mana-mana** (bukan di frontend, bukan di localStorage/sessionStorage sama sekali).
- Token sesi (session/JWT) — cadangkan pendekatan penyimpanan token kepada saya dahulu (httpOnly cookie disyorkan berbanding localStorage untuk elak XSS token theft) SEBELUM implementasi. Ini keputusan seni bina, bukan keputusan kod — jangan andaikan sendiri.
- Semua input pengguna (e-mel, password field) — pastikan tiada auto-render sebagai HTML di mana-mana (guna `textContent`/`value`, bukan `innerHTML`).
- Attribute `autocomplete="username"` / `autocomplete="current-password"` pada field yang betul (bantu password manager, bukan isu keselamatan tapi UX asas).
- Jangan hantar password dalam URL/query string — mesti dalam request body (POST).
- Rate-limiting/lockout selepas cubaan gagal berulang — ini **backend punya kerja**, tapi frontend perlu papar mesej ralat yang sesuai (rujuk peraturan mesej ralat di bawah), jangan bina logic lockout di frontend.

**Kontrak dengan backend:**
- Endpoint login BELUM wujud di `main.py` — Antigravity perlu **cadangkan** kontrak endpoint (`POST /api/login` — payload, response shape) kepada saya untuk kelulusan SEBELUM tulis kod JS yang panggil endpoint tersebut.
- Jangan ubah ID elemen sedia ada yang jadi kontrak dashboard: `terminal`, `historyBody`, `userPrompt`, `modelSelect`, `sendBtn`, `resultBox`, `agentBadge`, `speedBadge`, `finalOutput`, `totalTasks`, `completedTasks`, `tarikh`, `refNo`.
- Mesej ralat ikut peraturan sedia ada: nyatakan apa berlaku + apa perlu dibuat, tanpa jargon teknikal (cth: "E-mel atau kata laluan salah. Sila cuba lagi." bukan "401 Unauthorized").

**Proses:**
- Jangan install dependency/library auth pihak ketiga (Auth0, Firebase Auth, dll) tanpa kelulusan saya — bincang dulu, sebab ini keputusan seni bina + kos.
- Jangan merge/deploy tanpa pengesahan saya. Auto-deploy ke Hugging Face Spaces bermakna sebarang silap terus live.
- Edit bersasar diutamakan berbanding refactor besar.

---

## 2. FASA KERJA — BERURUTAN, STOP SELEPAS SETIAP FASA

### FASA 0 — Cadangan Seni Bina (tiada kod dulu)
1. Cadangkan kontrak endpoint `POST /api/login` (payload: e-mel/kata laluan; response: token/session + user info apa yang perlu).
2. Cadangkan kaedah simpan sesi (httpOnly cookie vs token dalam memori JS) berserta sebab.
3. Cadangkan struktur fail baharu (cth: `frontend/src/login.html` + `css/login.css` berasingan, atau reuse `tokens.css` + fail CSS baharu khusus login).
4. **Checkpoint:** hantar cadangan ini kepada saya. Jangan tulis kod sebelum saya luluskan.

### FASA 1 — Login Page (UI sahaja, tanpa logic auth sebenar)
1. Bina `login.html` (atau laluan yang diluluskan Fasa 0) dengan borang: e-mel, kata laluan, butang "Log Masuk" (`.btn-stamp`).
2. Guna komponen sedia ada: `.card` untuk bekas borang, `.card-head`/`.card-title` untuk tajuk, style textarea/input sedia ada dari `forms.css` sebagai asas (adaptasi untuk input password/email jika perlu class baharu — dokumenkan dalam komen CSS).
3. State ralat (kata laluan salah, medan kosong) — guna gaya `--stamp` untuk teks ralat, konsisten dengan gaya ralat sedia ada.
4. Responsive: ikut breakpoint sedia ada (960px, 440px).
5. Aksesibiliti: label eksplisit untuk setiap input, `:focus-visible` outline `--stamp` 2px, boleh navigasi penuh guna keyboard.
6. **Checkpoint:** screenshot/demo UI login (tanpa backend berfungsi lagi) untuk semakan saya.

### FASA 2 — Sambung Login ke Backend + Proteksi Dashboard
1. Sambung borang login ke endpoint yang diluluskan di Fasa 0.
2. Selepas log masuk berjaya → redirect ke dashboard sedia ada (`index.html`).
3. Dashboard mesti check status sesi — jika tiada sesi sah, redirect balik ke `login.html` (proteksi client-side sahaja tidak memadai — sahkan backend juga tolak request tanpa sesi sah di `/api/execute` dan `/api/history`; laporkan kepada saya jika backend belum ada proteksi ini, JANGAN ubah backend sendiri tanpa arahan).
4. Tambah butang "Log Keluar" di dashboard (lokasi cadangkan kepada saya — mungkin dekat letterhead/header) yang clear sesi dan redirect ke login.
5. **Checkpoint:** demo aliran penuh (login gagal, login berjaya, akses dashboard tanpa sesi, log keluar) untuk semakan saya.

### FASA 3 — Kemas Kini Dashboard (jika perlu, selepas Fasa 2 diluluskan)
- Sebarang perubahan pada `index.html` sedia ada berkaitan integrasi login (cth: papar nama pengguna log masuk di header) — nyatakan skop dengan saya dahulu sebelum mula, sebab ini sentuh fail dashboard yang sedang live.

---

## 3. KRITERIA PENERIMAAN

- Tiada regresi pada fungsi dashboard sedia ada (`executeTask`, `fetchHistory`, `addLog`, polling 10s).
- Tiada password/token tersimpan plaintext di mana-mana storan client-side.
- Semua mesej ralat dalam Bahasa Melayu, mesra, tanpa jargon.
- WCAG AA contrast dan `:focus-visible` dikekalkan pada semua elemen baharu.
- Tiada console error/warning baharu.
- Kod lengkap, sedia copy-paste — tiada placeholder atau `// TODO`.

---

**Nota untuk Antigravity:** Mula dengan Fasa 0 SAHAJA. Jangan tulis satu baris kod pun sebelum cadangan seni bina (endpoint contract + kaedah sesi) diluluskan — ini bahagian paling senang jadi lubang keselamatan kalau tergesa-gesa.
