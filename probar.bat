@echo off
setlocal
cd /d "%~dp0"

if not exist "dist\Territory_Mapping.exe" (
    echo No existe dist\Territory_Mapping.exe
    echo Corre primero build.bat
    pause
    exit /b 1
)

if not exist "salida" mkdir "salida"

echo Generando el mapa del territorio de ejemplo...
"dist\Territory_Mapping.exe" -i "samples\territorio_ejemplo.json" -o "salida"
if errorlevel 1 (
    pause
    exit /b 1
)

echo.
echo Abriendo la imagen...
start "" "salida\territorio_ejemplo_area.png"
