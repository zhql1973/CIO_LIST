"""
CIO信息管理系统 - PyInstaller打包脚本
生成独立的Windows可执行文件
"""
import PyInstaller.__main__
import os
import shutil

# 清理旧的构建目录
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

# PyInstaller参数
params = [
    'app.py',  # 主程序入口
    '--name=CIO信息管理系统',
    '--onefile',  # 打包成单个文件
    '--windowed',  # Windows下不显示控制台
    '--add-data=static;static',  # 包含静态文件
    '--add-data=templates;templates',  # 包含模板文件
    '--icon=app.ico',  # 应用程序图标（如果有）
    '--clean',
    '--noconfirm',
    # 隐藏导入
    '--hidden-import=flask',
    '--hidden-import=flask_cors',
    '--hidden-import=pandas',
    '--hidden-import=openpyxl',
    '--hidden-import=xlrd',
    '--hidden-import=openai',
    '--hidden-import=requests',
    '--hidden-import=database',
    '--hidden-import=llm_config',
    '--hidden-import=llm_service',
    '--hidden-import=progress_manager',
]

print("开始打包CIO信息管理系统...")
PyInstaller.__main__.run(params)
print("打包完成！")
print("可执行文件位于: dist/CIO信息管理系统.exe")
