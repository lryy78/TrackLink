# landing/routes.py
from flask import Blueprint, render_template, request
from landing.utils import log_visit

ALLOWED_BIRTHDAYS = ["030605", "ry5678"]

landing_bp = Blueprint(
    "landing",
    __name__,
    template_folder="templates"
)

@landing_bp.route("/", methods=["GET", "POST"])
def landing():
    birthday_verified = False
    error = None

    if request.method == "POST":
        birthday = request.form.get("birthday", "").strip()
        if birthday in ALLOWED_BIRTHDAYS:
            birthday_verified = True
            log_visit("landing-birthday-unlocked")
        else:
            error = "Invalid birthday"
            log_visit(f"landing-birthday-failed-{birthday}")  # fixed: only one argument
    
    if request.method == "GET":
        log_visit("landing")

    return render_template(
        "landing.html",
        birthday_verified=birthday_verified,
        error=error
    )
