#!/usr/bin/env bash
# Запуск SPORTLY на эмуляторе. ./run_emulator.sh — запустить; ./run_emulator.sh --build — сначала пересобрать APK.
set -e
cd "$(dirname "$0")"
SDK="$HOME/Android/Sdk"
ADB="$SDK/platform-tools/adb"
AVD="${AVD:-Pixel_10_Pro_XL}"
APK="bin/sportly-1.0-x86_64_arm64-v8a-debug.apk"

if [ "$1" = "--build" ] || [ ! -f "$APK" ]; then
    export VIRTUAL_ENV="$PWD/.venv" PATH="$PWD/.venv/bin:$PATH"
    buildozer android debug
fi

if ! "$ADB" devices | grep -q "^emulator"; then
    echo "Запускаю эмулятор $AVD..."
    nohup "$SDK/emulator/emulator" -avd "$AVD" -no-boot-anim >/dev/null 2>&1 &
fi
echo "Жду загрузку эмулятора..."
"$ADB" wait-for-device
until [ "$("$ADB" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = "1" ]; do sleep 2; done

echo "Устанавливаю приложение..."
"$ADB" install -r "$APK"
"$ADB" shell am force-stop org.study.sportly
"$ADB" shell monkey -p org.study.sportly -c android.intent.category.LAUNCHER 1 >/dev/null
echo "Готово: SPORTLY запущен на эмуляторе."
