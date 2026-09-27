import json
import os
import sqlite3
from database import get_db_connection

# 默认大模型配置
DEFAULT_LLM_CONFIG = {
    'provider': 'openai',  # openai, azure, claude, custom
    'api_key': '',
    'api_base': '',
    'model': 'gpt-3.5-turbo',
    'temperature': 0.3,
    'max_tokens': 2000
}

def init_llm_config_table():
    """初始化大模型配置表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS llm_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL DEFAULT 'openai',
            api_key TEXT,
            api_base TEXT,
            model TEXT NOT NULL DEFAULT 'gpt-3.5-turbo',
            temperature REAL DEFAULT 0.3,
            max_tokens INTEGER DEFAULT 2000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入默认配置
    cursor.execute('SELECT COUNT(*) as count FROM llm_config')
    if cursor.fetchone()['count'] == 0:
        cursor.execute('''
            INSERT INTO llm_config (provider, api_key, api_base, model, temperature, max_tokens)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('openai', '', '', 'gpt-3.5-turbo', 0.3, 2000))
    
    conn.commit()
    conn.close()

def get_llm_config():
    """获取大模型配置"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM llm_config ORDER BY id DESC LIMIT 1')
    config = cursor.fetchone()
    conn.close()
    
    if config:
        return {
            'id': config['id'],
            'provider': config['provider'],
            'api_key': config['api_key'],
            'api_base': config['api_base'],
            'model': config['model'],
            'temperature': config['temperature'],
            'max_tokens': config['max_tokens']
        }
    return DEFAULT_LLM_CONFIG.copy()

def save_llm_config(config):
    """保存大模型配置"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE llm_config 
        SET provider = ?, api_key = ?, api_base = ?, model = ?, 
            temperature = ?, max_tokens = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (config['provider'], config['api_key'], config['api_base'],
          config['model'], config['temperature'], config['max_tokens'],
          config.get('id', 1)))
    
    conn.commit()
    conn.close()
    return True

# 支持的模型提供商配置
LLM_PROVIDERS = {
    'openai': {
        'name': 'OpenAI',
        'models': ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o', 'gpt-5.4'],
        'default_base': 'https://api.openai.com/v1'
    },
    'azure': {
        'name': 'Azure OpenAI',
        'models': ['gpt-35-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-5.4'],
        'default_base': ''
    },
    'claude': {
        'name': 'Claude (Anthropic)',
        'models': ['claude-3-haiku-20240307', 'claude-3-sonnet-20240229', 'claude-3-opus-20240229'],
        'default_base': 'https://api.anthropic.com'
    },
    'custom': {
        'name': '自定义/OpenAI兼容',
        'models': [],
        'default_base': ''
    }
}
