import json
import requests
import uuid
from openai import OpenAI
from llm_config import get_llm_config, LLM_PROVIDERS
from progress_manager import create_progress_task, update_progress, complete_progress, error_progress

def call_llm_for_data_extraction(file_content, file_type, progress_callback=None):
    """
    调用大模型识别文件中的CIO信息
    支持分批处理大量数据
    
    Args:
        file_content: 文件内容（字符串格式）
        file_type: 文件类型（excel, csv, txt）
        progress_callback: 进度回调函数，接收(current, total, message)参数
    
    Returns:
        list: 识别出的CIO信息列表
    """
    config = get_llm_config()
    
    if not config['api_key']:
        raise Exception('请先配置大模型API密钥')
    
    # 估算每批处理的数据量（根据内容长度）
    # 假设每条记录平均200字符，每批最多处理100条
    total_length = len(file_content)
    
    # 如果内容较短，直接处理
    if total_length <= 15000:
        if progress_callback:
            progress_callback(1, 1, '正在处理数据...')
        result = _process_single_batch(config, file_content, file_type)
        if progress_callback:
            progress_callback(1, 1, f'处理完成，识别出 {len(result)} 条记录')
        return result
    
    # 分批处理大量数据
    print(f"文件内容较大({total_length}字符)，将分批处理...")
    
    # 按行分割内容
    lines = file_content.split('\n')
    header = lines[0] if lines else ""
    data_lines = lines[1:] if len(lines) > 1 else []
    
    # 估算每批的行数（每批最多100条数据）
    batch_size = 100
    total_batches = (len(data_lines) + batch_size - 1) // batch_size
    all_results = []
    
    for i in range(0, len(data_lines), batch_size):
        batch_num = i // batch_size + 1
        batch_lines = data_lines[i:i+batch_size]
        batch_content = header + '\n' + '\n'.join(batch_lines)
        
        message = f'正在处理第 {batch_num}/{total_batches} 批数据...'
        print(message)
        if progress_callback:
            progress_callback(batch_num, total_batches, message)
        
        try:
            batch_result = _process_single_batch(config, batch_content, file_type)
            all_results.extend(batch_result)
            print(f"  本批识别出 {len(batch_result)} 条记录")
            if progress_callback:
                progress_callback(batch_num, total_batches, f'第 {batch_num} 批完成，已识别 {len(all_results)} 条记录')
        except Exception as e:
            error_msg = f'第 {batch_num} 批处理失败: {str(e)}'
            print(f"  {error_msg}")
            if progress_callback:
                progress_callback(batch_num, total_batches, error_msg)
            # 继续处理下一批
    
    final_message = f'处理完成，总共识别出 {len(all_results)} 条记录'
    print(final_message)
    if progress_callback:
        progress_callback(total_batches, total_batches, final_message)
    
    return all_results

def _process_single_batch(config, file_content, file_type):
    """处理单批数据"""
    # 构建提示词 - 增加内容长度到15000字符
    prompt = f"""请从以下{file_type}格式的文件中提取CIO信息，并以JSON格式返回。

文件内容：
{file_content[:15000]}

请识别以下字段（如果字段不存在则返回空字符串）：
- name: 姓名
- unit_name: 单位名称
- phone: 手机号
- email: 邮箱
- unit_full_name: 单位全称
- position: 职位
- gender: 性别
- home_address: 家庭地址

必须严格按以下JSON格式返回，不要添加任何其他文字说明：
{{"data":[{{"name":"","unit_name":"","phone":"","email":"","unit_full_name":"","position":"","gender":"","home_address":""}}]}}

重要提示：
1. 只返回JSON数据，不要包含markdown代码块标记（如```json）
2. 确保返回的是有效的JSON格式
3. 如果某个字段不存在，使用空字符串""
4. 每条记录必须是完整的JSON对象
5. 请确保识别出所有记录，不要遗漏
"""

    provider = config['provider']
    
    try:
        if provider == 'openai' or provider == 'custom':
            return _call_openai(config, prompt)
        elif provider == 'azure':
            return _call_azure(config, prompt)
        elif provider == 'claude':
            return _call_claude(config, prompt)
        else:
            raise Exception(f'不支持的提供商: {provider}')
    except Exception as e:
        raise Exception(f'大模型调用失败: {str(e)}')

def _call_openai(config, prompt):
    """调用OpenAI API"""
    api_base = config['api_base'] or 'https://api.openai.com/v1'
    model = config['model']
    
    client = OpenAI(
        api_key=config['api_key'],
        base_url=api_base
    )
    
    # gpt-5.4 使用 max_completion_tokens 而不是 max_tokens
    if model == 'gpt-5.4':
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个数据提取助手，擅长从各种格式的文件中提取结构化信息。请只返回JSON格式的结果。"},
                {"role": "user", "content": prompt}
            ],
            temperature=config['temperature'],
            max_completion_tokens=config['max_tokens']
        )
    else:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个数据提取助手，擅长从各种格式的文件中提取结构化信息。请只返回JSON格式的结果。"},
                {"role": "user", "content": prompt}
            ],
            temperature=config['temperature'],
            max_tokens=config['max_tokens']
        )
    
    content = response.choices[0].message.content
    return _parse_llm_response(content)

def _call_azure(config, prompt):
    """调用Azure OpenAI API"""
    if not config['api_base']:
        raise Exception('Azure OpenAI需要配置API Base URL')
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': config['api_key']
    }
    
    data = {
        'messages': [
            {"role": "system", "content": "你是一个数据提取助手，擅长从各种格式的文件中提取结构化信息。请只返回JSON格式的结果。"},
            {"role": "user", "content": prompt}
        ],
        'temperature': config['temperature'],
        'max_tokens': config['max_tokens']
    }
    
    response = requests.post(
        f"{config['api_base']}/openai/deployments/{config['model']}/chat/completions?api-version=2024-02-01",
        headers=headers,
        json=data
    )
    
    if response.status_code != 200:
        raise Exception(f'Azure API错误: {response.text}')
    
    result = response.json()
    content = result['choices'][0]['message']['content']
    return _parse_llm_response(content)

def _call_claude(config, prompt):
    """调用Claude API"""
    api_base = config['api_base'] or 'https://api.anthropic.com'
    
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': config['api_key'],
        'anthropic-version': '2023-06-01'
    }
    
    data = {
        'model': config['model'],
        'max_tokens': config['max_tokens'],
        'temperature': config['temperature'],
        'system': '你是一个数据提取助手，擅长从各种格式的文件中提取结构化信息。请只返回JSON格式的结果。',
        'messages': [
            {"role": "user", "content": prompt}
        ]
    }
    
    response = requests.post(
        f'{api_base}/v1/messages',
        headers=headers,
        json=data
    )
    
    if response.status_code != 200:
        raise Exception(f'Claude API错误: {response.text}')
    
    result = response.json()
    content = result['content'][0]['text']
    return _parse_llm_response(content)

def _parse_llm_response(content):
    """解析大模型返回的内容"""
    # 检查内容是否为空
    if not content or not content.strip():
        raise Exception('大模型返回内容为空')
    
    # 尝试提取JSON部分
    content = content.strip()
    
    # 如果包含markdown代码块，提取其中的内容
    if '```json' in content:
        start = content.find('```json') + 7
        end = content.find('```', start)
        if end == -1:
            end = len(content)
        content = content[start:end].strip()
    elif '```' in content:
        start = content.find('```') + 3
        end = content.find('```', start)
        if end == -1:
            end = len(content)
        content = content[start:end].strip()
    
    # 尝试找到JSON数组或对象的开始位置
    json_start = -1
    for i, char in enumerate(content):
        if char == '[' or char == '{':
            json_start = i
            break
    
    if json_start == -1:
        raise Exception(f'无法找到JSON内容，原始响应: {content[:200]}')
    
    content = content[json_start:]
    
    # 尝试找到JSON结束位置
    json_end = len(content)
    bracket_count = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(content):
        if escape_next:
            escape_next = False
            continue
        if char == '\\':
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if not in_string:
            if char in '[{':
                bracket_count += 1
            elif char in ']}':
                bracket_count -= 1
                if bracket_count == 0:
                    json_end = i + 1
                    break
    
    content = content[:json_end]
    
    try:
        result = json.loads(content)
        if 'data' in result and isinstance(result['data'], list):
            return result['data']
        elif isinstance(result, list):
            return result
        else:
            return []
    except json.JSONDecodeError as e:
        raise Exception(f'JSON解析失败: {str(e)}，原始内容: {content[:200]}')

def test_llm_connection():
    """测试大模型连接"""
    config = get_llm_config()
    
    if not config['api_key']:
        return {'success': False, 'message': 'API密钥未配置'}
    
    try:
        prompt = "请回复'连接成功'，只返回这两个字。"
        
        if config['provider'] == 'openai' or config['provider'] == 'custom':
            api_base = config['api_base'] or 'https://api.openai.com/v1'
            model = config['model']
            client = OpenAI(api_key=config['api_key'], base_url=api_base)
            
            # gpt-5.4 使用 max_completion_tokens
            if model == 'gpt-5.4':
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=10
                )
            else:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=10
                )
            return {'success': True, 'message': '连接成功'}
        elif config['provider'] == 'azure':
            return {'success': True, 'message': 'Azure配置已保存'}
        elif config['provider'] == 'claude':
            return {'success': True, 'message': 'Claude配置已保存'}
        
    except Exception as e:
        return {'success': False, 'message': f'连接失败: {str(e)}'}
