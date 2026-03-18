"""
页面路由 - Web 界面
"""
from flask import Blueprint, render_template, jsonify
from app import db
from app.models import TrendingProject, VideoScript, VideoTask, DeepAnalysis, ImageAsset
from datetime import datetime

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    """首页 - 项目管理面板"""
    # 获取最新抓取日期的数据
    latest_date = db.session.query(
        db.func.max(TrendingProject.crawl_date)
    ).scalar()

    stats = {
        'total_projects': 0,
        'analyzed': 0,
        'scripted': 0,
        'video_generated': 0
    }

    if latest_date:
        projects = TrendingProject.query.filter_by(crawl_date=latest_date).all()
        stats['total_projects'] = len(projects)
        stats['analyzed'] = sum(1 for p in projects if p.analysis)
        stats['scripted'] = sum(1 for p in projects if p.script)
        stats['video_generated'] = sum(1 for p in projects if p.video_task and p.video_task.status == 'completed')

    return render_template('index.html', latest_date=latest_date, stats=stats)


@pages_bp.route('/review')
def review_page():
    """审核页面"""
    return render_template('review.html')


@pages_bp.route('/projects/<int:project_id>')
def project_detail(project_id):
    """项目详情页"""
    project = TrendingProject.query.get_or_404(project_id)

    # 获取深度分析
    deep_analysis = None
    has_deep_analysis = False
    if project.analysis and project.analysis.deep_analysis:
        deep_analysis = project.analysis.deep_analysis
        has_deep_analysis = True

    # 获取图片资源
    images = project.images.all() if hasattr(project, 'images') else []
    images_count = len(images)

    # 检查是否已加入审核队列
    has_queued = project.video_task is not None

    return render_template('project_detail.html',
        project=project,
        has_deep_analysis=has_deep_analysis,
        deep_analysis=deep_analysis,
        images_count=images_count,
        images=images,
        has_queued=has_queued)


@pages_bp.route('/api/projects/<int:project_id>')
def project_detail_api(project_id):
    """项目详情 API"""
    project = TrendingProject.query.get_or_404(project_id)

    result = project.to_dict()

    # 添加基础分析
    if project.analysis:
        result['analysis'] = project.analysis.to_dict()
        # 添加深度分析
        if project.analysis.deep_analysis:
            result['has_deep_analysis'] = True
            result['deep_analysis'] = project.analysis.deep_analysis.to_dict()
        else:
            result['has_deep_analysis'] = False
            result['deep_analysis'] = None

    # 添加文案
    if project.script:
        result['script'] = project.script.to_dict()

    # 添加图片资源
    if hasattr(project, 'images'):
        result['images'] = [img.to_dict() for img in project.images.all()]

    # 添加视频任务
    if project.video_task:
        result['video_task'] = project.video_task.to_dict()

    return jsonify({
        'success': True,
        'data': result
    })


@pages_bp.route('/scripts/<int:script_id>/edit')
def script_edit(script_id):
    """文案编辑页"""
    script = VideoScript.query.get_or_404(script_id)
    return render_template('script_edit.html', script=script)


@pages_bp.route('/videos')
def videos_page():
    """视频库页面"""
    # 前端使用 JavaScript 异步加载数据，这里只渲染模板
    return render_template('videos.html', tasks=[])
