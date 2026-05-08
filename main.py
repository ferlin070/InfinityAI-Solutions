import os
import json
import requests
import time
from datetime import datetime
from openai import OpenAI
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="AI Command Center: 8-Agent System")

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

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

# --- SYSTEM PROMPTS (THE BRAIN) ---
AGENT_PROMPTS = {
    "CLAUDIA": (
        "Anda adalah Claudia, Chief of Staff (Manager Utama). Tugas anda adalah menganalisis arahan Bos "
        "dan menyerahkan tugas kepada ejen yang tepat dari senarai berikut:\n"
        "1. ZARA (Finance): Invois, resit, tax, hal duit.\n"
        "2. MAYA (Sales & CRM): Inquiry, quotation, client registry, status client.\n"
        "3. AMELIA (Training): Module, proposal training, checklist kelas, slides, nota.\n"
        "4. DANISH (Content): Copywriting, e-book, video analysis, prompt.\n"
        "5. AIMAN (Marketing): Launching plan, ads report, marketing strategy.\n"
        "6. ADILA (Operations): Morning brief, log harian, weekly review.\n"
        "7. HAKIM (System): Skill building, blueprint, tool integration, upgrade team.\n\n"
        "Balas HANYA JSON: {\"agent\": \"NAMA_EJEN\", \"task\": \"arahan terperinci\"}"
    ),
    "ZARA": "Anda adalah Zara, Pakar Kewangan. Fokus pada ketepatan data kewangan, pengurusan invois, dan laporan tax yang profesional.",
    "MAYA": "Anda adalah Maya, Pakar Sales & CRM. Fokus pada komunikasi pelanggan yang cemerlang, penyediaan sebut harga (quotation), dan pengurusan database client.",
    "AMELIA": "Anda adalah Amelia, Pakar Training Delivery. Fokus pada kualiti modul pembelajaran, penyediaan bahan latihan, dan struktur slides yang efektif.",
    "DANISH": "Anda adalah Danish, Pakar Content & Media. Fokus pada copywriting yang viral, penulisan e-book yang menarik, dan analisis video kreatif.",
    "AIMAN": "Anda adalah Aiman, Pakar Marketing. Fokus pada strategi pelancaran (launching), analisis data iklan (ads), dan strategi pemasaran yang agresif.",
    "ADILA": "Anda adalah Adila, Pakar Daily Operations. Fokus pada pengurusan rutin, morning brief yang bersemangat, dan mengekalkan log aktiviti pasukan.",
    "HAKIM": "Anda adalah Hakim, System Architect. Fokus pada pembangunan kemahiran (skills) baru ejen, pengurusan blueprint sistem, dan integrasi teknologi terkini."
}

class UserInput(BaseModel):
    prompt: str
    model_name: str = "meta/llama-3.3-70b-instruct"

# --- CORE FUNCTIONS ---

def upload_to_drive(filename, content, agent_name):
    folder_id = FOLDER_IDS.get(agent_name)
    if not GAS_URL or not folder_id:
        print(f"Skip Drive: GAS_URL atau Folder ID untuk {agent_name} tiada.")
        return

    try:
        payload = {"filename": filename, "content": content, "folderId": folder_id}
        requests.post(GAS_URL, json=payload, timeout=30)
        print(f"GAS Upload Berjaya: {filename} ({agent_name})")
    except Exception as e:
        print(f"Ralat Upload Drive: {str(e)}")

def add_json_log(agent, model, status, duration):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent": agent, "model": model, "status": status, "speed": f"{duration:.2f}s"
    }
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f: logs = json.load(f)
        except: logs = []
    logs.insert(0, log_entry)
    with open(LOG_FILE, "w", encoding="utf-8") as f: json.dump(logs[:50], f, indent=4)

def call_nvidia(sys_p, usr_p, model):
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}],
            temperature=0.7, max_tokens=4096
        )
        return resp.choices[0].message.content, time.time() - start
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", "r", encoding="utf-8") as f: return f.read()

@app.get("/api/history")
async def history():
    if not os.path.exists(LOG_FILE): return []
    with open(LOG_FILE, "r", encoding="utf-8") as f: return json.load(f)

@app.post("/api/execute")
async def execute(data: UserInput, background_tasks: BackgroundTasks):
    total_start = time.time()
    try:
        # Step 1: Claudia (Manager)
        claudia_out, _ = call_nvidia(AGENT_PROMPTS["CLAUDIA"], data.prompt, data.model_name)
        decision = json.loads(claudia_out.replace("```json", "").replace("```", "").strip())
        
        agent = decision.get("agent", "").upper()
        task = decision.get("task", "")
        
        if agent not in AGENT_PROMPTS or agent == "CLAUDIA":
            return {"status": "error", "message": f"Ejen {agent} tidak wujud."}

        # Step 2: Specialized Agent
        result, _ = call_nvidia(AGENT_PROMPTS[agent], task, data.model_name)
        total_time = time.time() - total_start
        
        # Step 3: Drive & Logging
        filename = f"{agent}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        background_tasks.add_task(upload_to_drive, filename, result, agent)
        add_json_log(agent, data.model_name, "Success", total_time)
        
        return {
            "status": "success", "assigned_to": agent, "task": task,
            "result": result, "speed": f"{total_time:.2f}s", "model": data.model_name
        }
    except Exception as e:
        add_json_log("System", data.model_name, f"Error: {str(e)}", 0)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
