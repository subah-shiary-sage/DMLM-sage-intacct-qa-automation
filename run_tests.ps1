# =============================================================================
#  run_tests.ps1  --  Run the test suite without needing pytest on PATH.
#
#  Usage (from a PowerShell prompt, right-click > "Run with PowerShell", or a
#  VS Code task):
#    .\run_tests.ps1                                        # full suite
#    .\run_tests.ps1 tests\loan_type                         # one folder
#    .\run_tests.ps1 tests\loan_type\test_create.py           # one file
#    .\run_tests.ps1 tests\loan_type\test_create.py::TestCreateLoanType::test_the_save_button_is_visible_on_the_create_form
#
#  Reports are written to reports\report.html and reports\results.xml
#  (see pytest.ini). Set HEADLESS=false in .env to watch the browser.
# =============================================================================

$PythonExe = "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host ""
    Write-Host "Could not find Python at: $PythonExe" -ForegroundColor Red
    Write-Host "Edit run_tests.ps1 and update `$PythonExe to your Python install path"
    Write-Host "(or run:  py -m pytest ...  if the 'py' launcher is on your PATH)."
    Write-Host ""
    exit 1
}

Set-Location -Path $PSScriptRoot
& $PythonExe -m pytest @args
$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "----------------------------------------------------------------------"
Write-Host "Done. HTML report: reports\report.html"
Write-Host "----------------------------------------------------------------------"

exit $exitCode
