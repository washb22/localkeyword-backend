@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo   키워드 순위 알림 - 텔레그램 설정
echo ==========================================
echo.
echo 잠시만 기다려주세요...
echo.

cd /d "%~dp0"
python setup_telegram.py

if %errorlevel% neq 0 (
    echo.
    echo [오류] Python이 설치되어 있지 않습니다.
    echo.
    echo 아래 방법으로 Python을 설치해주세요:
    echo 1. https://www.python.org/downloads/ 접속
    echo 2. "Download Python" 버튼 클릭
    echo 3. 설치할 때 "Add Python to PATH" 반드시 체크!
    echo 4. 설치 완료 후 이 파일을 다시 더블클릭
    echo.
)

pause
