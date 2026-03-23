from app import db
from datetime import datetime
import json


class CrawlBatch(db.Model):
    """抓取批次表 - 记录每次抓取的元数据"""
    __tablename__ = 'crawl_batches'

    id = db.Column(db.Integer, primary_key=True)
    crawl_date = db.Column(db.Date, nullable=False, index=True, unique=True)  # 每天只记录一次抓取批次
    projects_count = db.Column(db.Integer, default=0)  # 抓取的项目数量
    status = db.Column(db.String(50), default='completed')  # completed/failed/partial
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'crawl_date': self.crawl_date.isoformat() if self.crawl_date else None,
            'projects_count': self.projects_count,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TrendingProject(db.Model):
    """GitHub Trending 项目表"""
    __tablename__ = 'trending_projects'

    id = db.Column(db.Integer, primary_key=True)
    crawl_date = db.Column(db.Date, nullable=False, index=True)
    rank = db.Column(db.Integer, nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(300), nullable=False, index=True)  # 移除 unique=True，允许同一项目多条记录
    description = db.Column(db.Text)
    language = db.Column(db.String(50))
    stars = db.Column(db.Integer, default=0)
    forks = db.Column(db.Integer, default=0)
    topics = db.Column(db.Text)  # JSON 字符串
    readme_raw = db.Column(db.Text)  # README 原始内容
    readme_url = db.Column(db.String(500))
    html_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联关系
    analysis = db.relationship('ProjectAnalysis', backref='project', uselist=False, cascade='all, delete-orphan')
    script = db.relationship('VideoScript', backref='project', uselist=False, cascade='all, delete-orphan')
    video_task = db.relationship('VideoTask', backref='project', uselist=False, cascade='all, delete-orphan')
    images = db.relationship('ImageAsset', backref='project', lazy='dynamic', cascade='all, delete-orphan')

    @staticmethod
    def get_history(full_name, limit=10):
        """获取项目的历史上榜记录"""
        return TrendingProject.query.filter_by(full_name=full_name)\
            .order_by(TrendingProject.crawl_date.desc())\
            .limit(limit).all()

    @staticmethod
    def get_by_date(crawl_date):
        """获取指定日期的抓取列表"""
        return TrendingProject.query.filter_by(crawl_date=crawl_date)\
            .order_by(TrendingProject.rank).all()

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'crawl_date': self.crawl_date.isoformat() if self.crawl_date else None,
            'rank': self.rank,
            'owner': self.owner,
            'name': self.name,
            'full_name': self.full_name,
            'description': self.description,
            'language': self.language,
            'stars': self.stars,
            'forks': self.forks,
            'topics': json.loads(self.topics) if self.topics else [],
            'readme_url': self.readme_url,
            'html_url': self.html_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'has_analysis': self.analysis is not None,
            'has_deep_analysis': self.analysis.deep_analysis is not None if self.analysis else False,
            'has_script': self.script is not None,
            'video_status': self.video_task.status if self.video_task else None,
            'images_count': self.images.count() if hasattr(self, 'images') else 0
        }


class ProjectAnalysis(db.Model):
    """项目分析表"""
    __tablename__ = 'project_analysis'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('trending_projects.id'), nullable=False)
    use_cases = db.Column(db.Text)  # 适用范围
    features = db.Column(db.Text)  # JSON 字符串
    purpose = db.Column(db.Text)  # 主要用途
    install_command = db.Column(db.String(500))
    quick_start = db.Column(db.Text)
    official_docs = db.Column(db.String(500))
    analysis_raw = db.Column(db.Text)
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联深度分析
    deep_analysis = db.relationship('DeepAnalysis', backref='analysis', uselist=False, cascade='all, delete-orphan')

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'use_cases': self.use_cases,
            'features': json.loads(self.features) if self.features else [],
            'purpose': self.purpose,
            'install_command': self.install_command,
            'quick_start': self.quick_start,
            'official_docs': self.official_docs,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None
        }


class VideoScript(db.Model):
    """视频文案表"""
    __tablename__ = 'video_scripts'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('trending_projects.id'), nullable=False)
    script_title = db.Column(db.String(300))
    script_content = db.Column(db.Text)
    hook_opening = db.Column(db.Text)
    key_highlights = db.Column(db.Text)  # JSON 字符串
    call_to_action = db.Column(db.Text)
    word_count = db.Column(db.Integer, default=0)
    estimated_duration = db.Column(db.Integer, default=0)  # 秒
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'script_title': self.script_title,
            'script_content': self.script_content,
            'hook_opening': self.hook_opening,
            'key_highlights': json.loads(self.key_highlights) if self.key_highlights else [],
            'call_to_action': self.call_to_action,
            'word_count': self.word_count,
            'estimated_duration': self.estimated_duration,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None
        }


class VideoTask(db.Model):
    """视频任务表"""
    __tablename__ = 'video_tasks'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('trending_projects.id'), nullable=False)
    script_id = db.Column(db.Integer, db.ForeignKey('video_scripts.id'))
    status = db.Column(db.String(50), default='pending')  # pending/approved/rejected/generating/completed/failed
    video_path = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    error_message = db.Column(db.Text)
    approved_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关联 script
    script = db.relationship('VideoScript', backref='video_tasks')

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'script_id': self.script_id,
            'status': self.status,
            'video_path': self.video_path,
            'video_url': self.video_url,
            'error_message': self.error_message,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DeepAnalysis(db.Model):
    """深度分析表 - 包含使用场景、团队、前景等"""
    __tablename__ = 'deep_analysis'

    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('project_analysis.id'), nullable=False)

    # 深度分析内容
    use_case_scenarios = db.Column(db.Text)  # 详细使用场景
    team_info = db.Column(db.Text)  # 开源团队信息
    market_prospects = db.Column(db.Text)  # 市场前景/趋势
    tech_stack = db.Column(db.Text)  # 技术栈分析
    competitors = db.Column(db.Text)  # 竞品分析
    summary = db.Column(db.Text)  # 综合总结

    analysis_raw = db.Column(db.Text)  # LLM 原始返回
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'analysis_id': self.analysis_id,
            'use_case_scenarios': self.use_case_scenarios,
            'team_info': self.team_info,
            'market_prospects': self.market_prospects,
            'tech_stack': self.tech_stack,
            'competitors': self.competitors,
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ImageAsset(db.Model):
    """图片资源表 - 用于视频生成的素材"""
    __tablename__ = 'image_assets'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('trending_projects.id'), nullable=False)

    image_type = db.Column(db.String(50))  # screenshot/architecture/flowchart/promo
    image_path = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    description = db.Column(db.Text)  # 图片描述
    prompt = db.Column(db.Text)  # 生成图片用的 prompt
    is_generated = db.Column(db.Boolean, default=False)  # 是否是 AI 生成的
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'image_type': self.image_type,
            'image_path': self.image_path,
            'image_url': self.image_url,
            'description': self.description,
            'prompt': self.prompt,
            'is_generated': self.is_generated,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
