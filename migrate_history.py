"""
数据库迁移脚本 - 支持历史记录功能

1. 创建 crawl_batches 表
2. 迁移 trending_projects 数据（移除 unique 约束）
3. 添加 batch_id 外键关联
"""
import sqlite3
from datetime import datetime

DB_PATH = 'instance/github_trending.db'


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("开始数据库迁移...")

    # 1. 创建 crawl_batches 表
    print("1. 创建 crawl_batches 表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crawl_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_date DATE NOT NULL UNIQUE,
            projects_count INTEGER DEFAULT 0,
            status VARCHAR(50) DEFAULT 'completed',
            started_at DATETIME,
            completed_at DATETIME,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. 为 trending_projects 添加 batch_id 列（如果不存在）
    print("2. 添加 batch_id 列...")
    try:
        cursor.execute('ALTER TABLE trending_projects ADD COLUMN batch_id INTEGER')
    except sqlite3.OperationalError as e:
        if 'duplicate column' in str(e).lower():
            print("   batch_id 列已存在，跳过")
        else:
            raise

    # 3. 创建新表结构（移除 unique 约束）
    print("3. 重建 trending_projects 表（移除 unique 约束）...")

    # 获取现有数据
    cursor.execute('SELECT * FROM trending_projects')
    existing_data = cursor.fetchall()

    # 获取列名
    cursor.execute('PRAGMA table_info(trending_projects)')
    columns_info = cursor.fetchall()

    # 备份原表
    print("   备份原表...")
    cursor.execute('ALTER TABLE trending_projects RENAME TO trending_projects_old')

    # 创建新表（移除 unique 约束）
    print("   创建新表...")
    cursor.execute('''
        CREATE TABLE trending_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crawl_date DATE NOT NULL,
            rank INTEGER NOT NULL,
            owner VARCHAR(100) NOT NULL,
            name VARCHAR(200) NOT NULL,
            full_name VARCHAR(300) NOT NULL,
            description TEXT,
            language VARCHAR(50),
            stars INTEGER DEFAULT 0,
            forks INTEGER DEFAULT 0,
            topics TEXT,
            readme_raw TEXT,
            readme_url VARCHAR(500),
            html_url VARCHAR(300),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            batch_id INTEGER
        )
    ''')

    # 创建索引
    print("   创建索引...")
    cursor.execute('CREATE INDEX idx_crawl_date ON trending_projects (crawl_date)')
    cursor.execute('CREATE INDEX idx_full_name ON trending_projects (full_name)')

    # 恢复数据
    print("   恢复数据...")
    if existing_data:
        # 跳过 id 列，重新插入（让新表重新生成 id）
        cursor.executemany('''
            INSERT INTO trending_projects (
                crawl_date, rank, owner, name, full_name, description, language,
                stars, forks, topics, readme_raw, readme_url, html_url, created_at, batch_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [row[1:] for row in existing_data])

    # 删除旧表
    print("   删除旧表...")
    cursor.execute('DROP TABLE trending_projects_old')

    # 4. 为今天的日期创建一个 crawl_batch 记录（如果不存在）
    print("4. 创建默认 crawl_batch 记录...")
    today = datetime.now().date().isoformat()
    cursor.execute('''
        INSERT OR IGNORE INTO crawl_batches (crawl_date, status, projects_count, started_at, completed_at)
        VALUES (?, 'completed', 0, ?, ?)
    ''', (today, datetime.now(), datetime.now()))

    conn.commit()
    conn.close()

    print("\n迁移完成!")
    print(f"数据库路径：{DB_PATH}")


if __name__ == '__main__':
    migrate()
