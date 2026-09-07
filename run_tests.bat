@echo off
REM ============================================================================
REM  run_tests.bat  --  Run the test suite without needing pytest on PATH.
REM
REM  Usage:
REM    Double-click this file                     -> runs the full suite
REM    run_tests.bat tests\loan_type               -> runs just that folder
REM    run_tests.bat tests\loan_type\test_create.py -> runs just that file
REM    run_tests.bat tests\loan_type\test_create.py::TestCreateLoanType::test_the_save_button_is_visible_on_the_create_form
REM                                                  -> runs a single test
REM
REM  Reports are written to reports\report.html and reports\results.xml
REM  (see pytest.ini). Set HEADLESS=false in .env to watch the browser.
REM ============================================================================
setlocal

set PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe

if not exist "%PYTHON_EXE%" (
    echo.
    echo Could not find Python at:
    echo   %PYTHON_EXE%
    echo.
    echo Edit run_tests.bat and change PYTHON_EXE to your Python install path
    echo ^(or run:  py -m pytest %%*  if the 'py' launcher is on your PATH^).
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0"
"%PYTHON_EXE%" -m pytest %*
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ----------------------------------------------------------------------
echo Done. HTML report: reports\report.html
echo ----------------------------------------------------------------------
pause

endlocal
exit /b %EXIT_CODE%
