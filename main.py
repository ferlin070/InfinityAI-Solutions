import os
import json
import requests
import time
from datetime import datetime
from openai import OpenAI
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("server.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("ai_command_center")

app = FastAPI(title="AI Command Center: 8-Agent System")

# Configure CORS Middleware (Medium/Low Fix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Custom HTTP Middleware to inject Security Headers (Medium/Low Fix)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Configuration
NVIDIA_API_KEY = os.getenv("NVIDIA_NIM_API_KEY")
GAS_URL = os.getenv("GAS_WEB_APP_URL")
LOG_FILE = "daily_log.json"

# Folder Mappings
FOLDER_IDS = {
    "ZARA": os.getenv("ZARA_DRIVE_FOLDER_ID"),
    "DANISH": os.getenv("DANISH_DRIVE_FOLDER_ID"),
    "MAYA": os.getenv("MAYA_DRIVE_FOLDER_ID"),
    "AMELIA": os.getenv("AMELIA_DRIVE_FOLDER_ID"),
    "AIMAN": os.getenv("AIMAN_DRIVE_FOLDER_ID"),
    "ADILA": os.getenv("ADILA_DRIVE_FOLDER_ID"),
    "HAKIM": os.getenv("HAKIM_DRIVE_FOLDER_ID")
}

# Startup verification of environment variables
if not NVIDIA_API_KEY:
    logger.warning("NVIDIA_NIM_API_KEY tidak dikonfigurasikan dalam fail .env! Panggilan API ke model NVIDIA akan gagal.")
if not GAS_URL:
    logger.warning("GAS_WEB_APP_URL tidak dikonfigurasikan dalam fail .env! Sistem tidak dapat memuat naik hasil kerja ke Google Drive.")

for agent_name, folder_id in FOLDER_IDS.items():
    if not folder_id:
        logger.warning(f"Google Drive folder ID untuk ejen '{agent_name}' tidak dijumpai dalam fail .env.")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY or "missing_key",
    timeout=60.0 # Timeout configuration (Medium/Low Fix)
)

# --- SYSTEM PROMPTS (THE BRAIN) ---
AGENT_PROMPTS = {
    "CLAUDIA": (
        "Anda adalah Claudia, Chief of Staff. Analisis TUJUAN tugasan Bos, bukan sekadar kata kunci.\n"
        "PERATURAN UTAMA:\n"
        "1. STRATEGI PEMASARAN (AIMAN): Pelan marketing fasa-fasa, strategi iklan, branding.\n"
        "2. JUALAN & CRM (MAYA): Menapis prospek, menjawab inquiry klien, sebut harga.\n"
        "3. LATIHAN (AMELIA): Nota edaran peserta, modul kelas, slides pembelajaran.\n"
        "4. KREATIF (DANISH): E-book, copywriting hiburan/viral.\n"
        "5. KEWANGAN (ZARA): Bajet, invois, pengiraan kos.\n"
        "6. OPERASI (ADILA): Log harian, info umum syarikat.\n"
        "7. TEKNIKAL (HAKIM): Coding, IT, sistem.\n"
        "JANGAN hantar tugasan JUALAN kepada DANISH. Balas HANYA JSON: {\"status\": \"accepted\", \"assignments\": [{\"agent\": \"NAMA\", \"task\": \"arahan\"}]}"
    ),
    "ZARA": "Anda adalah Zara, Pakar Kewangan. Sediakan pengiraan bajet dan dokumen kewangan.",
    "MAYA": "Anda adalah Maya, Pakar Sales & CRM. Fokus anda adalah menapis prospek, mengurus database klien, dan menyediakan sebut harga.",
    "AMELIA": "Anda adalah Amelia, Pakar Training. Sediakan modul, nota kelas, dan bahan edaran peserta.",
    "DANISH": "Anda adalah Danish, Pakar Content. Tulis copywriting atau e-book. JANGAN buat skrip video kecuali diminta. Jika Bos minta nota/info, berikan dalam format teks biasa.",
    "AIMAN": "Anda adalah Aiman, Pakar Marketing. Sediakan strategi iklan dan marketing plan.",
    "ADILA": "Anda adalah Adila, Pakar Ops. Sediakan log harian dan laporan rutin.",
    "HAKIM": "Anda adalah Hakim, System Architect. Sediakan kod teknikal dan bantuan IT."
}

class UserInput(BaseModel):
    prompt: str
    model_name: str = "meta/llama-3.1-70b-instruct"

# --- CORE FUNCTIONS ---

def upload_to_drive(filename, content, agent_name):
    folder_id = FOLDER_IDS.get(agent_name)
    if not GAS_URL or not folder_id:
        logger.info(f"Skip Drive: GAS_URL atau Folder ID untuk {agent_name} tiada.")
        return

    try:
        payload = {"filename": filename, "content": content, "folderId": folder_id}
        resp = requests.post(GAS_URL, json=payload, timeout=30)
        resp.raise_for_status()
        logger.info(f"GAS Upload Berjaya: {filename} ({agent_name})")
    except Exception as e:
        logger.error(f"Ralat Upload Drive untuk {agent_name}: {str(e)}", exc_info=True)

def add_json_log(agent, model, status, duration):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent": agent, "model": model, "status": status, "speed": f"{duration:.2f}s"
    }
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception as e:
            logger.warning(f"Ralat membaca fail log harian: {str(e)}. Memulakan log baru.")
            logs = []
    logs.insert(0, log_entry)
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs[:50], f, indent=4)
    except Exception as e:
        logger.error(f"Gagal menulis log ke fail {LOG_FILE}: {str(e)}")

def call_nvidia(sys_p, usr_p, model, temp=0.7):
    start = time.time()
    try:
        # Konfigurasi khusus untuk model Kimi (Thinking Model)
        extra_args = {}
        tokens = 4096
        if "kimi" in model.lower():
            extra_args["extra_body"] = {"chat_template_kwargs": {"thinking": True}}
            tokens = 16384 # Kimi sokong token lebih tinggi
            
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}],
            temperature=temp, 
            max_tokens=tokens,
            **extra_args
        )
        return resp.choices[0].message.content, time.time() - start
    except Exception as e:
        logger.error(f"Ralat semasa memanggil API NVIDIA NIM: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Ralat dalaman semasa berhubung dengan API NVIDIA NIM."
        )

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/api/history")
async def history():
    if not os.path.exists(LOG_FILE): return []
    with open(LOG_FILE, "r", encoding="utf-8") as f: return json.load(f)

def extract_json(text):
    """Mencari dan mengekstrak objek JSON pertama dari teks secara robust."""
    if not text:
        return None
        
    text_clean = text.replace("```json", "").replace("```", "").strip()
    
    # Cuba cari kurungan sepadan dengan mengabaikan watak di dalam rentetan (strings)
    start = text_clean.find('{')
    if start == -1: 
        return None
    
    count = 0
    in_string = False
    escape = False
    
    for i in range(start, len(text_clean)):
        char = text_clean[i]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
            
        if not in_string:
            if char == '{':
                count += 1
            elif char == '}':
                count -= 1
                if count == 0:
                    candidate = text_clean[start:i+1]
                    try:
                        # Pengesahan standard JSON
                        json.loads(candidate)
                        return candidate
                    except Exception:
                        pass # Cuba cari kurungan lain jika ini bukan JSON sah
                        
    # Jika gagal sepadan secara dinamik, cuba guna pembilangan asal sebagai sandaran (fallback)
    count = 0
    for i in range(start, len(text_clean)):
        if text_clean[i] == '{': count += 1
        elif text_clean[i] == '}': count -= 1
        if count == 0:
            return text_clean[start:i+1]
            
    return text_clean[start:].strip()

@app.post("/api/execute")
async def execute(data: UserInput, background_tasks: BackgroundTasks):
    total_start = time.time()
    try:
        # Step 1: Claudia (Manager) decides
        claudia_out, _ = call_nvidia(AGENT_PROMPTS["CLAUDIA"], data.prompt, data.model_name, temp=0.1)
        
        json_str = extract_json(claudia_out)
        if not json_str:
            logger.warning(f"Claudia membalas tanpa JSON sah. Jawapan Claudia: {claudia_out[:200]}")
            return {"status": "error", "message": "Claudia membalas tanpa JSON sah."}
            
        try:
            # Cara 1: Bersihkan watak kawalan (control characters)
            import re
            cleaned = "".join(ch for ch in json_str if ch.isprintable() or ch in '\n\r\t')
            cleaned = cleaned.replace('\n', '\\n').replace('\r', '\\r')
            decision = json.loads(cleaned)
        except Exception:
            try:
                # Cara 2: Cuba regex untuk ambil field utama jika JSON hancur
                import re
                status_match = re.search(r'"status":\s*"(\w+)"', json_str)
                status = status_match.group(1) if status_match else "error"
                
                if status == "rejected":
                    reason_match = re.search(r'"reason":\s*"(.*?)"', json_str, re.DOTALL)
                    reason = reason_match.group(1) if reason_match else "Tugas ditolak."
                    decision = {"status": "rejected", "reason": reason}
                else:
                    # Ambil assignments secara manual
                    assignments = []
                    agents = re.findall(r'"agent":\s*"(\w+)"', json_str)
                    tasks = re.findall(r'"task":\s*"(.*?)"', json_str, re.DOTALL)
                    for a, t in zip(agents, tasks):
                        assignments.append({"agent": a, "task": t})
                    decision = {"status": "accepted", "assignments": assignments}
            except Exception as e:
                logger.error(f"Kegagalan total menghurai JSON dari Claudia: {str(e)}")
                return {"status": "error", "message": "Kegagalan menghurai keputusan tugasan dari Claudia."}
        
        # Handle Rejection
        if decision.get("status") == "rejected":
            return {"status": "rejected", "message": decision.get("reason", "Tugasan di luar bidang kuasa AI.")}

        assignments = decision.get("assignments", [])
        
        if not assignments:
            return {"status": "error", "message": "Claudia tidak memberikan tugasan kepada sesiapa."}

        # Step 2: Execute each assigned agent
        all_results = []
        for assign in assignments:
            agent = assign.get("agent", "").upper()
            task = assign.get("task", "")
            
            if agent in AGENT_PROMPTS and agent != "CLAUDIA":
                res, speed = call_nvidia(AGENT_PROMPTS[agent], task, data.model_name)
                
                # Drive & Logging
                filename = f"{agent}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                background_tasks.add_task(upload_to_drive, filename, res, agent)
                add_json_log(agent, data.model_name, "Success", speed)
                
                all_results.append({
                    "agent": agent,
                    "task": task,
                    "result": res,
                    "speed": f"{speed:.2f}s"
                })

        total_time = time.time() - total_start
        
        return {
            "status": "success",
            "results": all_results,
            "total_speed": f"{total_time:.2f}s",
            "model": data.model_name
        }
    except HTTPException as he:
        add_json_log("System", data.model_name, f"Error: {he.detail}", 0)
        raise he
    except Exception as e:
        logger.error(f"System execution failure: {str(e)}", exc_info=True)
        err_msg = "Ralat dalaman sistem semasa memproses tugasan."
        add_json_log("System", data.model_name, f"Error: {err_msg}", 0)
        raise HTTPException(status_code=500, detail=err_msg)

if __name__ == "__main__":
    import uvicorn
    # Hugging Face menggunakan port 7860
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
