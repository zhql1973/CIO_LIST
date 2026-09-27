from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import sqlite3
import hashlib
import os
import pandas as pd
import json
import uuid
import threading
import tempfile
from datetime import datetime
from database import get_db_connection, init_database
from llm_config import init_llm_config_table, get_llm_config, save_llm_config, LLM_PROVIDERS
from llm_service import call_llm_for_data_extraction, test_llm_connection
from progress_manager import create_progress_task, update_progress, get_progress, complete_progress, error_progress

app = Flask(__name__, static_folder='static')
CORS(app)

# 初始化数据库
init_database()
init_llm_config_table()

def md5_hash(password):
    return hashlib.md5(password.encode()).hexdigest()

# ==================== 登录接口 ====================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user_code = data.get('user_code')
    password = data.get('password')
    
    if not user_code or not password:
        return jsonify({'success': False, 'message': '账号和密码不能为空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_code = ? AND password = ?', 
                   (user_code, md5_hash(password)))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'success': True, 
            'message': '登录成功',
            'user': {
                'id': user['id'],
                'user_code': user['user_code'],
                'name': user['name']
            }
        })
    else:
        return jsonify({'success': False, 'message': '账号或密码错误'}), 401

# ==================== 用户管理接口 ====================
@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, user_code, name, created_at FROM users ORDER BY id DESC')
    users = cursor.fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'data': [dict(user) for user in users]
    })

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    user_code = data.get('user_code')
    password = data.get('password')
    name = data.get('name')
    
    if not user_code or not password or not name:
        return jsonify({'success': False, 'message': '所有字段都不能为空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (user_code, password, name) VALUES (?, ?, ?)',
                       (user_code, md5_hash(password), name))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '用户创建成功'})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'message': '用户编码已存在'}), 400

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.json
    user_code = data.get('user_code')
    name = data.get('name')
    password = data.get('password')
    
    if not user_code or not name:
        return jsonify({'success': False, 'message': '用户编码和姓名不能为空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if password:
        cursor.execute('UPDATE users SET user_code = ?, name = ?, password = ? WHERE id = ?',
                       (user_code, name, md5_hash(password), user_id))
    else:
        cursor.execute('UPDATE users SET user_code = ?, name = ? WHERE id = ?',
                       (user_code, name, user_id))
    
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '用户更新成功'})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': '用户删除成功'})

# ==================== CIO管理接口 ====================
@app.route('/api/cio', methods=['GET'])
def get_cio_list():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    name = request.args.get('name', '')
    unit_name = request.args.get('unit_name', '')
    phone = request.args.get('phone', '')
    unit_full_name = request.args.get('unit_full_name', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 构建查询条件
    conditions = []
    params = []
    if name:
        conditions.append('name LIKE ?')
        params.append(f'%{name}%')
    if unit_name:
        conditions.append('unit_name LIKE ?')
        params.append(f'%{unit_name}%')
    if phone:
        conditions.append('phone LIKE ?')
        params.append(f'%{phone}%')
    if unit_full_name:
        conditions.append('unit_full_name LIKE ?')
        params.append(f'%{unit_full_name}%')
    
    where_clause = ' AND '.join(conditions) if conditions else '1=1'
    
    # 获取总数
    cursor.execute(f'SELECT COUNT(*) as total FROM cio_list WHERE {where_clause}', params)
    total = cursor.fetchone()['total']
    
    # 获取分页数据
    offset = (page - 1) * per_page
    cursor.execute(f'''
        SELECT * FROM cio_list 
        WHERE {where_clause}
        ORDER BY id DESC 
        LIMIT ? OFFSET ?
    ''', params + [per_page, offset])
    
    cio_list = cursor.fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'data': [dict(cio) for cio in cio_list],
        'total': total,
        'page': page,
        'per_page': per_page
    })

# ==================== CIO数据导出接口 ====================
@app.route('/api/cio/export', methods=['GET'])
def export_cio_list():
    """导出CIO数据到Excel文件"""
    try:
        name = request.args.get('name', '')
        unit_name = request.args.get('unit_name', '')
        phone = request.args.get('phone', '')
        unit_full_name = request.args.get('unit_full_name', '')
        export_format = request.args.get('format', 'xlsx')  # xlsx 或 xls
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件（与查询接口相同，但不分页）
        conditions = []
        params = []
        if name:
            conditions.append('name LIKE ?')
            params.append(f'%{name}%')
        if unit_name:
            conditions.append('unit_name LIKE ?')
            params.append(f'%{unit_name}%')
        if phone:
            conditions.append('phone LIKE ?')
            params.append(f'%{phone}%')
        if unit_full_name:
            conditions.append('unit_full_name LIKE ?')
            params.append(f'%{unit_full_name}%')
        
        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        
        # 获取所有符合条件的数据（不分页）
        cursor.execute(f'''
            SELECT * FROM cio_list 
            WHERE {where_clause}
            ORDER BY id DESC
        ''', params)
        
        cio_list = cursor.fetchall()
        conn.close()
        
        if not cio_list:
            return jsonify({'success': False, 'message': '没有数据可导出'}), 400
        
        # 转换为DataFrame
        data = []
        for cio in cio_list:
            data.append({
                'ID': cio['id'],
                '姓名': cio['name'] or '',
                '单位名称': cio['unit_name'] or '',
                '手机号': cio['phone'] or '',
                '邮箱': cio['email'] or '',
                '单位全称': cio['unit_full_name'] or '',
                '职位': cio['position'] or '',
                '性别': cio['gender'] or '',
                '家庭地址': cio['home_address'] or '',
                '创建时间': cio['created_at'] or ''
            })
        
        df = pd.DataFrame(data)
        
        # 创建临时文件
        temp_dir = tempfile.gettempdir()
        
        if export_format == 'xls':
            filename = f'CIO名单_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xls'
            filepath = os.path.join(temp_dir, filename)
            # 使用xlwt引擎创建.xls文件
            df.to_excel(filepath, index=False, engine='xlwt')
            mimetype = 'application/vnd.ms-excel'
        else:
            filename = f'CIO名单_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            filepath = os.path.join(temp_dir, filename)
            # 使用openpyxl引擎创建.xlsx文件
            df.to_excel(filepath, index=False, engine='openpyxl')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        return send_file(
            filepath,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500

@app.route('/api/cio', methods=['POST'])
def create_cio():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cio_list (name, unit_name, phone, email, unit_full_name, position, gender, home_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data.get('name'), data.get('unit_name'), data.get('phone'), 
          data.get('email'), data.get('unit_full_name'), data.get('position'),
          data.get('gender'), data.get('home_address')))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return jsonify({'success': True, 'message': 'CIO信息创建成功', 'id': new_id})

@app.route('/api/cio/batch', methods=['POST'])
def batch_create_cio():
    data = request.json
    cio_list = data.get('data', [])
    upsert = data.get('upsert', False)  # 是否使用更新或插入模式
    
    if not cio_list:
        return jsonify({'success': False, 'message': '数据不能为空'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    
    for cio in cio_list:
        name = cio.get('name', '').strip()
        phone = cio.get('phone', '').strip()
        
        if upsert and name and phone:
            # 检查是否存在相同姓名和手机的记录
            cursor.execute('SELECT id FROM cio_list WHERE name = ? AND phone = ?', (name, phone))
            existing = cursor.fetchone()
            
            if existing:
                # 更新现有记录
                cursor.execute('''
                    UPDATE cio_list 
                    SET unit_name = ?, email = ?, unit_full_name = ?, 
                        position = ?, gender = ?, home_address = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (cio.get('unit_name'), cio.get('email'), cio.get('unit_full_name'),
                      cio.get('position'), cio.get('gender'), cio.get('home_address'), existing['id']))
                updated += 1
            else:
                # 插入新记录
                cursor.execute('''
                    INSERT INTO cio_list (name, unit_name, phone, email, unit_full_name, position, gender, home_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, cio.get('unit_name'), phone,
                      cio.get('email'), cio.get('unit_full_name'), cio.get('position'),
                      cio.get('gender'), cio.get('home_address')))
                inserted += 1
        else:
            # 直接插入
            cursor.execute('''
                INSERT INTO cio_list (name, unit_name, phone, email, unit_full_name, position, gender, home_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (cio.get('name'), cio.get('unit_name'), cio.get('phone'),
                  cio.get('email'), cio.get('unit_full_name'), cio.get('position'),
                  cio.get('gender'), cio.get('home_address')))
            inserted += 1
    
    conn.commit()
    conn.close()
    
    if upsert:
        return jsonify({
            'success': True, 
            'message': f'导入完成：新增 {inserted} 条，更新 {updated} 条',
            'inserted': inserted,
            'updated': updated
        })
    else:
        return jsonify({'success': True, 'message': f'成功导入{inserted}条数据'})

@app.route('/api/cio/<int:cio_id>', methods=['PUT'])
def update_cio(cio_id):
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE cio_list 
        SET name = ?, unit_name = ?, phone = ?, email = ?, 
            unit_full_name = ?, position = ?, gender = ?, home_address = ?
        WHERE id = ?
    ''', (data.get('name'), data.get('unit_name'), data.get('phone'),
          data.get('email'), data.get('unit_full_name'), data.get('position'),
          data.get('gender'), data.get('home_address'), cio_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'CIO信息更新成功'})

@app.route('/api/cio/<int:cio_id>', methods=['DELETE'])
def delete_cio(cio_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cio_list WHERE id = ?', (cio_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'CIO信息删除成功'})

# ==================== 大模型配置接口 ====================
@app.route('/api/llm/config', methods=['GET'])
def get_llm_config_api():
    config = get_llm_config()
    # 不返回API密钥
    config['api_key'] = '******' if config.get('api_key') else ''
    return jsonify({
        'success': True,
        'data': config,
        'providers': LLM_PROVIDERS
    })

@app.route('/api/llm/config', methods=['POST'])
def save_llm_config_api():
    data = request.json
    current_config = get_llm_config()
    
    # 如果API密钥是掩码，保留原值
    if data.get('api_key') == '******':
        data['api_key'] = current_config.get('api_key', '')
    
    save_llm_config(data)
    return jsonify({'success': True, 'message': '配置保存成功'})

@app.route('/api/llm/test', methods=['POST'])
def test_llm_connection_api():
    result = test_llm_connection()
    return jsonify(result)

# ==================== 文件导入接口（支持大模型识别） ====================
@app.route('/api/import', methods=['POST'])
def import_file():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '请选择文件'}), 400
    
    file = request.files['file']
    use_llm = request.form.get('use_llm', 'false').lower() == 'true'
    
    if file.filename == '':
        return jsonify({'success': False, 'message': '请选择文件'}), 400
    
    try:
        filename = file.filename.lower()
        file_content = ''
        file_type = ''
        
        # 读取文件内容
        if filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(file)
            file_content = df.to_csv(index=False, sep='\t')
            file_type = 'Excel'
        elif filename.endswith('.csv'):
            file_content = file.read().decode('utf-8')
            file.seek(0)
            df = pd.read_csv(file, encoding='utf-8')
            file_type = 'CSV'
        elif filename.endswith('.txt'):
            file_content = file.read().decode('utf-8')
            file.seek(0)
            try:
                df = pd.read_csv(file, encoding='utf-8', sep='\t')
            except:
                file.seek(0)
                df = pd.read_csv(file, encoding='utf-8', sep=',')
            file_type = 'TXT'
        else:
            return jsonify({'success': False, 'message': '不支持的文件格式'}), 400
        
        # 如果使用大模型识别
        if use_llm:
            try:
                data = call_llm_for_data_extraction(file_content, file_type)
                return jsonify({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'method': 'llm'
                })
            except Exception as e:
                return jsonify({'success': False, 'message': f'大模型识别失败: {str(e)}'}), 400
        else:
            # 使用传统方式解析
            column_mapping = {
                '姓名': 'name',
                '单位名称': 'unit_name',
                '手机号': 'phone',
                '邮箱': 'email',
                '单位全称': 'unit_full_name',
                '职位': 'position',
                '性别': 'gender',
                '家庭地址': 'home_address'
            }
            
            df = df.rename(columns=column_mapping)
            for col in column_mapping.values():
                if col not in df.columns:
                    df[col] = ''
            
            data = df[list(column_mapping.values())].fillna('').to_dict('records')
            
            return jsonify({
                'success': True,
                'data': data,
                'count': len(data),
                'method': 'traditional'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'文件解析失败: {str(e)}'}), 400

# ==================== 静态文件服务 ====================
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

def main():
    """程序入口点"""
    print("=" * 50)
    print("   CIO信息管理系统")
    print("=" * 50)
    print()
    print("服务启动中...")
    print("访问地址: http://127.0.0.1:5000")
    print("默认账号: admin")
    print("默认密码: admin")
    print()
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    print()
    
    # 生产环境关闭debug模式
    import sys
    debug_mode = '--debug' in sys.argv
    
    app.run(
        debug=debug_mode, 
        host='0.0.0.0', 
        port=5000,
        use_reloader=debug_mode  # 非调试模式禁用重载器
    )

if __name__ == '__main__':
    main()
