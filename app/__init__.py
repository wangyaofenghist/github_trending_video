"""
GitHub Trending 视频生成系统
"""
import os
from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config import Config
import json

# 初始化扩展
db = SQLAlchemy()

def create_app(config_class=Config):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    CORS(app)

    # 注册静态文件路由 - 用于提供视频文件服务
    @app.route('/videos/<path:filename>')
    def serve_video(filename):
        """提供视频文件服务"""
        video_dir = os.path.abspath(app.config.get('VIDEO_OUTPUT_DIR', './videos'))
        return send_from_directory(video_dir, filename)

    # 注册自定义过滤器
    @app.template_filter('from_json')
    def from_json_filter(value):
        """将 JSON 字符串解析为 Python 对象"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []

    # 注册蓝图
    from app.routes.crawl import crawl_bp
    from app.routes.analysis import analysis_bp
    from app.routes.script import script_bp
    from app.routes.video import video_bp
    from app.routes.pages import pages_bp

    app.register_blueprint(crawl_bp, url_prefix='/api')
    app.register_blueprint(analysis_bp, url_prefix='/api')
    app.register_blueprint(script_bp, url_prefix='/api')
    app.register_blueprint(video_bp, url_prefix='/api')
    app.register_blueprint(pages_bp)

    # 创建数据库表
    with app.app_context():
        db.create_all()

    return app
