"""
抓取相关路由
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from app import db
from app.models import TrendingProject
from app.services.crawler import GitHubCrawler
from flask import current_app
import logging

logger = logging.getLogger(__name__)

crawl_bp = Blueprint('crawl', __name__)


@crawl_bp.route('/crawl', methods=['POST'])
def trigger_crawl():
    """手动触发抓取"""
    try:
        data = request.get_json() or {}
        date_str = data.get('date')

        if date_str:
            crawl_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            crawl_date = datetime.now().date()

        # 执行抓取
        crawler = GitHubCrawler(current_app.config)
        count = crawler.crawl_and_save(crawl_date)

        return jsonify({
            'success': True,
            'message': '抓取完成',
            'data': {
                'crawled_count': count,
                'crawl_date': crawl_date.isoformat()
            }
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'日期格式错误：{str(e)}'
        }), 400
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Crawl error: {error_detail}")
        return jsonify({
            'success': False,
            'message': f'抓取失败：{str(e)}'
        }), 500


@crawl_bp.route('/projects', methods=['GET'])
def get_projects():
    """获取项目列表"""
    try:
        # 解析参数
        date_str = request.args.get('date')
        status = request.args.get('status')

        # 基础查询
        query = TrendingProject.query

        # 按日期筛选
        if date_str:
            crawl_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter_by(crawl_date=crawl_date)
        else:
            # 默认返回最新日期的数据
            latest_date = db.session.query(
                db.func.max(TrendingProject.crawl_date)
            ).scalar()
            if latest_date:
                query = query.filter_by(crawl_date=latest_date)

        # 按状态筛选（是否有分析/文案/视频任务）
        if status == 'pending_analysis':
            query = query.outerjoin(
                TrendingProject.analysis
            ).filter(TrendingProject.analysis == None)
        elif status == 'pending_script':
            query = query.join(
                TrendingProject.analysis
            ).outerjoin(
                TrendingProject.script
            ).filter(TrendingProject.script == None)
        elif status == 'pending_video':
            query = query.join(
                TrendingProject.script
            ).outerjoin(
                TrendingProject.video_task
            ).filter(
                (TrendingProject.video_task == None) |
                (TrendingProject.video_task.status == 'pending')
            )

        # 按排名排序
        query = query.order_by(TrendingProject.rank)

        # 分页
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 25, type=int)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        projects = [p.to_dict() for p in pagination.items]

        return jsonify({
            'success': True,
            'data': {
                'projects': projects,
                'total': pagination.total,
                'page': page,
                'per_page': per_page,
                'pages': pagination.pages
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取项目列表失败：{str(e)}'
        }), 500


@crawl_bp.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """获取单个项目详情"""
    try:
        project = TrendingProject.query.get_or_404(project_id)

        result = project.to_dict()
        if project.analysis:
            result['analysis'] = project.analysis.to_dict()
            # 包含深度分析
            if project.analysis.deep_analysis:
                result['deep_analysis'] = project.analysis.deep_analysis.to_dict()
                result['has_deep_analysis'] = True
        if project.script:
            result['script'] = project.script.to_dict()
        if project.video_task:
            result['video_task'] = project.video_task.to_dict()

        # 包含图片素材
        if hasattr(project, 'images'):
            result['images'] = [img.to_dict() for img in project.images.all()]

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取项目详情失败：{str(e)}'
        }), 500
