# 🔧 Исправление проблемы с Git

## Проблема
```
fatal: detected dubious ownership in repository at '/opt/taxi-zhukovo'
```

## ✅ Решение

Выполните на сервере:

```bash
cd /opt/taxi-zhukovo

# Добавить директорию в безопасные
git config --global --add safe.directory /opt/taxi-zhukovo

# Теперь можно обновить код
git pull origin main
```

---

## Полная последовательность команд

```bash
cd /opt/taxi-zhukovo

# Исправление Git
git config --global --add safe.directory /opt/taxi-zhukovo

# Обновление кода
git pull origin main

# Активация виртуального окружения
source venv/bin/activate

# Проверка профиля
python check_driver.py 7003530057

# Исправление профиля
python fix_driver_profile.py 7003530057

# Перезапуск бота
systemctl restart taxi-bot
```

---

**После этого всё должно работать!**




