@echo off
chcp 65001 >nul
cls

echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║         МИГРАЦИЯ БАЗЫ ДАННЫХ - СИСТЕМА ОЧЕРЕДЕЙ                 ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.
echo Эта миграция добавит:
echo   • Новые поля для водителей (status, current_zone, online_since и др.)
echo   • Новые поля для заказов (zone, assigned_driver_id)
echo   • Поддержку всех 6 зон обслуживания
echo.
echo ВАЖНО: Создайте резервную копию базы данных перед миграцией!
echo.
pause

python database\migrations\add_queue_system.py

pause

