import os
import sys

# Masukkan direktori backend ke sys.path untuk membolehkan import src.*
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(root_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from src.services.supabase_client import get_client

def verify():
    client = get_client()
    if not client:
        print("GAGAL: Kredensial Supabase tidak dikonfigurasikan di .env.")
        sys.exit(1)

    tables = ["organizations", "org_members", "agents", "agent_runs", "executions"]
    all_ok = True

    print("Memulakan verifikasi jadual Supabase...")
    for table in tables:
        # Gunakan Prefer: count=exact untuk mendapatkan jumlah baris dari PostgREST
        headers = {"Prefer": "count=exact"}
        # Hadkan limit=1 untuk kelajuan optimum
        response = client.get(f"{table}?limit=1", headers=headers)

        # PostgREST mengembalikan HTTP 200 atau 206 jika pertanyaan berjaya
        if response.status_code in (200, 206):
            content_range = response.headers.get("Content-Range")
            count = "unknown"
            if content_range and "/" in content_range:
                count = content_range.split("/")[-1]
            print(f"Jadual '{table}': WUJUD (jumlah baris: {count})")
            
            # Verifikasi seed data untuk jadual agents
            if table == "agents":
                try:
                    num_agents = int(count)
                    if num_agents < 8:
                        print(f"AMARAN: Seed data agents kurang daripada 8 (dijumpai: {num_agents})")
                except ValueError:
                    pass
        else:
            print(f"Jadual '{table}': GAGAL (HTTP {response.status_code}) - {response.text}")
            all_ok = False

    if all_ok:
        print("\nOK: Semua 5 jadual M0 wujud di Supabase dan boleh diakses.")
        sys.exit(0)
    else:
        print("\nGAGAL: Beberapa jadual tidak wujud atau tidak boleh diakses.")
        sys.exit(1)

if __name__ == "__main__":
    verify()
