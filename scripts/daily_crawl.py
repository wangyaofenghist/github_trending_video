#!/usr/bin/env python3
"""
每日定时抓取脚本
可通过 cron 执行：0 9 * * * /usr/bin/python3 /path/to/daily_crawl.py
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from app import create_app, db
from app.services.crawler import GitHubCrawler
from app.services.analyzer import ProjectAnalyzer
from app.services.script_generator import ScriptGenerator
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    app = create_app()

    with app.app_context():
        try:
            crawl_date = datetime.now().date()
            logger.info(f"开始执行每日抓取任务，日期：{crawl_date}")

            # 1. 抓取 Trending 项目
            crawler = GitHubCrawler(app.config)
            project_count = crawler.crawl_and_save(crawl_date)
            logger.info(f"抓取完成，共 {project_count} 个项目")

            if project_count == 0:
                logger.info("没有新项目，结束任务")
                return

            # 2. 自动分析所有新项目
            from app.models import TrendingProject
            projects = TrendingProject.query.filter_by(crawl_date=crawl_date).all()

            analyzer = ProjectAnalyzer(app.config)
            analyzed_count = 0

            for project in projects:
                if project.readme_raw and not project.analysis:
                    try:
                        analysis = analyzer.analyze_readme(project)
                        db.session.add(analysis)
                        analyzed_count += 1
                    except Exception as e:
                        logger.error(f"分析项目 {project.full_name} 失败：{e}")
                        continue

            db.session.commit()
            logger.info(f"分析完成，共 {analyzed_count} 个项目")

            # 3. 自动生成文案
            generator = ScriptGenerator(app.config)
            scripted_count = 0

            for project in projects:
                if project.analysis and not project.script:
                    try:
                        script = generator.generate_script(project)
                        db.session.add(script)
                        scripted_count += 1
                    except Exception as e:
                        logger.error(f"生成文案失败 {project.full_name}: {e}")
                        continue

            db.session.commit()
            logger.info(f"文案生成完成，共 {scripted_count} 个")

            logger.info("每日任务执行完毕！")

        except Exception as e:
            logger.error(f"任务执行失败：{e}", exc_info=True)
            sys.exit(1)


if __name__ == '__main__':
    main()
