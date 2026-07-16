import pytest
from unittest.mock import patch
from src.core import config
from src.services.supabase_client import get_client, SupabaseRestClient

def test_supabase_config_missing_one_raises_error():
    # Uji SUPABASE_URL diset, SUPABASE_SERVICE_ROLE_KEY tidak diset
    with patch("src.core.config.SUPABASE_URL", "https://example.supabase.co"), \
         patch("src.core.config.SUPABASE_SERVICE_ROLE_KEY", None):
        with pytest.raises(RuntimeError) as exc_info:
            config.verify_environment()
        assert "Konfigurasi Supabase tidak lengkap" in str(exc_info.value)

    # Uji SUPABASE_URL tidak diset, SUPABASE_SERVICE_ROLE_KEY diset
    with patch("src.core.config.SUPABASE_URL", None), \
         patch("src.core.config.SUPABASE_SERVICE_ROLE_KEY", "secret-role-key"):
        with pytest.raises(RuntimeError) as exc_info:
            config.verify_environment()
        assert "Konfigurasi Supabase tidak lengkap" in str(exc_info.value)

def test_supabase_config_both_missing_succeeds_fail_open():
    # Uji kedua-duanya tiada (fail-open)
    with patch("src.core.config.SUPABASE_URL", None), \
         patch("src.core.config.SUPABASE_SERVICE_ROLE_KEY", None):
        # Tidak sepatutnya mencetuskan sebarang RuntimeError
        config.verify_environment()
        
        # Supabase client sepatutnya mengembalikan None
        with patch("src.services.supabase_client.SUPABASE_URL", None), \
             patch("src.services.supabase_client.SUPABASE_SERVICE_ROLE_KEY", None), \
             patch("src.services.supabase_client._client", None):
            client = get_client()
            assert client is None

def test_supabase_config_both_set_succeeds():
    # Uji kedua-duanya diset
    with patch("src.core.config.SUPABASE_URL", "https://example.supabase.co"), \
         patch("src.core.config.SUPABASE_SERVICE_ROLE_KEY", "secret-role-key"):
        # Tidak sepatutnya mencetuskan sebarang RuntimeError
        config.verify_environment()
        
        # Client sepatutnya berjaya diinisialisasi
        with patch("src.services.supabase_client.SUPABASE_URL", "https://example.supabase.co"), \
             patch("src.services.supabase_client.SUPABASE_SERVICE_ROLE_KEY", "secret-role-key"), \
             patch("src.services.supabase_client._client", None):
            client = get_client()
            assert isinstance(client, SupabaseRestClient)
            assert client.url == "https://example.supabase.co"
            assert client.headers["apikey"] == "secret-role-key"
            assert client.headers["Authorization"] == "Bearer secret-role-key"
