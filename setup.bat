@echo off
echo === v0-extended Setup ===
echo This script will set up the v0-extended environment.

:: Check Python version
echo.
echo Checking Python version...
python --version 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python not found. Please install Python 3.9 or higher.
    exit /b 1
)

:: Create virtual environment
echo.
echo Creating virtual environment...
if exist venv (
    echo Virtual environment already exists. Skipping creation.
) else (
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to create virtual environment.
        exit /b 1
    )
    echo Virtual environment created successfully.
)

:: Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to activate virtual environment.
    exit /b 1
)
echo Virtual environment activated.

:: Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Failed to upgrade pip. Continuing anyway.
)

:: Install package
echo.
echo Installing v0-extended...
pip install -e .
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install package.
    exit /b 1
)
echo v0-extended installed successfully.

:: Create .env file if it doesn't exist
echo.
echo Checking for .env file...
if not exist .env (
    echo Creating sample .env file...
    (
        echo OPENAI_API_KEY=your_openai_key_here
        echo GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\google-credentials.json
        echo TTS_ENGINE=google
        echo STT_ENGINE=whisper
        echo LOG_LEVEL=INFO
        echo LLM_MODEL=gpt-4
        echo WHISPER_MODEL=base
    ) > .env
    echo Sample .env file created. Please edit it with your API keys.
) else (
    echo .env file already exists. Skipping creation.
)

:: Check .env file
echo.
echo Checking .env file...
findstr "your_openai_key_here" .env >nul
if %ERRORLEVEL% EQU 0 (
    echo Warning: You need to update the OPENAI_API_KEY in .env file.
)
findstr "C:\path\to\google-credentials.json" .env >nul
if %ERRORLEVEL% EQU 0 (
    echo Warning: You need to update the GOOGLE_APPLICATION_CREDENTIALS in .env file.
)

echo.
echo Setup completed!
echo To activate the environment in the future, run: venv\Scripts\activate
echo To test your setup, run: python test_setup.py
echo To use v0-extended, run: rin ask "Hello!"

:: Keep the window open
pause 