"""Explicitly retain the tracked Jinja templates in Vercel's Python bundle.

Flask/Jinja resolves templates dynamically, so these literal file reads make the
existing app/templates files reachable to Vercel's Python dependency tracer.
The HTML files remain the single source of truth; their contents are never
copied or embedded here.
"""


def verify_template_assets() -> None:
    """Read one byte from every tracked template using literal paths."""
    template_paths = (
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

    missing = []
    for template_path in template_paths:
        try:
            with open(template_path, "rb") as template_file:
                template_file.read(1)
        except FileNotFoundError:
            missing.append(template_path)

    if missing:
        raise RuntimeError(
            "Required Jinja template assets are missing: " + ", ".join(missing)
        )
