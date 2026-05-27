@echo off
REM Production deployment script for Windows
REM 智能原生教育科研助手

echo === 智能原生教育科研助手 - 启动脚本 ===

cd /d "%~dp0..\backend"

REM Install dependencies
echo 安装依赖...
pip install -r requirements.txt

REM Start with gunicorn simulation (uvicorn for Windows)
echo 启动服务 (端口8013)...
echo   - 健康检查: http://localhost:8013/health
echo   - API文档:  http://localhost:8013/docs

uvicorn main:app --host 0.0.0.0 --port 8013 --reload

pause
