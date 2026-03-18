"""
Routes 包初始化
"""
from app.routes.crawl import crawl_bp
from app.routes.analysis import analysis_bp
from app.routes.script import script_bp
from app.routes.video import video_bp
from app.routes.pages import pages_bp

__all__ = [
    'crawl_bp',
    'analysis_bp',
    'script_bp',
    'video_bp',
    'pages_bp'
]
