"""Explicitly make every tracked Jinja template a Python runtime dependency.

Vercel's Python runtime bundles files that are reachable at build time. Flask/Jinja
loads HTML templates dynamically, so the template tree is otherwise invisible to
the dependency tracer. These literal paths keep app/templates as the single
source of truth while making the existing files reachable without copying or
generating templates during the build.
"""

from pathlib import Path


_TEMPLATE_FILES = (
    "app/templates/admin/audit_logs.html",
    "app/templates/admin/roles.html",
    "app/templates/admin/users.html",
    "app/templates/auth/login.html",
    "app/templates/auth/logout.html",
    "app/templates/auth/profile.html",
    "app/templates/auth/register.html",
    "app/templates/base.html",
    "app/templates/budgets/index.html",
    "app/templates/budgets/manage.html",
    "app/templates/contributions/index.html",
    "app/templates/dashboard/index.html",
    "app/templates/documents/list.html",
    "app/templates/documents/upload.html",
    "app/templates/documents/view.html",
    "app/templates/donations/create.html",
    "app/templates/donations/list.html",
    "app/templates/donations/view.html",
    "app/templates/errors/429.html",
    "app/templates/errors/500.html",
    "app/templates/errors/http_error.html",
    "app/templates/expenses/categories.html",
    "app/templates/expenses/create.html",
    "app/templates/expenses/list.html",
    "app/templates/expenses/view.html",
    "app/templates/income/create.html",
    "app/templates/income/list.html",
    "app/templates/income/view.html",
    "app/templates/public/checkout.html",
    "app/templates/public/donate.html",
    "app/templates/public/transparency.html",
    "app/templates/reports/index.html",
    "app/templates/reports/reconciliation.html",
    "app/templates/vendors/create.html",
    "app/templates/vendors/list.html",
)


def verify_template_assets() -> None:
    """Touch every tracked template so the deployment tracer retains it."""
    project_root = Path(__file__).resolve().parent.parent
    missing = []

    for relative_path in _TEMPLATE_FILES:
        template_path = project_root / relative_path
        if not template_path.is_file():
            missing.append(relative_path)
            continue
        # The read is intentional: it creates an explicit runtime dependency on
        # the tracked file without duplicating its contents anywhere else.
        with template_path.open("r", encoding="utf-8") as template_file:
            template_file.read(1)

    if missing:
        raise RuntimeError(
            "Required Jinja template assets are missing: " + ", ".join(missing)
        )
