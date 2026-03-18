"""
分析相关路由
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models import TrendingProject, ProjectAnalysis, DeepAnalysis, ImageAsset
from app.services.analyzer import ProjectAnalyzer
from app.services.deep_analyzer import DeepAnalyzer
from app.services.image_generator import ImageGenerator

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/analyze', methods=['POST'])
def analyze_project():
    """分析单个项目"""
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')

        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少 project_id 参数'
            }), 400

        project = TrendingProject.query.get_or_404(project_id)

        if not project.readme_raw:
            return jsonify({
                'success': False,
                'message': '该项目没有 README 内容'
            }), 400

        if project.analysis:
            return jsonify({
                'success': False,
                'message': '该项目已分析过'
            }), 400

        # 执行分析
        analyzer = ProjectAnalyzer(current_app.config)
        analysis = analyzer.analyze_readme(project)

        db.session.add(analysis)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '分析完成',
            'data': analysis.to_dict()
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
            'message': f'分析失败：{str(e)}'
        }), 500


@analysis_bp.route('/analyze/batch', methods=['POST'])
def analyze_batch():
    """批量分析项目（并发执行）"""
    try:
        data = request.get_json() or {}
        project_ids = data.get('project_ids', [])
        max_workers = data.get('max_workers')  # 支持自定义并发数（可选，默认使用配置）
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

        # 过滤掉已分析的项目
        projects_to_analyze = [p for p in projects if not p.analysis]

        if not projects_to_analyze:
            return jsonify({
                'success': False,
                'message': '所有项目都已分析过'
            }), 400

        analyzer = ProjectAnalyzer(current_app.config)
        results = analyzer.analyze_batch(
            projects_to_analyze,
            max_workers=max_workers,
            max_retries=max_retries,
            timeout=timeout
        )

        # 保存成功分析的结果到数据库
        success_count = 0
        api_results = []
        for result in results:
            if result['success'] and 'analysis' in result:
                db.session.add(result['analysis'])
                success_count += 1
                # 转换为可序列化的格式
                api_results.append({
                    'project_id': result['project_id'],
                    'success': True,
                    'analysis': result['analysis'].to_dict()
                })
            else:
                api_results.append(result)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'批量分析完成，成功{success_count}/{len(projects_to_analyze)}',
            'data': {
                'total': len(projects_to_analyze),
                'success_count': success_count,
                'failed_count': len(projects_to_analyze) - success_count,
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
            'message': f'批量分析失败：{str(e)}'
        }), 500


@analysis_bp.route('/analyze/deep', methods=['POST'])
def deep_analyze_project():
    """深度分析单个项目"""
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')

        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少 project_id 参数'
            }), 400

        project = TrendingProject.query.get_or_404(project_id)

        if not project.readme_raw:
            return jsonify({
                'success': False,
                'message': '该项目没有 README 内容'
            }), 400

        if not project.analysis:
            return jsonify({
                'success': False,
                'message': '请先完成基础分析'
            }), 400

        if project.analysis.deep_analysis:
            return jsonify({
                'success': False,
                'message': '该项目已深度分析过'
            }), 400

        # 执行深度分析
        analyzer = DeepAnalyzer(current_app.config)
        analysis = analyzer.analyze(project)

        db.session.add(analysis)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '深度分析完成',
            'data': analysis.to_dict()
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
            'message': f'深度分析失败：{str(e)}'
        }), 500


@analysis_bp.route('/analyze/deep/batch', methods=['POST'])
def deep_analyze_batch():
    """批量深度分析项目（并发执行）"""
    try:
        data = request.get_json() or {}
        project_ids = data.get('project_ids', [])
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

        # 过滤掉已完成基础分析但未深度分析的项目
        projects_to_analyze = [p for p in projects if p.analysis and not p.analysis.deep_analysis]

        if not projects_to_analyze:
            return jsonify({
                'success': False,
                'message': '所有项目都已深度分析过，或尚未完成基础分析'
            }), 400

        analyzer = DeepAnalyzer(current_app.config)
        results = analyzer.analyze_batch(
            projects_to_analyze,
            max_workers=max_workers,
            max_retries=max_retries,
            timeout=timeout
        )

        # 保存成功分析的结果到数据库
        success_count = 0
        api_results = []
        for result in results:
            if result['success'] and 'analysis' in result:
                db.session.add(result['analysis'])
                success_count += 1
                # 转换为可序列化的格式
                api_results.append({
                    'project_id': result['project_id'],
                    'success': True,
                    'analysis': result['analysis'].to_dict()
                })
            else:
                api_results.append(result)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'批量深度分析完成，成功{success_count}/{len(projects_to_analyze)}',
            'data': {
                'total': len(projects_to_analyze),
                'success_count': success_count,
                'failed_count': len(projects_to_analyze) - success_count,
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
            'message': f'批量深度分析失败：{str(e)}'
        }), 500


@analysis_bp.route('/analyze/images', methods=['POST'])
def generate_image_prompts():
    """生成项目图片提示词"""
    try:
        data = request.get_json() or {}
        project_id = data.get('project_id')

        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少 project_id 参数'
            }), 400

        project = TrendingProject.query.get_or_404(project_id)

        if not project.analysis:
            return jsonify({
                'success': False,
                'message': '请先完成基础分析'
            }), 400

        # 生成图片提示词
        generator = ImageGenerator(current_app.config)
        prompts = generator.generate_prompts(project)

        # 保存图片记录
        saved_images = []
        for prompt_data in prompts:
            image = generator.save_image_record(
                project_id=project_id,
                image_type=prompt_data.get('type', 'promo'),
                description=prompt_data.get('description', ''),
                prompt=prompt_data.get('prompt', '')
            )
            db.session.add(image)
            saved_images.append(image.to_dict())

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'生成{len(prompts)}个图片提示词',
            'data': {
                'prompts': prompts,
                'images': saved_images
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
            'message': f'生成图片提示词失败：{str(e)}'
        }), 500


@analysis_bp.route('/analyze/images/batch', methods=['POST'])
def generate_image_prompts_batch():
    """批量生成图片提示词（并发执行）"""
    try:
        data = request.get_json() or {}
        project_ids = data.get('project_ids', [])
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

        # 过滤掉已完成基础分析的项目
        projects_to_process = [p for p in projects if p.analysis]

        if not projects_to_process:
            return jsonify({
                'success': False,
                'message': '没有需要生成的项目（都未完成基础分析）'
            }), 400

        generator = ImageGenerator(current_app.config)
        results = generator.generate_prompts_batch(
            projects_to_process,
            max_workers=max_workers,
            max_retries=max_retries,
            timeout=timeout
        )

        # 保存成功生成的图片记录到数据库
        total_prompts = 0
        success_count = 0
        for result in results:
            if result['success'] and 'prompts' in result:
                project_id = result['project_id']
                for prompt_data in result['prompts']:
                    image = generator.save_image_record(
                        project_id=project_id,
                        image_type=prompt_data.get('type', 'promo'),
                        description=prompt_data.get('description', ''),
                        prompt=prompt_data.get('prompt', '')
                    )
                    db.session.add(image)
                success_count += 1
                total_prompts += len(result['prompts'])

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'批量生成完成，共生成{total_prompts}个图片提示词',
            'data': {
                'total': len(projects_to_process),
                'success_count': success_count,
                'failed_count': len(projects_to_process) - success_count,
                'total_prompts': total_prompts,
                'results': results
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
            'message': f'批量生成图片提示词失败：{str(e)}'
        }), 500


@analysis_bp.route('/analysis/<int:analysis_id>', methods=['PUT'])
def update_analysis(analysis_id):
    """更新基础分析"""
    try:
        data = request.get_json() or {}
        analysis = ProjectAnalysis.query.get_or_404(analysis_id)

        if 'use_cases' in data:
            analysis.use_cases = data['use_cases']
        if 'purpose' in data:
            analysis.purpose = data['purpose']
        if 'features' in data:
            import json
            analysis.features = json.dumps(data['features'], ensure_ascii=False)
        if 'install_command' in data:
            analysis.install_command = data['install_command']
        if 'quick_start' in data:
            analysis.quick_start = data['quick_start']
        if 'official_docs' in data:
            analysis.official_docs = data['official_docs']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '基础分析已更新',
            'data': analysis.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新失败：{str(e)}'
        }), 500


@analysis_bp.route('/deep-analysis/<int:deep_id>', methods=['PUT'])
def update_deep_analysis(deep_id):
    """更新深度分析"""
    try:
        data = request.get_json() or {}
        deep = DeepAnalysis.query.get_or_404(deep_id)

        if 'use_case_scenarios' in data:
            deep.use_case_scenarios = data['use_case_scenarios']
        if 'team_info' in data:
            deep.team_info = data['team_info']
        if 'market_prospects' in data:
            deep.market_prospects = data['market_prospects']
        if 'tech_stack' in data:
            deep.tech_stack = data['tech_stack']
        if 'competitors' in data:
            deep.competitors = data['competitors']
        if 'summary' in data:
            deep.summary = data['summary']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '深度分析已更新',
            'data': deep.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新失败：{str(e)}'
        }), 500


@analysis_bp.route('/images/<int:image_id>', methods=['PUT'])
def update_image(image_id):
    """更新图片记录"""
    try:
        data = request.get_json() or {}
        image = ImageAsset.query.get_or_404(image_id)

        if 'image_type' in data:
            image.image_type = data['image_type']
        if 'description' in data:
            image.description = data['description']
        if 'prompt' in data:
            image.prompt = data['prompt']
        if 'image_path' in data:
            image.image_path = data['image_path']
        if 'image_url' in data:
            image.image_url = data['image_url']
        if 'is_generated' in data:
            image.is_generated = data['is_generated']

        db.session.commit()

        return jsonify({
            'success': True,
            'message': '图片记录已更新',
            'data': image.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'更新失败：{str(e)}'
        }), 500


@analysis_bp.route('/images/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    """删除图片记录"""
    try:
        image = ImageAsset.query.get_or_404(image_id)
        db.session.delete(image)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '图片已删除'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'删除失败：{str(e)}'
        }), 500


@analysis_bp.route('/images', methods=['GET'])
def list_images():
    """获取图片列表（支持分页、筛选）"""
    try:
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('page_size', 20, type=int)

        # 筛选参数
        project_id = request.args.get('project_id', type=int)
        image_type = request.args.get('image_type', type=str)
        is_generated = request.args.get('is_generated', type=str)

        # 构建查询
        query = ImageAsset.query

        if project_id:
            query = query.filter_by(project_id=project_id)
        if image_type:
            query = query.filter_by(image_type=image_type)
        if is_generated is not None:
            is_generated_bool = is_generated.lower() == 'true'
            query = query.filter_by(is_generated=is_generated_bool)

        # 按创建时间倒序
        query = query.order_by(ImageAsset.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        items = [image.to_dict() for image in pagination.items]

        return jsonify({
            'success': True,
            'data': {
                'items': items,
                'total': pagination.total,
                'page': page,
                'page_size': per_page,
                'total_pages': (pagination.total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取图片列表失败：{str(e)}'
        }), 500


@analysis_bp.route('/images/<int:image_id>', methods=['GET'])
def get_image(image_id):
    """获取单个图片详情"""
    try:
        image = ImageAsset.query.get_or_404(image_id)

        return jsonify({
            'success': True,
            'data': image.to_dict()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取图片详情失败：{str(e)}'
        }), 500


@analysis_bp.route('/images/generate', methods=['POST'])
def generate_images():
    """触发 AI 生成图片（基于已有的 prompt）"""
    try:
        data = request.get_json() or {}
        image_ids = data.get('image_ids', [])

        if not image_ids:
            return jsonify({
                'success': False,
                'message': '缺少 image_ids 参数'
            }), 400

        images = ImageAsset.query.filter(ImageAsset.id.in_(image_ids)).all()

        if not images:
            return jsonify({
                'success': False,
                'message': '未找到指定的图片记录'
            }), 400

        generator = ImageGenerator(current_app.config)
        results = []

        for image in images:
            if not image.prompt:
                results.append({
                    'image_id': image.id,
                    'success': False,
                    'error': '缺少 AI 绘画提示词'
                })
                continue

            try:
                # 调用 AI 绘画 API 生成图片
                gen_result = generator.generate_image_with_ai(image.prompt, image.image_type)

                if gen_result.get('success'):
                    # 更新图片记录
                    image.image_path = gen_result.get('image_path', '')
                    image.image_url = gen_result.get('image_url', '')
                    image.is_generated = True
                    db.session.commit()

                    results.append({
                        'image_id': image.id,
                        'success': True,
                        'image_url': gen_result.get('image_url')
                    })
                else:
                    results.append({
                        'image_id': image.id,
                        'success': False,
                        'error': gen_result.get('message', '生成失败')
                    })
            except Exception as e:
                results.append({
                    'image_id': image.id,
                    'success': False,
                    'error': str(e)
                })

        success_count = sum(1 for r in results if r['success'])

        return jsonify({
            'success': True,
            'message': f'生成完成，成功{success_count}/{len(images)}',
            'data': {
                'total': len(images),
                'success_count': success_count,
                'failed_count': len(images) - success_count,
                'results': results
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'生成图片失败：{str(e)}'
        }), 500


@analysis_bp.route('/images/upload', methods=['POST'])
def upload_image():
    """上传图片文件"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '缺少文件'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '未选择文件'
            }), 400

        project_id = request.form.get('project_id', type=int)
        image_type = request.form.get('image_type', 'other')
        description = request.form.get('description', '')

        if not project_id:
            return jsonify({
                'success': False,
                'message': '缺少 project_id 参数'
            }), 400

        # 保存图片文件
        from werkzeug.utils import secure_filename
        import os
        from datetime import datetime

        upload_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', './uploads'), 'images')
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # 创建图片记录
        image = ImageAsset(
            project_id=project_id,
            image_type=image_type,
            image_path=filepath,
            image_url=f'/uploads/images/{filename}',
            description=description,
            is_generated=False
        )
        db.session.add(image)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '图片上传成功',
            'data': image.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'上传失败：{str(e)}'
        }), 500
