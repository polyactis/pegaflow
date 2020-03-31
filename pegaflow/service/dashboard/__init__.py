from flask import Blueprint

dashboard_routes = Blueprint('dashboard_routes', __name__)

from pegaflow.service.dashboard import views

from pegaflow.service import app

app.register_blueprint(dashboard_routes)
