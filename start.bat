@echo off
chcp 65001 >nul
echo ========================================
echo    CIO信息管理系统
echo ========================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python环境，请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist ".venv\Scripts\activate.bat" (
    echo [信息] 正在创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
call .venv\Scripts\activate.bat

REM 安装依赖
echo [信息] 正在检查依赖...
pip install -r requirements.txt -q

REM 启动服务
echo.
echo [信息] 正在启动CIO信息管理系统...
echo [信息] 服务启动后，请使用浏览器访问: http://127.0.0.1:5000
echo.
echo 按Ctrl+C可以停止服务
echo ========================================
echo.

python app.py

pause
