"""进度管理器 - 用于跟踪大模型处理进度"""
import time
import threading

# 全局进度存储
_progress_store = {}
_progress_lock = threading.Lock()


def create_progress_task(task_id):
    """创建一个新的进度任务"""
    with _progress_lock:
        _progress_store[task_id] = {
            'status': 'processing',  # processing, completed, error
            'current_batch': 0,
            'total_batches': 0,
            'current_records': 0,
            'total_records': 0,
            'message': '准备处理...',
            'created_at': time.time()
        }
    return task_id


def update_progress(task_id, **kwargs):
    """更新进度信息"""
    with _progress_lock:
        if task_id in _progress_store:
            _progress_store[task_id].update(kwargs)


def get_progress(task_id):
    """获取进度信息"""
    with _progress_lock:
        progress = _progress_store.get(task_id, {})
        # 清理超过30分钟的旧任务
        current_time = time.time()
        old_tasks = [tid for tid, p in _progress_store.items() 
                     if current_time - p.get('created_at', 0) > 1800]
        for tid in old_tasks:
            del _progress_store[tid]
        return progress.copy() if progress else None


def complete_progress(task_id, message='处理完成'):
    """标记任务完成"""
    update_progress(task_id, status='completed', message=message)


def error_progress(task_id, message='处理失败'):
    """标记任务失败"""
    update_progress(task_id, status='error', message=message)
