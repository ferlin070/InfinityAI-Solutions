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
        "Anda adalah Claudia, Chief of Staff (Manager Utama). Tugas anda adalah menganalisis arahan Bos.\n"
        "Jika arahan memerlukan lebih daripada satu kepakaran, anda MESTI membahagikan tugas kepada ejen-ejen yang berkaitan.\n"
        "Senarai Ejen:\n"
        "1. ZARA (Finance): Invois, bajet, resit, hal duit.\n"
        "2. MAYA (Sales & CRM): Quotation, client database, inquiry.\n"
        "3. AMELIA (Training): Modul, slides, nota, proposal training.\n"
        "4. DANISH (Content): Copywriting, skrip, e-book, video analysis.\n"
        "5. AIMAN (Marketing): Ads report, strategy, FB/IG comments.\n"
        "6. ADILA (Operations): Log, briefs, info umum.\n"
        "7. HAKIM (System): IT, coding, system architect, skill upgrade.\n\n"
        "Balas HANYA JSON: {\"assignments\": [{\"agent\": \"NAMA_EJEN\", \"task\": \"arahan spesifik\"}]}"
    ),
    "ZARA": "Anda adalah Zara, Pakar Kewangan. Sediakan pengiraan bajet atau dokumen kewangan yang tepat.",
    "MAYA": "Anda adalah Maya, Pakar CRM. Uruskan database klien dan sediakan sebut harga profesional.",
    "AMELIA": "Anda adalah Amelia, Pakar Training. Sediakan modul atau nota latihan yang sistematik.",
    "DANISH": "Anda adalah Danish, Pakar Content. Tulis copywriting atau skrip video yang menarik.",
    "AIMAN": "Anda adalah Aiman, Pakar Marketing. Sediakan strategi pemasaran atau balasan komen prospek yang efektif.",
    "ADILA": "Anda adalah Adila, Pakar Operations. Sediakan maklumat umum atau log harian yang kemas.",
    "HAKIM": "Anda adalah Hakim, System Architect. Bina kod HTML/CSS/JS atau beri nasihat teknikal sistem."
}

class UserInput(BaseModel):
    prompt: str
    model_name: str = "meta/llama-3.1-70b-instruct"

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

def extract_json(text):
    """Mencari dan mengekstrak objek JSON pertama yang lengkap dari teks."""
    start = text.find('{')
    if start == -1: return None
    count = 0
    for i in range(start, len(text)):
        if text[i] == '{': count += 1
        elif text[i] == '}': count -= 1
        if count == 0:
            return text[start:i+1]
    return None

@app.post("/api/execute")
async def execute(data: UserInput, background_tasks: BackgroundTasks):
    total_start = time.time()
    try:
        # Step 1: Claudia (Manager) decides
        claudia_out, _ = call_nvidia(AGENT_PROMPTS["CLAUDIA"], data.prompt, data.model_name)
        
        json_str = extract_json(claudia_out.replace("```json", "").replace("```", "").strip())
        if not json_str:
            return {"status": "error", "message": "Claudia gagal memproses arahan."}
            
        decision = json.loads(json_str)
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
    except Exception as e:
        add_json_log("System", data.model_name, f"Error: {str(e)}", 0)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
