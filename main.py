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

def call_nvidia(sys_p, usr_p, model, temp=0.7):
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}],
            temperature=temp, max_tokens=4096
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
    """Mencari dan mengekstrak objek JSON pertama dari teks."""
    start = text.find('{')
    if start == -1: return None
    
    # Cuba cari kurungan sepadan
    count = 0
    for i in range(start, len(text)):
        if text[i] == '{': count += 1
        elif text[i] == '}': count -= 1
        if count == 0:
            return text[start:i+1]
            
    # Jika gagal sepadan (mungkin truncated), ambil sahaja hingga akhir
    # dan cuba tambah penutup } jika perlu
    return text[start:].strip()

@app.post("/api/execute")
async def execute(data: UserInput, background_tasks: BackgroundTasks):
    total_start = time.time()
    try:
        # Step 1: Claudia (Manager) decides
        claudia_out, _ = call_nvidia(AGENT_PROMPTS["CLAUDIA"], data.prompt, data.model_name, temp=0.1)
        
        json_str = extract_json(claudia_out.replace("```json", "").replace("```", "").strip())
        if not json_str:
            return {"status": "error", "message": f"Claudia membalas tanpa JSON: {claudia_out[:100]}..."}
            
        try:
            # Cara 1: Bersihkan watak kawalan (control characters)
            import re
            # Buang watak kawalan kecuali tab, newline, dsb
            cleaned = "".join(ch for ch in json_str if ch.isprintable() or ch in '\n\r\t')
            # Tukar newline kepada literal \n untuk json.loads
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
            except:
                return {"status": "error", "message": f"Kegagalan Total JSON: {json_str[:100]}..."}
        
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
    except Exception as e:
        add_json_log("System", data.model_name, f"Error: {str(e)}", 0)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Hugging Face menggunakan port 7860
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
