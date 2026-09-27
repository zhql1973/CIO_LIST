# CIO信息管理系统

## 简介

CIO信息管理系统是一个基于Web的CIO信息管理平台，支持大模型智能字段识别、数据批量导入、去重更新等功能。

## 快速开始

### 方式一：一键启动（推荐）
```bash
双击运行 start.bat
```

### 方式二：命令行启动
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate.bat

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

### 访问系统
```
浏览器访问: http://127.0.0.1:5000

默认账号: admin
默认密码: admin
```

## 项目结构

```
CIO_LIST/
├── app.py                  # Flask主程序
├── database.py             # 数据库操作
├── llm_config.py          # 大模型配置
├── llm_service.py         # 大模型服务
├── progress_manager.py    # 进度管理器
├── requirements.txt       # 依赖包列表
├── setup.py               # 安装脚本
├── build_exe.py           # 打包脚本
├── start.bat              # 启动脚本
├── static/                # 静态文件
│   ├── index.html
│   └── app.js
├── cio_system.db          # SQLite数据库
└── 安装部署手册.md         # 详细文档
```

## 功能特性

- ✅ CIO信息增删改查
- ✅ Excel/CSV/TXT批量导入
- ✅ 大模型智能字段识别（支持gpt-3.5/4/5.4等）
- ✅ 数据去重更新（姓名+手机号）
- ✅ 批量选择/删除
- ✅ 多条件模糊查询
- ✅ 分页显示

## 技术栈

- **后端**: Flask + SQLite
- **前端**: HTML5 + CSS3 + JavaScript
- **AI**: OpenAI / Azure / Claude API

## 详细文档

参见 [安装部署手册.md](安装部署手册.md)

## 许可证

MIT License
