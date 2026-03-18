"""
视频任务相关路由
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from app import db
from app.models import TrendingProject, VideoScript, VideoTask, DeepAnalysis, ImageAsset
from app.services.video_generator import VideoGenerator

video_bp = Blueprint('video', __name__)


def calculate_progress(video_task):
    """计算视频生成进度"""
    if video_task.status == 'pending':
        return 0
    elif video_task.status == 'approved':
        # 已审核，等待开始
        return 10
    elif video_task.status == 'generating':
        # 生成中 - 根据已有字段细化进度
        # 如果有图片资源，可以根据已生成图片数量计算进度
        project = video_task.project
        if hasattr(project, 'images'):
            total_images = len(project.images.all()) if hasattr(project, 'images') else 0
            generated_images = len([img for img in project.images.all() if img.is_generated]) if total_images > 0 else 0
            if total_images > 0:
                # 图片生成进度占 50%，视频合成占 50%
                image_progress = int((generated_images / total_images) * 50)
                return 30 + image_progress  # 30% 基础进度 + 图片进度
        return 50  # 默认返回 50%
    elif video_task.status == 'completed':
        return 100
    elif video_task.status == 'failed':
        return 0
    else:
        return 0


def get_status_counts():
    """获取各状态视频任务数量统计"""
    pending_count = VideoTask.query.filter_by(status='pending').count()
    generating_count = VideoTask.query.filter(
        VideoTask.status.in_(['approved', 'generating'])
    ).count()
    completed_count = VideoTask.query.filter_by(status='completed').count()
    failed_count = VideoTask.query.filter_by(status='failed').count()

    return {
        'all': pending_count + generating_count + completed_count + failed_count,
        'generating': generating_count,
        'completed': completed_count,
        'failed': failed_count,
        'pending': pending_count
    }


@video_bp.route('/video/queue', methods=['POST'])
def add_to_queue():
    """将项目加入审核队列"""
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')

        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少 project_id 参数'
            }), 400

        project = TrendingProject.query.get_or_404(project_id)

        if not project.script:
            return jsonify({
                'success': False,
                'message': '请先生成文案'
            }), 400

        # 创建或更新视频任务
        video_task = project.video_task
        if not video_task:
            video_task = VideoTask(
                project_id=project.id,
                script_id=project.script.id,
                status='pending'
            )
            db.session.add(video_task)
        else:
            video_task.status = 'pending'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '已加入审核队列',
            'data': video_task.to_dict()
        })

    except ValueError as e:
        return jsonify({
            'success': False,
            'message': f'配置错误：{str(e)}'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'加入队列失败：{str(e)}'
        }), 500


@video_bp.route('/video/list', methods=['GET'])
def get_video_list():
    """获取视频库列表（支持按状态筛选）"""
    try:
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('page_size', 20, type=int)
        # 状态筛选：all(全部)/generating(生成中)/completed(已完成)/failed(失败)
        status_filter = request.args.get('status', 'all')

        # 构建查询
        query = VideoTask.query

        if status_filter == 'generating':
            # 生成中：approved 或 generating 状态
            query = query.filter(VideoTask.status.in_(['approved', 'generating']))
        elif status_filter == 'completed':
            # 已完成
            query = query.filter_by(status='completed')
        elif status_filter == 'failed':
            # 失败
            query = query.filter_by(status='failed')
        # else: all 或空，返回全部任务

        # 按状态优先级排序（生成中优先，然后是失败，最后是已完成）
        status_priority = db.case(
            {'approved': 1, 'generating': 1, 'failed': 2, 'completed': 3},
            value=VideoTask.status
        )
        query = query.order_by(status_priority, VideoTask.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        items = []
        for task in pagination.items:
            project = task.project
            # 计算进度
            progress = calculate_progress(task)

            item = {
                'id': task.id,
                'task_id': task.id,
                'project_id': project.id,
                'project_name': project.full_name,
                'status': task.status,
                'progress': progress,
                'video_url': task.video_url,
                'video_path': task.video_path,
                'error_message': task.error_message if task.status == 'failed' else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'created_at': task.created_at.isoformat() if task.created_at else None
            }
            items.append(item)

        return jsonify({
            'success': True,
            'data': {
                'items': items,
                'total': pagination.total,
                'page': page,
                'page_size': per_page,
                'status_counts': get_status_counts()  # 各状态数量统计
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取视频列表失败：{str(e)}'
        }), 500


@video_bp.route('/video/generate/batch', methods=['POST'])
def generate_video_batch():
    """批量生成视频（并发执行）"""
    try:
        data = request.get_json() or {}
        project_ids = data.get('project_ids', [])
        max_workers = data.get('max_workers', 3)

        if not project_ids:
            return jsonify({
                'success': False,
                'message': '缺少 project_ids 参数'
            }), 400

        projects = TrendingProject.query.filter(
            TrendingProject.id.in_(project_ids)
        ).all()

        # 过滤掉有文案的项目
        projects_with_script = [p for p in projects if p.script]

        if not projects_with_script:
            return jsonify({
                'success': False,
                'message': '没有可生成视频的项目（缺少文案）'
            }), 400

        # 创建或更新视频任务
        tasks = []
        for project in projects_with_script:
            video_task = project.video_task
            if not video_task:
                video_task = VideoTask(
                    project_id=project.id,
                    script_id=project.script.id,
                    status='approved',
                    approved_at=datetime.utcnow()
                )
                db.session.add(video_task)
            else:
                video_task.status = 'approved'
                video_task.approved_at = datetime.utcnow()
            tasks.append(video_task)

        db.session.commit()

        # 并发执行视频生成
        def generate_single(video_task):
            try:
                # 更新状态为生成中
                video_task.status = 'generating'
                db.session.commit()

                generator = VideoGenerator(current_app.config)
                result = generator.generate_video(video_task.script)

                video_task.video_path = result.get('video_path')
                video_task.video_url = result.get('video_url')
                video_task.status = 'completed'
                video_task.completed_at = datetime.utcnow()
                db.session.commit()

                return {'task_id': video_task.id, 'success': True}
            except Exception as e:
                video_task.status = 'failed'
                video_task.error_message = str(e)
                db.session.commit()
                return {'task_id': video_task.id, 'success': False, 'error': str(e)}

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {executor.submit(generate_single, t): t for t in tasks}
            for future in as_completed(future_to_task):
                results.append(future.result())

        success_count = sum(1 for r in results if r['success'])

        return jsonify({
            'success': True,
            'message': f'批量生成完成，成功{success_count}/{len(tasks)}',
            'data': {
                'total': len(tasks),
                'success_count': success_count,
                'failed_count': len(tasks) - success_count,
                'results': results
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'批量生成失败：{str(e)}'
        }), 500


@video_bp.route('/video/approve', methods=['POST'])
def approve_video():
    """审核通过并触发视频生成（异步）"""
    try:
        data = request.get_json() or {}
        project_ids = data.get('project_ids', [])
        auto_generate = data.get('auto_generate', True)  # 是否自动触发视频生成

        if not project_ids:
            return jsonify({
                'success': False,
                'message': '缺少 project_ids 参数'
            }), 400

        projects = TrendingProject.query.filter(
            TrendingProject.id.in_(project_ids)
        ).all()

        task_ids = []

        for project in projects:
            if not project.script:
                continue

            # 创建或更新视频任务
            video_task = project.video_task
            if not video_task:
                video_task = VideoTask(
                    project_id=project.id,
                    script_id=project.script.id,
                    status='approved',
                    approved_at=datetime.utcnow()
                )
                db.session.add(video_task)
            else:
                video_task.status = 'approved'
                video_task.approved_at = datetime.utcnow()

            db.session.flush()
            task_ids.append(video_task.id)

        db.session.commit()

        # 异步触发视频生成
        if auto_generate:
            # 在线程中执行，不阻塞响应
            from concurrent.futures import ThreadPoolExecutor

            def generate_batch(task_ids):
                with current_app.app_context():
                    for tid in task_ids:
                        try:
                            video_task = VideoTask.query.get(tid)
                            if video_task and video_task.script:
                                video_task.status = 'generating'
                                db.session.commit()

                                generator = VideoGenerator(current_app.config)
                                result = generator.generate_video(video_task.script)

                                video_task.video_path = result.get('video_path')
                                video_task.video_url = result.get('video_url')
                                video_task.status = 'completed'
                                video_task.completed_at = datetime.utcnow()
                                db.session.commit()
                        except Exception as e:
                            if video_task:
                                video_task.status = 'failed'
                                video_task.error_message = str(e)
                                db.session.commit()

            executor = ThreadPoolExecutor(max_workers=3)
            executor.submit(generate_batch, task_ids)

        return jsonify({
            'success': True,
            'message': f'已处理 {len(task_ids)} 个视频任务',
            'data': {
                'queued_count': len(task_ids),
                'task_ids': task_ids
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'审核处理失败：{str(e)}'
        }), 500


@video_bp.route('/video/reject', methods=['POST'])
def reject_video():
    """审核拒绝（跳过）"""
    try:
        data = request.get_json() or {}
        project_ids = data.get('project_ids', [])
        reason = data.get('reason', '')

        if not project_ids:
            return jsonify({
                'success': False,
                'message': '缺少 project_ids 参数'
            }), 400

        projects = TrendingProject.query.filter(
            TrendingProject.id.in_(project_ids)
        ).all()

        for project in projects:
            if not project.video_task:
                video_task = VideoTask(
                    project_id=project.id,
                    script_id=project.script.id if project.script else None,
                    status='rejected'
                )
                db.session.add(video_task)
            else:
                video_task.status = 'rejected'

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'已跳过 {len(project_ids)} 个项目'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'操作失败：{str(e)}'
        }), 500


@video_bp.route('/video/status/<int:task_id>', methods=['GET'])
def get_video_status(task_id):
    """获取视频生成状态"""
    try:
        video_task = VideoTask.query.get_or_404(task_id)
        project = video_task.project

        result = video_task.to_dict()
        result['project_name'] = project.full_name
        result['status'] = video_task.status
        result['progress'] = calculate_progress(video_task)

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取状态失败：{str(e)}'
        }), 500


@video_bp.route('/review/list', methods=['GET'])
def get_review_list():
    """获取审核列表"""
    try:
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('page_size', 20, type=int)
        status = request.args.get('status', 'pending')

        # 查询有文案但视频任务状态为 pending 的项目
        query = TrendingProject.query.join(VideoScript).outerjoin(VideoTask)

        if status == 'pending':
            query = query.filter(
                (VideoTask.id == None) | (VideoTask.status == 'pending')
            )
        elif status == 'approved':
            query = query.filter(VideoTask.status == 'approved')
        elif status == 'rejected':
            query = query.filter(VideoTask.status == 'rejected')
        elif status == 'completed':
            query = query.filter(VideoTask.status == 'completed')

        query = query.order_by(TrendingProject.rank)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        items = []
        for project in pagination.items:
            item = {
                'id': project.id,
                'project_name': project.full_name,
                'rank': project.rank,
                'script_preview': project.script.script_content[:100] + '...' if project.script else '',
                'word_count': project.script.word_count if project.script else 0,
                'status': project.video_task.status if project.video_task else 'pending',
                'created_at': project.script.generated_at.isoformat() if project.script else None,
                'video_url': project.video_task.video_url if project.video_task and project.video_task.video_url else None,
                'has_deep_analysis': project.analysis.deep_analysis is not None if project.analysis else False,
                'images_count': len(project.images.all()) if hasattr(project, 'images') else 0
            }
            items.append(item)

        return jsonify({
            'success': True,
            'data': {
                'items': items,
                'total': pagination.total,
                'page': page,
                'page_size': per_page
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取审核列表失败：{str(e)}'
        }), 500


@video_bp.route('/video/capabilities', methods=['GET'])
def get_capabilities():
    """获取视频生成能力说明"""
    try:
        generator = VideoGenerator(current_app.config)
        capabilities = generator.get_capabilities()

        return jsonify({
            'success': True,
            'data': capabilities
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取能力说明失败：{str(e)}'
        }), 500


@video_bp.route('/video/<int:task_id>', methods=['DELETE'])
def delete_video_task(task_id):
    """删除视频任务"""
    try:
        video_task = VideoTask.query.get_or_404(task_id)

        # 删除视频文件（如果存在）
        import os
        if video_task.video_path and os.path.exists(video_task.video_path):
            os.remove(video_task.video_path)

        db.session.delete(video_task)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '视频任务已删除'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除失败：{str(e)}'
        }), 500


@video_bp.route('/project/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目（包括关联的文案、分析、视频任务等）"""
    try:
        project = TrendingProject.query.get_or_404(project_id)

        # 删除关联的视频文件
        import os
        if project.video_task and project.video_task.video_path:
            if os.path.exists(project.video_task.video_path):
                os.remove(project.video_task.video_path)

        # 删除关联的图片文件
        for image in project.images.all():
            if image.image_path and os.path.exists(image.image_path):
                os.remove(image.image_path)

        db.session.delete(project)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '项目已删除'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除失败：{str(e)}'
        }), 500

