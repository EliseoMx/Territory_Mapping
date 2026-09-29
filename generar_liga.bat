@echo off
setlocal
cd /d "%~dp0"

rem Arrastra un JSON de coordenadas sobre este archivo: te da una liga web
rem con el mapa (geojson.io) y la abre. Sin cuenta, sin Google, gratis.

if "%~1"=="" (
    echo Arrastra un archivo .json de coordenadas sobre generar_liga.bat
    echo   o corre:  generar_liga.bat mi_territorio.json
    pause
    exit /b 1
)
if not exist "dist\Territory_Mapping.exe" (
    echo No existe dist\Territory_Mapping.exe
    echo Corre primero build.bat
    pause
    exit /b 1
)
if not exist "salida" mkdir "salida"

"dist\Territory_Mapping.exe" -i "%~1" -o "salida" --kml --sin-imagen --abrir
echo.
echo Las ligas quedaron en salida\%~n1_liga.txt
pause
