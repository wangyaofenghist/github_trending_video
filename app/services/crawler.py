"""
GitHub Trending 爬虫服务
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from app import db
from app.models import TrendingProject
import logging

logger = logging.getLogger(__name__)


class GitHubCrawler:
    """GitHub Trending 爬虫类"""

    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.get('REQUEST_HEADERS', {}))

    def fetch_trending_page(self):
        """抓取 GitHub Trending 页面"""
        try:
            response = self.session.get(
                self.config.get('GITHUB_TRENDING_URL', 'https://github.com/trending'),
                timeout=30
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"抓取 Trending 页面失败：{e}")
            raise

    def parse_trending_projects(self, html_content, crawl_date=None):
        """解析 Trending 项目列表"""
        soup = BeautifulSoup(html_content, 'lxml')
        projects = []

        # 查找所有项目文章
        articles = soup.select('article.Box-row')

        for rank, article in enumerate(articles, 1):
            try:
                # 提取项目链接和名称
                link_elem = article.select_one('h2 a')
                if not link_elem:
                    continue

                full_name = link_elem.get('href', '').strip('/')
                parts = full_name.split('/')
                if len(parts) != 2:
                    continue

                owner, name = parts

                # 提取描述
                desc_elem = article.select_one('p')
                description = desc_elem.get_text(strip=True) if desc_elem else None

                # 提取语言
                lang_elem = article.select_one('[itemprop="programmingLanguage"]')
                language = lang_elem.get_text(strip=True) if lang_elem else None

                # 提取 stars 和 forks
                star_elem = article.select_one('a[href$="/stargazers"]')
                fork_elem = article.select_one('a[href$="/forks"]')

                stars = self._parse_number(star_elem.get_text(strip=True)) if star_elem else 0
                forks = self._parse_number(fork_elem.get_text(strip=True)) if fork_elem else 0

                # 提取 topics
                topics = []
                for topic_elem in article.select('[alt]'):
                    if topic_elem.get('href', '').startswith('/topics/'):
                        topics.append(topic_elem.get_text(strip=True))

                project = TrendingProject(
                    crawl_date=crawl_date or datetime.now().date(),
                    rank=rank,
                    owner=owner,
                    name=name,
                    full_name=full_name,
                    description=description,
                    language=language,
                    stars=stars,
                    forks=forks,
                    topics=str(topics),
                    html_url=f"{self.config.get('GITHUB_BASE_URL', 'https://github.com')}/{full_name}"
                )
                projects.append(project)

            except Exception as e:
                logger.error(f"解析项目失败：{e}")
                continue

        return projects

    def _parse_number(self, text):
        """解析数字（支持 k, M 等单位）"""
        if not text:
            return 0
        text = text.strip().replace(',', '')
        try:
            if 'k' in text.lower():
                return int(float(text.lower().replace('k', '')) * 1000)
            elif 'm' in text.lower():
                return int(float(text.lower().replace('m', '')) * 1000000)
            return int(float(text))
        except ValueError:
            return 0

    def fetch_readme(self, owner, name):
        """获取项目 README 内容"""
        readme_url = f"https://raw.githubusercontent.com/{owner}/{name}/master/README.md"
        alt_url = f"https://raw.githubusercontent.com/{owner}/{name}/main/README.md"

        for url in [readme_url, alt_url]:
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    return response.text, url
            except requests.RequestException:
                continue

        return None, None

    def crawl_and_save(self, crawl_date=None):
        """执行完整抓取流程并保存"""
        crawl_date = crawl_date or datetime.now().date()

        # 检查是否已抓取
        existing = TrendingProject.query.filter_by(crawl_date=crawl_date).count()
        if existing > 0:
            logger.info(f"{crawl_date} 的数据已存在，共 {existing} 条")
            return existing

        # 抓取页面
        html = self.fetch_trending_page()

        # 解析项目
        projects = self.parse_trending_projects(html, crawl_date)

        # 获取 README 并保存
        for project in projects:
            readme_content, readme_url = self.fetch_readme(project.owner, project.name)
            if readme_content:
                project.readme_raw = readme_content
                project.readme_url = readme_url

            db.session.add(project)
            logger.info(f"抓取项目：{project.full_name}")

        db.session.commit()
        logger.info(f"抓取完成，共 {len(projects)} 个项目")

        return len(projects)
