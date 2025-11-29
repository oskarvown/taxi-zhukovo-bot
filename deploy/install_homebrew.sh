#!/bin/bash
# Установка Homebrew на Mac

echo "🍺 Установка Homebrew..."

# Установка Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Добавление Homebrew в PATH (для Apple Silicon Mac)
if [[ $(uname -m) == "arm64" ]]; then
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# Установка sshpass
echo "📦 Установка sshpass..."
brew install hudochenkov/sshpass/sshpass

echo "✅ Готово! Теперь можно использовать auto_deploy.sh"

