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

app = FastAPI(title="Multi-Agent AI Orchestrator (Major Upgrade)")

# Configuration
NVIDIA_API_KEY = os.getenv("NVIDIA_NIM_API_KEY")
ZARA_FOLDER_ID = os.getenv("ZARA_DRIVE_FOLDER_ID")
DANISH_FOLDER_ID = os.getenv("DANISH_DRIVE_FOLDER_ID")
GAS_URL = os.getenv("GAS_WEB_APP_URL")
LOG_FILE = "daily_log.json"

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

# Agent System Prompts
AGENT_PROMPTS = {
    "CLAUDIA": (
        "Anda adalah Claudia, Manager Ejen AI. Tugas anda adalah menganalisis arahan pengguna "
        "dan menyerahkan tugas kepada ejen yang betul: ZARA atau DANISH.\n"
        "- ZARA: Pakar Kewangan (Invois, resit, bajet, pengurusan wang).\n"
        "- DANISH: Pakar Kandungan (Content creator, media sosial, copywriting, pemasaran).\n\n"
        "Balas HANYA dalam format JSON (Tanpa markdown): \n"
        "{\"agent\": \"ZARA\", \"task\": \"arahan terperinci untuk Zara\"}\n"
        "atau\n"
        "{\"agent\": \"DANISH\", \"task\": \"arahan terperinci untuk Danish\"}"
    ),
    "ZARA": (
        "Anda adalah Zara, Pakar Kewangan. Sediakan dokumen kewangan seperti invois atau resit yang sangat kemas "
        "dan profesional dalam format teks."
    ),
    "DANISH": (
        "Anda adalah Danish, Content Creator yang hebat. Gaya bahasa anda santai, moden, dan sangat memujuk."
    )
}

class UserInput(BaseModel):
    prompt: str
    model_name: str = "meta/llama3-70b-instruct"

# --- FUNCTIONS ---

def upload_to_drive(filename, content, folder_id):
    """Memuat naik kandungan ke Google Drive melalui Google Apps Script Bridge."""
    if not GAS_URL:
        add_json_log("System", "N/A", "Gagal (GAS_URL Tiada)", 0)
        return

    try:
        payload = {
            "filename": filename,
            "content": content,
            "folderId": folder_id
        }
        
        response = requests.post(GAS_URL, json=payload, timeout=30)
        result = response.json()
        
        if result.get("status") == "success":
            print(f"GAS Upload Selesai: {filename}")
        else:
            print(f"GAS Upload Error: {result.get('message')}")
            
    except Exception as e:
        print(f"Ralat Request GAS: {str(e)}")

def add_json_log(agent, model, status, duration):
    """Menyimpan rekod log ke dalam fail daily_log.json."""
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agent": agent,
        "model": model,
        "status": status,
        "speed": f"{duration:.2f}s"
    }
    
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except:
            logs = []
            
    logs.insert(0, log_entry) # Tambah di atas
    
    # Simpan hanya 50 log terakhir
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs[:50], f, indent=4)

def call_nvidia_nim(system_prompt: str, user_prompt: str, model_name: str):
    start_time = time.time()
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=4096
        )
        duration = time.time() - start_time
        return completion.choices[0].message.content, duration
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def read_index():
    if not os.path.exists("index.html"):
         return HTMLResponse(content="<h1>index.html not found</h1>", status_code=404)
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/history")
async def get_history():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/execute")
async def execute_orchestrator(input_data: UserInput, background_tasks: BackgroundTasks):
    total_start_time = time.time()
    
    # Step 1: Claudia analyzes the request
    claudia_response, _ = call_nvidia_nim(AGENT_PROMPTS["CLAUDIA"], input_data.prompt, input_data.model_name)
    
    try:
        # Clean response if there is markdown
        clean_json = claudia_response.replace("```json", "").replace("```", "").strip()
        decision = json.loads(clean_json)
        
        target_agent = decision.get("agent", "").upper()
        task_description = decision.get("task", "")
        
        if target_agent not in ["ZARA", "DANISH"]:
            add_json_log("Claudia", input_data.model_name, "Error: Ejen Tidak Ditemui", 0)
            return {"status": "error", "message": "Ejen tidak ditemui dalam senarai."}
        
        # Step 2: Execute the specialized agent
        final_result, agent_duration = call_nvidia_nim(AGENT_PROMPTS[target_agent], task_description, input_data.model_name)
        
        # Calculate overall duration for the specific agent task
        total_duration = time.time() - total_start_time
        
        # Step 3: Google Drive Upload via GAS & Logging
        folder_id = ZARA_FOLDER_ID if target_agent == "ZARA" else DANISH_FOLDER_ID
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"Tugasan_{target_agent}_{timestamp_str}.txt"
        
        # Background upload to Drive
        background_tasks.add_task(upload_to_drive, filename, final_result, folder_id)
        
        # Record Log
        add_json_log(target_agent, input_data.model_name, "Success", total_duration)
        
        return {
            "status": "success",
            "manager": "Claudia",
            "assigned_to": target_agent,
            "task": task_description,
            "result": final_result,
            "speed": f"{total_duration:.2f}s",
            "model": input_data.model_name
        }
        
    except Exception as e:
        add_json_log("System", input_data.model_name, f"Error: {str(e)}", 0)
        return {
            "status": "error",
            "message": f"Parsing Error: {str(e)}",
            "raw": claudia_response
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
