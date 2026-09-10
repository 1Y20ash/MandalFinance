"""Make the three dynamically loaded public Jinja templates explicit bundle dependencies.

Most application templates are already reachable through Python imports. The public
blueprint is the exceptional case: its templates are selected dynamically by Flask,
so Vercel's Python tracer does not retain them. These literal reads keep the tracked
HTML files as the only source of truth and do not generate or copy templates.
"""


def verify_public_template_assets() -> None:
    """Read the public templates through literal paths so Vercel retains them."""
    missing = []

    try:
        with open("app/templates/public/checkout.html", "rb") as template_file:
            template_file.read(1)
    except FileNotFoundError:
        missing.append("app/templates/public/checkout.html")

    try:
        with open("app/templates/public/donate.html", "rb") as template_file:
            template_file.read(1)
    except FileNotFoundError:
        missing.append("app/templates/public/donate.html")

    try:
        with open("app/templates/public/transparency.html", "rb") as template_file:
            template_file.read(1)
    except FileNotFoundError:
        missing.append("app/templates/public/transparency.html")

    if missing:
        raise RuntimeError(
            "Required public Jinja template assets are missing: " + ", ".join(missing)
        )
