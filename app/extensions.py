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

# Phase 23: the production configuration validates that this URI is backed by
# shared persistent storage. Development/testing may intentionally use memory.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri='memory://',
    default_limits=['300 per minute'],
    headers_enabled=True,
)

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'
