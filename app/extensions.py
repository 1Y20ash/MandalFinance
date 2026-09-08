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

# Rate-limit state must be shared/persistent in production.  An in-memory
# backend is acceptable only for local development/testing when no backend
# has been configured explicitly.
_ratelimit_storage_uri = os.getenv("RATELIMIT_STORAGE_URI")
if os.getenv("FLASK_ENV", "").lower() == "production" and not _ratelimit_storage_uri:
    raise RuntimeError("RATELIMIT_STORAGE_URI must be configured in production")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_ratelimit_storage_uri or "memory://",
    default_limits=[],
)

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'
