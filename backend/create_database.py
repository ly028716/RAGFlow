"""
创建数据库

如果数据库不存在，则创建ai_assistant数据库。
"""

import sys
import os
import pymysql
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings


def create_database():
    """创建数据库（如果不存在）"""
    print("=" * 60)
    print("创建数据库")
    print("=" * 60)

    # 从环境变量读取连接信息
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    username = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_ROOT_PASSWORD", "root")
    database = os.getenv("MYSQL_DATABASE", "ai_assistant")
    
    print(f"\n连接信息:")
    print(f"  - 主机: {host}")
    print(f"  - 端口: {port}")
    print(f"  - 用户: {username}")
    print(f"  - 数据库: {database}")
    
    try:
        
        # 连接到MySQL服务器（不指定数据库）
        print(f"\n正在连接到MySQL服务器...")
        connection = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            charset='utf8mb4'
        )
        
        print("✓ 成功连接到MySQL服务器")
        
        # 创建游标
        cursor = connection.cursor()
        
        # 检查数据库是否存在
        cursor.execute(f"SHOW DATABASES LIKE '{database}'")
        result = cursor.fetchone()
        
        if result:
            print(f"\n✓ 数据库 '{database}' 已存在")
        else:
            # 创建数据库
            print(f"\n正在创建数据库 '{database}'...")
            cursor.execute(
                f"CREATE DATABASE {database} "
                f"CHARACTER SET utf8mb4 "
                f"COLLATE utf8mb4_unicode_ci"
            )
            print(f"✓ 成功创建数据库 '{database}'")
        
        # 关闭连接
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("数据库创建完成")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        if create_database():
            print("\n✓ 操作成功")
            sys.exit(0)
        else:
            print("\n✗ 操作失败")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ 未预期的错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
