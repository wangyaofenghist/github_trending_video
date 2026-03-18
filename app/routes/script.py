"""
文案相关路由
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import TrendingProject, VideoScript
from app.services.script_generator import ScriptGenerator

script_bp = Blueprint('script', __name__)


@script_bp.route('/script/generate', methods=['POST'])
def generate_script():
    """生成视频文案"""
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')
        style = data.get('style', 'tech_review')
        duration = data.get('duration', 60)

        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少 project_id 参数'
            }), 400

        project = TrendingProject.query.get_or_404(project_id)

        if not project.analysis:
            return jsonify({
                'success': False,
                'message': '该项目尚未分析，请先执行分析'
            }), 400

        if project.script:
            return jsonify({
                'success': False,
                'message': '该项目文案已生成'
            }), 400

        # 生成文案
        generator = ScriptGenerator(current_app.config)
        script = generator.generate_script(project, style, duration)

        db.session.add(script)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '文案生成完成',
            'data': script.to_dict()
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
            'message': f'文案生成失败：{str(e)}'
        }), 500


@script_bp.route('/script/<int:script_id>', methods=['PUT'])
def update_script(script_id):
    """更新文案"""
    try:
        data = request.get_json() or {}
        script = VideoScript.query.get_or_404(script_id)

        # 更新允许的字段
        if 'script_content' in data:
            script.script_content = data['script_content']
            script.word_count = len(data['script_content'])
        if 'script_title' in data:
            script.script_title = data['script_title']
        if 'hook_opening' in data:
            script.hook_opening = data['hook_opening']
        if 'key_highlights' in data:
            import json
            script.key_highlights = json.dumps(data['key_highlights'], ensure_ascii=False)
        if 'call_to_action' in data:
            script.call_to_action = data['call_to_action']
        if 'estimated_duration' in data:
            script.estimated_duration = data['estimated_duration']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '文案已更新',
            'data': script.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新失败：{str(e)}'
        }), 500


@script_bp.route('/script/<int:script_id>', methods=['GET'])
def get_script(script_id):
    """获取文案详情"""
    try:
        script = VideoScript.query.get_or_404(script_id)

        return jsonify({
            'success': True,
            'data': script.to_dict()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取文案失败：{str(e)}'
        }), 500


@script_bp.route('/video-script/<int:script_id>', methods=['PUT'])
def update_video_script(script_id):
    """更新文案（别名接口，兼容前端调用）"""
    try:
        data = request.get_json() or {}
        script = VideoScript.query.get_or_404(script_id)

        # 更新允许的字段
        if 'script_content' in data:
            script.script_content = data['script_content']
            script.word_count = len(data['script_content'])
        if 'script_title' in data:
            script.script_title = data['script_title']
        if 'hook_opening' in data:
            script.hook_opening = data['hook_opening']
        if 'key_highlights' in data:
            import json
            script.key_highlights = json.dumps(data['key_highlights'], ensure_ascii=False)
        if 'call_to_action' in data:
            script.call_to_action = data['call_to_action']
        if 'estimated_duration' in data:
            script.estimated_duration = data['estimated_duration']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '文案已更新',
            'data': script.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新失败：{str(e)}'
        }), 500


@script_bp.route('/video-script/<int:script_id>', methods=['GET'])
def get_video_script(script_id):
    """获取文案详情（别名接口，兼容前端调用）"""
    try:
        script = VideoScript.query.get_or_404(script_id)

        return jsonify({
            'success': True,
            'data': script.to_dict()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取文案失败：{str(e)}'
        }), 500


@script_bp.route('/script/generate/batch', methods=['POST'])
def generate_script_batch():
    """批量生成视频文案（并发执行）"""
    try:
        data = request.get_json() or {}
        project_ids = data.get('project_ids', [])
        style = data.get('style', 'tech_review')
        duration = data.get('duration', 60)
        max_workers = data.get('max_workers')  # 支持自定义并发数（可选）
        max_retries = data.get('max_retries')  # 支持自定义重试次数
        timeout = data.get('timeout')  # 支持自定义超时时间

        if not project_ids:
            return jsonify({
                'success': False,
                'message': '缺少 project_ids 参数'
            }), 400

        projects = TrendingProject.query.filter(
            TrendingProject.id.in_(project_ids)
        ).all()

        # 过滤掉已有文案的项目
        projects_to_generate = [p for p in projects if not p.script]

        if not projects_to_generate:
            return jsonify({
                'success': False,
                'message': '所有项目都已生成过文案'
            }), 400

        # 生成文案
        generator = ScriptGenerator(current_app.config)
        results = generator.generate_script_batch(
            projects_to_generate,
            style=style,
            duration=duration,
            max_workers=max_workers,
            max_retries=max_retries,
            timeout=timeout
        )

        # 保存成功生成的文案到数据库
        success_count = 0
        api_results = []
        for result in results:
            if result['success'] and 'script' in result:
                db.session.add(result['script'])
                success_count += 1
                # 转换为可序列化的格式
                api_results.append({
                    'project_id': result['project_id'],
                    'success': True,
                    'script': result['script'].to_dict()
                })
            else:
                api_results.append(result)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'批量生成完成，成功{success_count}/{len(projects_to_generate)}',
            'data': {
                'total': len(projects_to_generate),
                'success_count': success_count,
                'failed_count': len(projects_to_generate) - success_count,
                'results': api_results
            }
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
            'message': f'批量生成失败：{str(e)}'
        }), 500

