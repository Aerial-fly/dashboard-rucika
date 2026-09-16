@echo off
title Menjalankan QA Monitoring Dashboard Rucika
echo ===================================================
echo   Menyalakan QA Monitoring Dashboard Pabrik Rucika
echo ===================================================
echo.
echo Memeriksa dan menjalankan container Docker...
docker compose up -d

if %errorlevel% neq 0 (
    echo.
    echo [PERINGATAN] Gagal menjalankan Docker!
    echo Pastikan aplikasi Docker Desktop sudah dibuka dan statusnya Running.
    echo.
    pause
    exit /b
)

echo.
echo [SUKSES] Seluruh sistem berhasil dijalankan!
echo Membuka Dashboard di browser otomatis...
timeout /t 2 >nul
start http://localhost:5000

echo.
echo ===================================================
echo  Aplikasi siap digunakan:
echo  - Dashboard QA : http://localhost:5000
echo  - phpMyAdmin   : http://localhost:8080
echo ===================================================
echo.
echo (Jendela ini boleh Anda tutup)
timeout /t 5 >nul
