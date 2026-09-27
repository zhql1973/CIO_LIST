import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'cio_system.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_code TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建CIO列表表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cio_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit_name TEXT,
            phone TEXT,
            email TEXT,
            unit_full_name TEXT,
            position TEXT,
            gender TEXT,
            home_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入默认管理员账号
    hashed_password = hashlib.md5('admin'.encode()).hexdigest()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_code, password, name)
        VALUES (?, ?, ?)
    ''', ('admin', hashed_password, '管理员'))
    
    conn.commit()
    conn.close()
    print("数据库初始化完成！")
    print("默认账号：admin，密码：admin")

if __name__ == '__main__':
    init_database()
