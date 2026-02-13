from flask import Blueprint

disk_manager = Blueprint('disk_manager', __name__, template_folder='../templates')

from . import routes
