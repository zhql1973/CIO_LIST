"""CIO信息管理系统 - 安装打包脚本"""
from setuptools import setup, find_packages
import os

# 读取requirements
requirements = []
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='cio-management-system',
    version='1.0.0',
    description='CIO信息管理系统 - 支持大模型智能识别',
    author='Your Organization',
    author_email='admin@example.com',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        '': ['static/*', 'static/**/*', '*.db', '*.txt'],
    },
    install_requires=requirements,
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'cio-system=app:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Enterprise',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
