# Design System Dashboard — "Dokumen Pejabat"

> **Sejarah, bukan reka bentuk semasa (ditanda 2026-07-19):** dashboard
> React sekarang (`frontend-react/`) guna palet indigo/gold/graphite
> (commit `e7cbce6`, "UI/UX upgrade"), bukan tema "dokumen pejabat" IBM Plex
> yang diterangkan di bawah. `index.html` yang dirujuk di sini juga dah tak
> wujud pada laluan tu — lihat `frontend-react/index.html` +
> `frontend-react/src/App.jsx` untuk struktur sebenar. Dokumen ni dikekalkan
> sebagai rekod sejarah reka bentuk asal; jangan ikut token di bawah untuk
> kerja UI baru tanpa sahkan dulu dengan `frontend-react/src/index.css` /
> `tailwind.config.js`.

Panduan rekaan untuk `index.html` (versi lama, vanilla HTML/CSS/JS — lihat nota di atas). Sesiapa yang menambah UI baru **mesti** ikut token dan peraturan di sini supaya dashboard kekal satu identiti.

## Konsep

Sistem ini ialah *pejabat maya* sebuah syarikat — 8 staf AI, dan pengguna ialah bos yang memberi arahan kerja. Maka antara muka mengambil bahasa visual **dokumen pejabat rasmi Malaysia**, bukan "sci-fi mission control":

- Input tugasan = **Borang Arahan Kerja** (dengan No. Rujukan, Kepada, Butiran)
- Senarai agent = **Senarai Bertugas** (kad staf bernombor)
- Log masa nyata = **Log Perhubungan** (buku log dengan garis margin merah)
- Hasil kerja = **Minit Kerja** (dengan cop getah merah)
- Sejarah = **Buku Log Aktiviti** (jadual ledger)

**Elemen tandatangan** (satu sahaja, jangan tambah lagi): estetika *cop getah* — badge bersempadan merah 2px dengan putaran -1.2° pada kepala Minit Kerja, dan garis margin merah menegak pada Log Perhubungan.

## Token Warna

Semua warna WAJIB melalui CSS variables di `:root` — jangan hardcode hex baru.

| Token | Hex | Guna untuk |
|---|---|---|
| `--paper` | `#EFF2F0` | Latar halaman (kertas ledger sejuk) |
| `--card` | `#FBFCFB` | Latar kad/borang |
| `--ink` | `#1D2A32` | Teks utama, butang, garis tebal (dakwat pen) |
| `--ink-soft` | `#4E6069` | Teks sekunder |
| `--ink-faint` | `#7E929B` | Label kecil, placeholder, metadata |
| `--rule` | `#C7D2D2` | Sempadan kad, garis jadual |
| `--rule-soft` | `#DFE6E5` | Garis halus (baris textarea, baris jadual) |
| `--stamp` | `#B23A2C` | **Aksen tunggal**: cop, ralat, fokus. Guna berjimat |
| `--green` | `#2E6B4E` | Status berjaya/selesai sahaja |
| `--green-soft` | `#E0EAE2` | Latar chip status berjaya |

Larangan: tiada gradient, tiada glassmorphism/`backdrop-filter`, tiada glow/`box-shadow` berwarna, tiada dark mode navy. `border-radius` maksimum 3px (dokumen bersudut tajam).

## Tipografi

Satu keluarga sahaja — **IBM Plex** (Google Fonts), tiga peranan:

| Peranan | Font | Guna untuk |
|---|---|---|
| Display | IBM Plex Sans Condensed 600/700, UPPERCASE, letter-spacing .12–.18em | Tajuk halaman, kepala seksyen/borang, butang |
| Badan | IBM Plex Sans 400/600 | Teks kandungan, borang |
| Data | IBM Plex Mono 400/500 | Angka, masa, no. rujukan, log, nama model |

Peraturan: angka & data teknikal sentiasa Mono; tajuk sentiasa Condensed caps; jangan import font lain.

## Komponen

- **`.card`** — bekas asas: latar `--card`, sempadan 1px `--rule`, radius 3px, bayang 1px kelabu neutral.
- **`.card-head` + `.card-title`** — kepala setiap kad, condensed caps 13px dengan nota mono kanan (`.card-note`).
- **`.btn-stamp`** — butang utama: blok dakwat penuh, condensed caps, tekan turun 1px pada `:active`. Satu sahaja per borang.
- **`.cop`** — badge cop getah merah (sempadan 2px, putaran -1.2°). Untuk kepala hasil/status penting sahaja.
- **`.chip`** — status kecil dalam jadual (mono 10px, latar `--green-soft`).
- **`.log-line`** + `.log-success/.log-error/.log-agent` — baris log mono 12px, prefiks masa (HH:MM) melalui `addLog()`.
- **Textarea borang** — latar bergaris (repeating-linear-gradient 28px, `background-attachment: local`) dengan `line-height: 28px` supaya teks duduk atas garisan.

## Peraturan Kandungan (copywriting UI)

- Bahasa Melayu, register pejabat rasmi tapi mesra ("Bos" dikekalkan sebagai panggilan pengguna).
- Butang menyatakan tindakan sebenar: "Hantar Arahan ke Claudia", bukan "Submit".
- Empty state memberi arah: terangkan apa akan berlaku, bukan sekadar "tiada data".
- Ralat menyatakan apa berlaku + apa perlu dibuat ("Sambungan terputus. Cuba hantar semula.") — tanpa jargon teknikal.
- Nombor staf (01–08) adalah ID staf — bermakna, bukan hiasan. Jangan tambah penomboran kosmetik di tempat lain.

## Aksesibiliti & Teknikal

- `:focus-visible` outline 2px `--stamp` pada semua elemen interaktif — jangan buang.
- `prefers-reduced-motion` dihormati (semua transition/animation dimatikan).
- Responsif: 2 kolum → 1 kolum di bawah 960px; roster 4→2→1; jadual dibungkus `.ledger-wrap` dengan `overflow-x: auto`.
- **Tiada framework CSS** — Tailwind CDN telah dibuang (tidak sesuai untuk production). CSS vanila sahaja, dalam `<style>` di `index.html`. Satu-satunya dependency luaran: Google Fonts.
- **Keselamatan (jangan regres):** semua data dari server mesti melalui `escapeHtml()` jika dimasukkan via template string, atau guna `textContent`/`createTextNode` (rujuk `addLog()`). Ini pembaikan XSS dari [audit-report-2026-07.md](../development/audit-report-2026-07.md).

## Kontrak dengan Backend (jangan ubah tanpa ubah main.py)

ID elemen yang digunakan JavaScript: `terminal`, `historyBody`, `userPrompt`, `modelSelect`, `sendBtn`, `resultBox`, `agentBadge`, `speedBadge`, `finalOutput`, `totalTasks`, `completedTasks`, `tarikh`, `refNo`. Endpoint: `POST /api/execute`, `GET /api/history` (polling 10s).
