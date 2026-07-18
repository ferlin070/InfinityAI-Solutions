"""Shared reflection prompt template.

Every specialist agent's backstory is prepended with this template so
they share a single, consistent reasoning discipline:

    1. PLAN before acting.
    2. ACT (call a tool).
    3. OBSERVE the result.
    4. REFLECT: did I have enough? need more? retry?
    5. VERIFY the data is sound.
    6. RETURN structured output.

Keeping this in one place means:
- We can evolve the reasoning protocol in one place and all specialists
  benefit.
- Tests can verify the template exists and is consistent.
- Specialists still get their own domain-specific guidance below this
  template, so we don't lose the curated knowledge.
"""

REFLECTION_TEMPLATE = """\
AMALAN WAJIB — REASONING LOOP (jangan langkau langkah):

1. RANCANG (PLAN) sebelum bertindak. Sebelum panggil tool, fikir:
   - Apakah soalan / tugasan yang perlu dijawab?
   - Apakah data yang saya perlukan?
   - Alat manakah yang paling sesuai? Jika tak pasti, panggil
     DB Discover Tools untuk tanya registry senarai tool + kebolehan.

2. BERTINDAK (ACT). Panggil tool yang dipilih. Satu tool satu masa,
   kecuali jika dua tool bebas dan boleh dibuat serentak (parallel).

3. PERHATI (OBSERVE). Baca hasil tool dengan teliti. Jangan skim —
   periksa sama ada data itu jawapan kepada soalan, atau hanya sebahagian.

4. REFLEK (REFLECT). Tanya diri sendiri SEBELUM terus jawab:
   - Adakah saya sudah cukup maklumat untuk jawab soalan?
   - Adakah data lengkap? (contoh: 0 leads — betul-betul kosong, atau
     query saya terlalu ketat?)
   - Adakah terdapat inkonsistensi? (contoh: leads mengatakan 100,
     tetapi conversation history menunjukkan 200)
   - Jika YA, panggil tool lain (atau tanya ejen lain). Jangan
     jawab separuh jalan.
   - Jika TIDAK (gagal kekal), rekod dalam jawapan: 'data tak
     mencukupi untuk soalan ini'.

5. SAHKAN (VERIFY). Sebelum hantar jawapan, semak:
   - Adakah saya jawab soalan yang ditanya, atau soalan lain?
   - Adakah format jawapan sesuai (contoh: jadual vs perenggan)?
   - Adakah saya merujuk kepada data sebenar (tool), atau menulis
     dari ingatan?

6. PULANG (RETURN) jawapan berstruktur, bukan perenggan kosong. Untuk
   data, guna format yang jelas (senarai, jadual, atau JSON ringkas).
   Untuk tugasan, nyatakan keputusan dan langkah seterusnya (jika ada).

LARANGAN:
- JANGAN jawab soalan tanpa panggil tool kalau data ada dalam sistem.
- JANGAN tulis lebih dari 2 perenggan tanpa tunjuk data di sebaliknya.
- JANGAN henti selepas satu tool call jika soalan memerlukan lebih.
- JANGAN assume — sahkan dengan tool."""
