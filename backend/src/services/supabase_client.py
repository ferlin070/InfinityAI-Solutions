import requests
from src.core.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, logger

class SupabaseRestClient:
    """
    Satu pembungkus (client) REST ringan untuk berkomunikasi terus dengan
    PostgREST API milik Supabase menggunakan pustaka requests (Opsi B).
    """
    def __init__(self, url: str, service_role_key: str):
        self.url = url.strip().rstrip('/')
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json"
        }

    def get(self, path: str, params: dict = None, headers: dict = None):
        target_url = f"{self.url}/rest/v1/{path.lstrip('/')}"
        merged_headers = {**self.headers, **(headers or {})}
        response = requests.get(target_url, headers=merged_headers, params=params)
        return response

    def post(self, path: str, json_data: dict = None, headers: dict = None):
        target_url = f"{self.url}/rest/v1/{path.lstrip('/')}"
        merged_headers = {**self.headers, **(headers or {})}
        response = requests.post(target_url, headers=merged_headers, json=json_data)
        return response

# Instance client dimuat secara lazy (lazy-init)
_client = None

def get_client() -> SupabaseRestClient:
    """
    Mengambil atau menginisialisasi instance SupabaseRestClient secara lazy.
    Mengembalikan None jika Supabase tidak dikonfigurasikan di lingkungan.
    """
    global _client
    if _client is not None:
        return _client

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("get_client() dipanggil tetapi Supabase tidak dikonfigurasikan di .env.")
        return None

    _client = SupabaseRestClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _client
