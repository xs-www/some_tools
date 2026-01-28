@echo off
:: Run the app using the virtual environment Python (CMD)
cd /d %~dp0

:: If SOFFICE_PATH not set, try common installation paths for LibreOffice
if not defined SOFFICE_PATH (
	if exist "C:\Program Files\LibreOffice\program\soffice.exe" (
		set "SOFFICE_PATH=C:\Program Files\LibreOffice\program\soffice.exe"
	) else if exist "C:\Program Files (x86)\LibreOffice\program\soffice.exe" (
		set "SOFFICE_PATH=C:\Program Files (x86)\LibreOffice\program\soffice.exe"
	)
)

:: Default DOCX2PDF cleanup behavior (0 = disabled, 1 = kill WINWORD after conversion)
if not defined DOCX2PDF_CLEANUP_WINWORD set "DOCX2PDF_CLEANUP_WINWORD=0"

echo Using SOFFICE_PATH=%SOFFICE_PATH%
echo DOCX2PDF_CLEANUP_WINWORD=%DOCX2PDF_CLEANUP_WINWORD%

:: Activate venv for this CMD session if available
if exist "venv\Scripts\activate.bat" (
	call venv\Scripts\activate.bat
)

:: Start the application with the venv Python
venv\Scripts\python.exe app.py