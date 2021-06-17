from flask import Blueprint

blueprint = Blueprint("dashboard", __name__)

from pegaflow.service.dashboard import views  # noqa: E402,F401 isort:skip
