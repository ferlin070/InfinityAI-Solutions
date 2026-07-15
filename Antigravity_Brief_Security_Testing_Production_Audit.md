# ANTIGRAVITY TASK BRIEF
## Security, Testing & Production-Readiness Audit (Generik — Semua Webapp)

**Jenis tugasan:** Audit & Remediation (bukan feature baru)
**Mod:** Diagnostik dahulu, fix kemudian — JANGAN terus ubah kod sebelum laporan awal diberikan
**Skop:** Codebase sedia ada di repo ini (webapp — sesuaikan stack ikut projek: React/Vite/Tailwind/Firebase, Electron/React/TS, dsb.)

---

## 0. GUARDRAILS (WAJIB PATUH)

1. **Jangan refactor besar-besaran.** Fix mesti minimal, bertarget, dan tidak mengubah tingkah laku fungsi sedia ada kecuali ia memang bug/security hole.
2. **Jangan padam atau tulis semula fail secara total** — guna targeted edit sahaja.
3. **Setiap perubahan mesti disertakan sebab (kenapa ia security/testing/production risk).**
4. **Jangan install dependency baru** tanpa nyatakan dalam laporan kenapa ia perlu, dan dapatkan pengesahan dahulu jika ia menambah attack surface (contoh: package yang handle auth, payment, atau file upload).
5. **Jangan expose sebarang secret/API key/credential dalam log, console, atau commit.** Jika jumpa hardcoded secret sedia ada, flag sebagai CRITICAL — jangan padam terus tanpa laporan (mungkin perlu rotate key dahulu).
6. **Output akhir mesti dalam 2 bahagian:** (A) Laporan Audit (markdown), (B) Fix yang benar-benar dilaksanakan — dipisahkan ikut severity, bukan satu commit besar bercampur.
7. **Jika ragu sama ada sesuatu itu bug atau by-design**, tanya dalam laporan (bahagian "Perlu Pengesahan"), jangan andaikan dan terus ubah.

---

## 1. OBJEKTIF

Buat audit menyeluruh ke atas sistem ini untuk pastikan ia **selamat (secure)**, **stabil (tested)**, dan **sedia untuk production**, mengikut piawaian coding semasa (2026) untuk stack yang digunakan. Hasil akhir: laporan bertulis + senarai fix yang telah dilaksanakan, disusun ikut keutamaan (Critical → High → Medium → Low).

---

## 2. SKOP AUDIT

### A. SECURITY

- **Authentication & Authorization**
  - Semak session/token handling (expiry, refresh, storage — jangan simpan token sensitif dalam `localStorage` jika boleh dielak; guna `httpOnly` cookie atau secure storage yang sesuai).
  - Role-based access control (admin/staff/user) — pastikan setiap route/API endpoint benar-benar enforce role di **server-side**, bukan hanya sorok di UI.
  - Firebase/Supabase Security Rules (jika berkaitan) — semak `firestore.rules` / `storage.rules` / RLS policies, pastikan tiada rule yang terlalu longgar (`allow read, write: if true`).

- **Input Validation & Injection**
  - Semua input dari user (form, query param, QR code payload, file upload) mesti disahkan di server-side, bukan client-side sahaja.
  - Semak risiko XSS (unsanitized `dangerouslySetInnerHTML`, innerHTML), SQL/NoSQL injection, dan command injection jika ada backend script.
  - Semak file upload (jika ada) — had saiz, jenis fail (whitelist bukan blacklist), dan scan lokasi simpanan.

- **Secrets & Configuration**
  - Pastikan tiada API key/secret hardcoded dalam source code atau commit history.
  - Semak `.env` betul-betul di-`.gitignore`, dan `.env.example` tidak bocor nilai sebenar.
  - Semak environment variables yang expose ke client bundle (contoh: Vite `VITE_` prefix) — pastikan tiada secret sensitif dihantar ke browser.

- **Dependency & Supply Chain**
  - Jalankan `npm audit` (atau setara) dan senaraikan vulnerability mengikut severity.
  - Semak dependency yang sudah deprecated/unmaintained.

- **Transport & Headers**
  - Pastikan HTTPS enforced.
  - Semak security headers asas (CSP, X-Content-Type-Options, X-Frame-Options) jika deployment platform membenarkan konfigurasi ini.
  - CORS policy — pastikan tidak `*` secara sembarangan untuk endpoint yang handle data sensitif.

- **Rate Limiting & Abuse Prevention**
  - Semak sama ada endpoint public (contoh: submit feedback, QR scan) terdedah kepada spam/abuse tanpa rate limiting atau captcha.

### B. TESTING

- Semak liputan testing sedia ada (unit/integration/e2e) — jika tiada test framework langsung, laporkan sebagai gap, cadangkan setup minimum (contoh: Vitest untuk React/Vite, Playwright untuk e2e).
- Tuliskan/tambah test untuk:
  - Fungsi critical path (contoh: submission flow, auth flow, role-based redirect).
  - Edge case yang berpotensi crash (empty state, network failure, offline mode).
- Manual smoke-test checklist untuk flow utama sistem (senaraikan langkah demi langkah supaya boleh diulang oleh manusia jika perlu).
- Semak error handling — pastikan tiada `try/catch` kosong yang "senyapkan" error penting, dan tiada unhandled promise rejection.

### C. PRODUCTION READINESS

- Semak build process (`npm run build`) — pastikan tiada warning/error yang diabaikan.
- Semak console.log/debug statement yang tertinggal dalam kod production.
- Semak loading state & error state UI untuk setiap network call (jangan biarkan skrin blank/hang tanpa feedback kepada user).
- Semak responsiveness asas (mobile/tablet) jika sistem web-facing untuk end-user awam.
- Semak dark mode / multilingual (jika berkaitan) tidak pecah bila toggle — tiada text overflow, tiada missing translation key.
- Semak performance asas: bundle size tidak melampau, imej dioptimumkan, tiada N+1 query/read yang boleh bebankan Firestore/Supabase read quota.
- Semak logging & monitoring — ada cara untuk kesan error di production (contoh: Sentry, atau minimum console error logging yang boleh disemak).

### D. CODING STANDARDS (SEMASA)

- Konsistensi struktur folder & naming convention.
- TypeScript strictness (jika projek TS) — semak `any` yang boleh dielak, unused variables/imports.
- ESLint/Prettier config dijalankan tanpa error.
- Komponen React ikut best practice semasa (hooks rules, tiada prop-drilling melampau tanpa context/state management yang jelas, key prop betul dalam list rendering).

---

## 3. FORMAT LAPORAN (WAJIB)

Sediakan laporan dalam fail berasingan `AUDIT_REPORT.md` dengan struktur:

```
# Audit Report — [Nama Sistem]
Tarikh: [tarikh]

## Ringkasan Eksekutif
(3-5 ayat — status keseluruhan, adakah selamat untuk production sekarang atau tidak)

## CRITICAL (mesti fix sebelum production)
- [Isu] — [Lokasi fail:baris] — [Kesan] — [Status: Fixed/Perlu Pengesahan]

## HIGH
...

## MEDIUM
...

## LOW / Cadangan Penambahbaikan
...

## Perlu Pengesahan Kaihara
(Isu yang Antigravity tidak pasti sama ada bug atau by-design)

## Fix Yang Telah Dilaksanakan
(Senarai fail yang diubah + ringkasan perubahan)
```

---

## 4. URUTAN KERJA

1. Scan keseluruhan codebase — jangan ubah apa-apa lagi.
2. Hasilkan draf `AUDIT_REPORT.md` (Critical & High dahulu).
3. Untuk isu **CRITICAL** dan **HIGH** — terus fix dan catat dalam laporan.
4. Untuk isu **MEDIUM/LOW** — senaraikan sahaja sebagai cadangan, jangan fix melainkan diarah.
5. Serahkan laporan lengkap + senarai fail yang diubah untuk semakan Kaihara sebelum di-merge/deploy.

---

**Nota:** Brief ini generik dan boleh digunakan untuk mana-mana webapp (Online Feedback System, EZOffice, atau projek lain). Sebelum hantar kepada Antigravity, isi placeholder `[Nama Sistem]` dan nyatakan stack sebenar (contoh: "React/Vite + Tailwind + Firebase" atau "Electron + React 19 + TypeScript") supaya Antigravity fokus kepada checklist yang relevan sahaja.
