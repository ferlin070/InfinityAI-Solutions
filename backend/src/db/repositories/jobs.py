from datetime import datetime, timezone
from typing import Optional
from src.db.client import get_supabase


class JobRepo:
    def __init__(self):
        self._db = get_supabase()

    def enqueue(self, org_id: str, job_type: str, payload: Optional[dict] = None,
                run_at: Optional[str] = None) -> dict:
        data = {
            "org_id": org_id,
            "type": job_type,
            "payload": payload or {},
            "run_at": run_at or datetime.now(timezone.utc).isoformat(),
        }
        result = self._db.table("jobs").insert(data).execute()
        return result.data[0]

    def claim_next(self) -> Optional[dict]:
        now = datetime.now(timezone.utc).isoformat()
        result = (
            self._db.rpc("claim_job", {"current_time": now})
            .execute()
        )
        return result.data[0] if result.data else None

    def complete(self, job_id: str) -> dict:
        result = (
            self._db.table("jobs")
            .update({"status": "done"})
            .eq("id", job_id)
            .execute()
        )
        return result.data[0]

    def fail(self, job_id: str, error: str) -> dict:
        job = (
            self._db.table("jobs")
            .select("attempts, max_attempts")
            .eq("id", job_id)
            .single()
            .execute()
        )
        data = job.data
        new_attempts = (data.get("attempts", 0) or 0) + 1
        if new_attempts >= data.get("max_attempts", 3):
            status = "failed"
        else:
            status = "pending"
        result = (
            self._db.table("jobs")
            .update({
                "status": status,
                "attempts": new_attempts,
                "last_error": error,
            })
            .eq("id", job_id)
            .execute()
        )
        return result.data[0]
