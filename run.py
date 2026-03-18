#!/usr/bin/env python3
"""
GitHub Trending 视频生成系统 - 主程序入口
"""
import click
from app import create_app, db
from app.models import TrendingProject, ProjectAnalysis, VideoScript, VideoTask
import os

app = create_app()


@app.cli.command()
def init_db():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        print("数据库初始化完成！")


@app.cli.command()
@click.option('--date', help='抓取日期 (YYYY-MM-DD)', default=None)
def crawl(date):
    """执行抓取任务"""
    from datetime import datetime
    from app.services.crawler import GitHubCrawler
    from flask import current_app

    with app.app_context():
        if date:
            crawl_date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            crawl_date = datetime.now().date()

        crawler = GitHubCrawler(current_app.config)
        count = crawler.crawl_and_save(crawl_date)
        print(f"抓取完成！共 {count} 个项目")


if __name__ == '__main__':
    # 关闭 reloader 以避免子进程配置加载问题
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
