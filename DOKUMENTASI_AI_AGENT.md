# Dokumentasi Sistem AI Agent Command Center

Sistem ini adalah platform orkestrasi multi-agent berbasis AI yang menggunakan **FastAPI** sebagai backend dan **NVIDIA NIM (Llama 3.1 / Kimi)** sebagai otak kecerdasan buatan. Sistem ini dirancang untuk mengotomatisasi tugas-tugas bisnis seperti pemasaran, keuangan, kreatif, dan teknikal.

---

## 1. Gambaran Umum Sistem
Sistem bekerja dengan prinsip "Manager-Worker". Seorang Manajer (Claudia) menerima perintah dari pengguna, menganalisisnya, dan membagi tugas tersebut kepada agen spesialis yang sesuai.

### Komponen Utama:
*   **Backend**: FastAPI (Python)
*   **AI Engine**: NVIDIA NIM API (Llama-3.1-70b / Kimi-k2.6)
*   **Storage**: Google Drive via Google Apps Script (GAS)
*   **Frontend**: HTML5/Tailwind CSS/JS (Single Page Application)

---

## 2. Struktur Agen (The Agents)

Setiap agen memiliki "System Prompt" unik yang menentukan keahlian dan gaya bahasa mereka:

| Nama Agen | Peran | Tanggung Jawab |
| :--- | :--- | :--- |
| **Claudia** | Chief of Staff | Manager; pembagi tugas via format JSON. |
| **Zara** | Finance Expert | Pengiraan bajet, invois, dan laporan kewangan. |
| **Danish** | Content Creator | Penulisan E-book, copywriting, dan konten kreatif. |
| **Aiman** | Marketing Lead | Strategi iklan, branding, dan marketing plan. |
| **Hakim** | System Architect | Coding, debugging, dan dokumentasi teknikal. |
| **Maya** | Sales/CRM | Menapis prospek dan menyediakan sebut harga. |
| **Amelia** | Trainer | Pembuatan modul latihan dan nota edaran. |
| **Adila** | Operations | Laporan harian dan log operasional syarikat. |

---

## 3. Alur Kerja (Workflow)

1.  **Input**: Pengguna memasukkan perintah di dashboard web.
2.  **Orchestration**: 
    *   Perintah dikirim ke **Claudia**.
    *   Claudia membalas dengan struktur JSON: `{"assignments": [{"agent": "ZARA", "task": "..."}]}`.
3.  **Execution**: Sistem memproses setiap tugas secara paralel (jika lebih dari satu agen dipilih).
4.  **Storage**: Hasil kerja dikirim ke Google Drive melalui Google Apps Script.
5.  **Logging**: Setiap aktivitas dicatat dalam `daily_log.json` untuk pemantauan kecepatan dan status.

---

## 4. Panduan Instalasi

### Prasyarat
*   Python 3.9+
*   NVIDIA NIM API Key
*   Google Apps Script Web App URL

### Langkah-langkah:
1.  **Clone Repository** dan masuk ke direktori proyek.
2.  **Install Dependensi**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Konfigurasi Environment**:
    Buat file `.env` dan isi dengan data berikut:
    ```env
    NVIDIA_NIM_API_KEY=your_api_key_here
    GAS_WEB_APP_URL=your_gas_url_here
    ZARA_DRIVE_FOLDER_ID=folder_id_zara
    DANISH_DRIVE_FOLDER_ID=folder_id_danish
    # ... (tambahkan untuk agen lainnya)
    ```
4.  **Menjalankan Aplikasi**:
    ```bash
    python main.py
    ```
    Aplikasi akan berjalan di `http://localhost:7860`.

---

## 5. Integrasi Google Drive (GAS)

Sistem menggunakan skrip perantara untuk mengunggah file. Berikut adalah contoh logika yang harus dipasang di Google Apps Script:

```javascript
function doPost(e) {
  var data = JSON.parse(e.postData.contents);
  var folder = DriveApp.getFolderById(data.folderId);
  var file = folder.createFile(data.filename, data.content);
  return ContentService.createTextOutput("Success");
}
```

---

## 6. Deployment (Docker & Hugging Face)

File `Dockerfile` telah disediakan untuk deployment cepat. Sistem dikonfigurasi untuk berjalan di port `7860` secara default, sesuai dengan standar Hugging Face Spaces.

```dockerfile
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]
```

---

## 7. Catatan Pengembangan
*   **JSON Handling**: Sistem dilengkapi dengan fungsi `extract_json` dan pembersihan karakter khusus untuk memastikan integritas data dari AI.
*   **Thinking Models**: Untuk model seperti Kimi, sistem mengirimkan parameter tambahan `{"thinking": true}` untuk hasil yang lebih analitis.

---
*Dokumentasi ini dibuat secara otomatis untuk membantu pemeliharaan dan pengembangan sistem AI Agent.*
