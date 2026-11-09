[app]
title = SPORTLY
package.name = sportly
package.domain = org.study
source.dir = .
source.include_exts = py,png,jpg,ttf,json
source.exclude_dirs = .venv,tools,bin,.buildozer,shots,photo,.idea
version = 1.0
requirements = python3,kivy==2.3.1
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 24
android.archs = x86_64, arm64-v8a
android.accept_sdk_license = True
android.permissions = INTERNET,ACCESS_NETWORK_STATE

[buildozer]
log_level = 2
build_dir = /home/artem111/.sportly-build
