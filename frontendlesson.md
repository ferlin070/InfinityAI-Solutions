# Frontend & Deployment — Pengajaran Sebenar (bukan teori)

Dokumen ini disusun daripada bug **sebenar** yang dijumpai dan dibetulkan dalam
sistem production InfinityAI Solutions (Julai 2026) — setiap satu disahkan
melalui log/API Railway sebenar atau ujian automatik, bukan teka. Tujuannya
untuk elak pola yang sama berulang.

---

## 1. Jangan hardcode status UI — sentiasa derive dari data backend sebenar

**Apa yang jadi:** `Settings.jsx` papar **"Connected & Active"** (hijau, ikon
WiFi) untuk *setiap* nombor WhatsApp dalam senarai — teks tu terus ditulis
dalam JSX, langsung tak check `ch.status` yang backend hantar. Akibatnya,
nombor yang baru sahaja diklik "Sambung Nombor Baru" (status sebenar:
`pending_qr`, malah kemudiannya `disconnected` sebab bug Chrome — lihat §4)
kelihatan "Connected & Active" walhal tak pernah connect langsung. `Dashboard.jsx`
ada bug serupa: `channels.length > 0` (row wujud dalam DB) disamakan dengan
"connected", dan ada bug copy-paste lain — teks placeholder input telefon
(`+60123456789`) tersalah guna sebagai label "nombor yang connect".

**Pengajaran:** Kalau backend hantar field status (`status`, `state`,
`connected`, dll), UI **mesti** derive paparan daripada field tu — jangan
tulis teks/warna hardcoded "sebab logiknya sepatutnya begitu". Test dengan
data yang BUKAN happy-path (status `pending_qr`, `disconnected`, list kosong)
sebelum anggap ia betul.

## 2. 401 handling dalam SPA tanpa hash router — reload betul-betul, jangan tukar hash je

**Apa yang jadi:** `api.js` buat `window.location.href = '#login'` bila dapat
401. Tapi `App.jsx` **bukan** hash-routed — dia decide Login vs Dashboard
semata-mata daripada `isAuthenticated` state yang di-check SEKALI sahaja masa
`verifyAuth()` di awal mount. Tukar hash URL tak buat apa-apa — `isAuthenticated`
kekal `true`, user still "nampak" logged in, tapi setiap panggilan API lepas
tu senyap-senyap return `null`/kosong. Ini punca sebenar aduan "saya bagi
arahan pada AI, tukar page, balik — semua dah hilang" — bukan data hilang,
tapi session dah expired dan app tak pernah bagitahu user, cuma papar kosong.

**Pengajaran:** Bila fix "redirect ke login on 401", **betul-betul test** ia
navigate — jangan anggap tukar `window.location.href` cukup dalam SPA yang
tak pakai router. Guna `window.location.reload()` (atau router betul) supaya
state re-check berjalan. **Tapi** hati-hati — endpoint yang MEMANG sepatutnya
401 bila belum login (contoh `/api/me` yang dipanggil `verifyAuth()` untuk
tanya "adakah saya dah login?") mesti **dikecualikan** daripada logik reload
ni, atau setiap pelawat baru akan terperangkap infinite-reload-loop.

## 3. Session/state yang perlu survive restart JANGAN simpan dalam memori proses sahaja

**Apa yang jadi:** `core/sessions.py` simpan token login dalam
`ACTIVE_SESSIONS = {}` — dict Python biasa dalam memori. Setiap kali backend
restart (deploy baru, crash, Railway respawn — kerap berlaku semasa
development aktif), dict tu kosong semula, dan **SEMUA** session sah terus
invalid — semua orang logout serentak. Ini punca sebenar aduan "setiap kali
saya refresh, saya kena login semula".

**Pengajaran:** Apa-apa state yang user harap "kekal" (session, cache
penting, dll) mesti disimpan di tempat yang survive restart — DB
(Supabase), atau token **stateless** yang self-verifying (HMAC-signed,
disahkan melalui signature+masa, bukan carian dalam dict proses). Fix
sebenar: `create_session()`/`verify_session()` kini stateless — token sendiri
mengandungi timestamp + nonce rawak + signature HMAC, jadi sah tanpa perlu
proses yang sama yang cipta dia.

## 4. Nama environment variable mesti PADAN betul-betul dengan apa yang library baca

**Apa yang jadi:** Dockerfile gateway WhatsApp set `CHROMIUM_PATH=/usr/bin/chromium`
selepas install Chromium — kedengaran munasabah, tapi **Puppeteer/whatsapp-web.js
langsung tak baca nama variable tu**. Nama sebenar yang Puppeteer recognize
ialah `PUPPETEER_EXECUTABLE_PATH`. Akibatnya, Chromium terpasang dalam
container, tapi setiap sesi WhatsApp gagal initialize dengan ralat "Could not
find Chrome" — disahkan terus daripada log deployment Railway sebenar.

**Pengajaran:** Bila set env var untuk configure library pihak ketiga
(Puppeteer, dll), **check dokumentasi library tu** untuk nama variable yang
tepat — jangan reka nama yang "nampak logik". Lagi selamat: hantar config tu
terus dalam code (`executablePath: process.env.PUPPETEER_EXECUTABLE_PATH`)
supaya ia eksplisit dan mudah nampak dalam code review, bukan bergantung
semata-mata pada env var auto-detection yang senyap kalau salah nama.

## 5. Jangan buat panggilan blocking terus dalam route `async def`

**Apa yang jadi:** `wa_routes.py` panggil `requests.post(...)` (blocking,
synchronous) terus dalam `async def` FastAPI route, tanpa `asyncio.to_thread`.
Server ni satu proses, satu event loop — bila satu panggilan WhatsApp
gateway tersekat (contoh: gateway lambat/tak reachable), **SELURUH server**
beku untuk tempoh tu, termasuk request lain yang tiada kaitan (chat AI pun
ikut hang sekali).

**Pengajaran:** Dalam `async def` FastAPI, apa-apa panggilan I/O yang bukan
`await`-able secara native (library `requests` biasa, bukan `httpx.AsyncClient`)
mesti dibalut `await asyncio.to_thread(fn, ...)`. Kalau tak, satu request
perlahan boleh bunuh keseluruhan server buat semua orang.

## 6. Sahkan repo/branch mana yang BETUL-BETUL disambung ke platform deploy

**Apa yang jadi:** Berminggu-minggu fix dihantar ke `Reef-hash/InfinityAI-Solutions`
— tapi Railway sebenarnya build daripada **`ferlin070/InfinityAI-Solutions`**,
fork yang berlainan sepenuhnya. Tiada satu fix pun live sehingga ini disedari
(disahkan terus melalui Railway API — deployment `meta.repo` tunjuk fork
yang salah).

**Pengajaran:** Bila "fix dah push tapi production still rosak", jangan
anggap salah kod — **sahkan dulu repo/branch mana yang platform deploy
(Railway/Vercel/dll) betul-betul guna**. Boleh check terus dalam dashboard
platform (Settings → Source), atau melalui API platform tu.

## 7. Kalau agent/tool framework (contoh CrewAI) "sepatutnya" panggil tool — VERIFY, jangan percaya sahaja

**Apa yang jadi:** Setiap agent (Maya, Hakim, Danish) ada tools terpasang
(`tools=[...]`) dan kod nampak betul — tapi CrewAI punya executor sebenar
(`crew_agent_executor.py`) **tak pernah** hantar `tools`/`available_functions`
ke custom LLM adapter, hanya `from_task`. Bermakna langsung tiada tool yang
pernah dipanggil, walaupun kod adapter untuk handle tool-call memang wujud
dan betul — ia cuma tak pernah terima apa-apa untuk di-loop.

**Pengajaran:** Bila integrate dengan framework (agent framework, orchestration
library, dll), **jangan percaya dokumentasi/nama parameter sahaja** — test
end-to-end dengan scripted/mocked response yang benar-benar memaksa laluan
tool-call, dan confirm tool tu betul-betul dipanggil (contoh: check
side-effect sebenar, bukan cuma "tiada ralat"). "Tiada error" tak bermakna
"berfungsi".

---

## Cara elak ni semua ulang: checklist ringkas sebelum "siap"

- [ ] UI status/badge — check ia derive daripada field backend sebenar, bukan hardcoded
- [ ] Auth/401 handling — betul-betul test navigate ke login (bukan cuma tengok kod)
- [ ] Apa-apa state yang perlu "ingat" — confirm ia survive restart proses
- [ ] Env var untuk library luar — check dokumentasi rasmi nama variable
- [ ] Panggilan I/O blocking dalam async route — mesti `asyncio.to_thread`
- [ ] Deploy — confirm repo/branch yang platform guna sama dengan yang awak push
- [ ] Tool/function-calling dengan agent framework — test end-to-end, jangan anggap "sepatutnya jalan"
