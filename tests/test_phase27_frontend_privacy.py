from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_TEMPLATE = ROOT / "app" / "templates" / "base.html"
DONATE_TEMPLATE = ROOT / "app" / "templates" / "public" / "donate.html"
PWA_JS = ROOT / "app" / "static" / "js" / "pwa-install.js"
SERVICE_WORKER = ROOT / "app" / "static" / "sw.js"
POLICY = ROOT / "docs" / "FRONTEND_PRIVACY_POLICY.md"


def test_frontend_privacy_policy_exists_and_defines_storage_boundary():
    text = POLICY.read_text(encoding="utf-8")
    required = [
        "Client-side storage rules",
        "sessionStorage",
        "localStorage",
        "CSRF tokens",
        "payment credentials",
        "document contents",
        "Service-worker and offline-cache boundary",
    ]
    for phrase in required:
        assert phrase in text


def test_pwa_install_state_is_only_non_sensitive_session_ui_state():
    text = PWA_JS.read_text(encoding="utf-8")
    assert "sessionStorage" in text
    assert "SESSION_KEY" in text
    assert "deferredInstallPrompt" in text
    assert "localStorage" not in text
    assert "document.cookie" not in text
    assert "Authorization" not in text


def test_donation_page_contains_csrf_and_is_not_precached():
    donate = DONATE_TEMPLATE.read_text(encoding="utf-8")
    worker = SERVICE_WORKER.read_text(encoding="utf-8")

    assert 'name="csrf_token"' in donate
    assert "'/donate'" not in worker
    assert '"/donate"' not in worker
    assert "PUBLIC_SHELL_ASSETS" in worker
    assert "PUBLIC_FALLBACK = '/transparency'" in worker


def test_service_worker_never_caches_non_get_or_cross_origin_requests():
    worker = SERVICE_WORKER.read_text(encoding="utf-8")
    assert "request.method === 'GET'" in worker
    assert "new URL(request.url).origin === self.location.origin" in worker
    assert "if (!isGetRequest(request) || !isSameOrigin(request)) return;" in worker


def test_service_worker_cache_is_limited_to_public_shell_and_static_assets():
    worker = SERVICE_WORKER.read_text(encoding="utf-8")
    assert "request.mode === 'navigate'" in worker
    assert "isStaticAsset(request)" in worker
    assert "request.url" in worker
    assert "caches.match(PUBLIC_FALLBACK)" in worker
    assert "caches.match(request)" in worker
    assert "PUBLIC_SHELL_ASSETS" in worker


def test_base_template_does_not_directly_persist_application_data():
    text = BASE_TEMPLATE.read_text(encoding="utf-8")
    assert "localStorage" not in text
    assert "indexedDB" not in text.lower()
    assert "document.cookie" not in text
    assert "navigator.serviceWorker.register('/sw.js')" in text
