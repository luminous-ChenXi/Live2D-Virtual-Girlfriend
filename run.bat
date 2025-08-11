@echo off

:: 设置编码为UTF-8
chcp 65001 >nul

:: 删除旧的虚拟环境（如果存在）
if exist .venv (
    echo 删除旧的虚拟环境...
    rmdir /s /q .venv
)

:: 创建新的虚拟环境
 echo 创建新的虚拟环境...
python -m venv .venv --without-pip

:: 手动安装pip
set PIP_URL=https://bootstrap.pypa.io/get-pip.py
if not exist get-pip.py (
    echo 下载get-pip.py...
    powershell -Command "Invoke-WebRequest -Uri %PIP_URL% -OutFile get-pip.py"
)

:: 激活虚拟环境
call .venv\Scripts\activate.bat

:: 安装pip到虚拟环境
python get-pip.py

:: 显示当前环境信息
pip --version

:: 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

:: 列出已安装的包
echo 列出已安装的包...
pip list

:: 运行项目
echo 运行项目...
python main.py

pause
