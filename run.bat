@echo off
REM Check if Python is installed
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python and try again.
    pause
    exit /b
)

REM Install required Python packages if they aren't already installed
echo Installing required Python packages...
pip install flask requests pillow >nul 2>&1
if %errorlevel% neq 0 (
    echo Failed to install required packages. Please check your internet connection and try again.
    pause
    exit /b
)

REM Launch the Flask server in a new command prompt window
echo Starting Flask server...
start cmd /k "python app.py && exit"

REM Wait for the Flask server to start (adjust the timeout if needed)
timeout /t 5 >nul

REM Open the website in the default browser
echo Opening http://127.0.0.1:5000...
start http://127.0.0.1:5000

REM Exit the script
exit