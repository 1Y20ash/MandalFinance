import os

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

# Rate-limit state must be shared/persistent in production.  Prefer an
# explicitly configured rate-limit URI, while allowing Vercel's Redis
# integration (REDIS_URL) to supply the shared Redis connection directly.
_ratelimit_storage_uri = os.getenv("RATELIMIT_STORAGE_URI") or os.getenv("REDIS_URL")
if os.getenv("FLASK_ENV", "").lower() == "production" and not _ratelimit_storage_uri:
    raise RuntimeError("RATELIMIT_STORAGE_URI or REDIS_URL must be configured in production")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_ratelimit_storage_uri or "memory://",
    # Phase 24: establish a conservative application-wide ceiling while
    # sensitive endpoints receive tighter route-specific limits.
    default_limits=["300 per minute"],
    headers_enabled=True,
)

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'
