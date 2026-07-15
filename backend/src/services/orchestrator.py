import time
import re
import json
from datetime import datetime
from fastapi import HTTPException, BackgroundTasks
from src.core.config import logger
from src.core.constants import AGENT_PROMPTS, SPECIALIST_AGENTS
from src.services.llm import call_nvidia
from src.services.drive import upload_to_drive
from src.services.logging import add_json_log, extract_json
from src.schemas.models import UserInput, ExecuteResponse, AgentResult


async def execute_task(data: UserInput, background_tasks: BackgroundTasks) -> ExecuteResponse:
    """
    Execute a task by having Claudia parse the request and delegate to specialists.

    Flow:
    1. Claudia analyzes the prompt and decides which agents should handle it
    2. For each assigned agent, call the LLM with that agent's prompt
    3. Upload results to Drive and log execution
    """
    total_start = time.time()
    try:
        # Step 1: Claudia (Manager) decides task assignments
        claudia_prompt = AGENT_PROMPTS["CLAUDIA"]
        claudia_out, _ = call_nvidia(claudia_prompt, data.prompt, data.model_name, temperature=0.1)

        json_str = extract_json(claudia_out)
        if not json_str:
            logger.warning(f"Claudia membalas tanpa JSON sah. Jawapan Claudia: {claudia_out[:200]}")
            return ExecuteResponse(
                status="error",
                message="Claudia membalas tanpa JSON sah.",
                model=data.model_name
            )

        # Try parsing Claudia's decision
        try:
            # Clean control characters
            import re
            cleaned = "".join(ch for ch in json_str if ch.isprintable() or ch in '\n\r\t')
            cleaned = cleaned.replace('\n', '\\n').replace('\r', '\\r')
            decision = json.loads(cleaned)
        except Exception:
            try:
                # Fallback: regex extraction
                status_match = re.search(r'"status":\s*"(\w+)"', json_str)
                status = status_match.group(1) if status_match else "error"

                if status == "rejected":
                    reason_match = re.search(r'"reason":\s*"(.*?)"', json_str, re.DOTALL)
                    reason = reason_match.group(1) if reason_match else "Tugas ditolak."
                    decision = {"status": "rejected", "reason": reason}
                else:
                    assignments = []
                    agents = re.findall(r'"agent":\s*"(\w+)"', json_str)
                    tasks = re.findall(r'"task":\s*"(.*?)"', json_str, re.DOTALL)
                    for a, t in zip(agents, tasks):
                        assignments.append({"agent": a, "task": t})
                    decision = {"status": "accepted", "assignments": assignments}
            except Exception as e:
                logger.error(f"Kegagalan total menghurai JSON dari Claudia: {str(e)}")
                return ExecuteResponse(
                    status="error",
                    message="Kegagalan menghurai keputusan tugasan dari Claudia.",
                    model=data.model_name
                )

        # Handle rejection
        if decision.get("status") == "rejected":
            return ExecuteResponse(
                status="rejected",
                message=decision.get("reason", "Tugasan di luar bidang kuasa AI."),
                model=data.model_name
            )

        assignments = decision.get("assignments", [])
        if not assignments:
            return ExecuteResponse(
                status="error",
                message="Claudia tidak memberikan tugasan kepada sesiapa.",
                model=data.model_name
            )

        # Step 2: Execute each assigned agent
        all_results = []
        for assign in assignments:
            agent = assign.get("agent", "").upper()
            task = assign.get("task", "")

            if agent in SPECIALIST_AGENTS:
                res, speed = call_nvidia(AGENT_PROMPTS[agent], task, data.model_name)

                # Upload result and log
                filename = f"{agent}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
                background_tasks.add_task(upload_to_drive, filename, res, agent)
                add_json_log(agent, data.model_name, "Success", speed)

                all_results.append(AgentResult(
                    agent=agent,
                    task=task,
                    result=res,
                    speed=f"{speed:.2f}s"
                ))

        total_time = time.time() - total_start

        return ExecuteResponse(
            status="success",
            results=all_results,
            total_speed=f"{total_time:.2f}s",
            model=data.model_name
        )

    except HTTPException as he:
        add_json_log("System", data.model_name, f"Error: {he.detail}", 0)
        raise he
    except Exception as e:
        logger.error(f"System execution failure: {str(e)}", exc_info=True)
        err_msg = "Ralat dalaman sistem semasa memproses tugasan."
        add_json_log("System", data.model_name, f"Error: {err_msg}", 0)
        raise HTTPException(status_code=500, detail=err_msg)
