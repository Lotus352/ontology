from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.routes.courses import courses_bp
from app.routes.structure import structure_bp
from app.routes.search import search_bp
from app.routes.auth import auth_bp
from app.routes.user import user_bp
from app.routes.user_courses import user_courses_bp
from app.routes.contents import contents_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Enable CORS for all routes and origins
    CORS(app)

    # Register blueprints
    app.register_blueprint(courses_bp)
    app.register_blueprint(structure_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(user_courses_bp)
    app.register_blueprint(contents_bp)

    
    @app.route('/', methods=['GET'])
    def hello():
        return "Hello, World!"

    return app
