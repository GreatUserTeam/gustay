# GUStay — нативные приложения на Tauri v2

Исходный `GUStay.html` превращён в четыре независимых проекта Tauri v2:
`android/`, `linux/`, `windows/`, `macos/`. Electron не используется.
Frontend полностью автономен: Google Fonts удалены, шрифт Inter встроен в HTML
как base64 WOFF2.

## Что реализовано

- Отдельный `index.html` и отдельный `src-tauri` в каждом каталоге.
- Нативное хранение настроек в JSON с атомарной записью.
- Команды Rust:
  - `save_settings(json: String) -> Result<(), String>`;
  - `load_settings() -> Result<String, String>`;
  - `get_settings_path() -> Result<String, String>`.
- Ассоциация `.gustay`, MIME-тип `application/x-gustay`, общая иконка.
- Обработка файлов:
  - Windows/Linux — аргумент командной строки;
  - macOS/Android — событие `RunEvent::Opened`;
  - запуск до готовности WebView — очередь `take_pending_theme`;
  - frontend слушает `file-open` и вызывает
    `importTheme(new File([content], 'theme.gustay'))`.
- Сохранение настроек с задержкой 300 мс (debounce) и синхронный
  `localStorage`-фасад, поэтому исходный код приложения не пришлось
  переписывать на async.
- Публичные JS-хелперы: `saveSettings`, `loadSettings`, `getSettingsPath`,
  `window.GUStayNative`.
- Иконки `.ico`, `.icns`, PNG, Android mipmap, Linux `.desktop` и MIME XML,
  Windows NSIS-хуки.
- Внешние ссылки (`http://`, `https://`) открываются в системном браузере
  через `tauri-plugin-opener`; WebView остаётся на приложении.

## Структура

```text
.
├── android/
│   ├── artifacts/
│   │   └── GUStay_1.0.0_arm64.apk
│   ├── src-tauri/
│   │   ├── capabilities/
│   │   ├── icons/
│   │   ├── src/
│   │   ├── Cargo.lock
│   │   ├── Cargo.toml
│   │   ├── build.rs
│   │   └── tauri.conf.json
│   ├── index.html
│   └── package.json
├── linux/
│   ├── src-tauri/
│   │   ├── bundle/
│   │   ├── capabilities/
│   │   ├── icons/
│   │   ├── src/
│   │   ├── Cargo.lock
│   │   ├── Cargo.toml
│   │   ├── build.rs
│   │   └── tauri.conf.json
│   ├── index.html
│   └── package.json
├── macos/
│   ├── src-tauri/
│   │   ├── capabilities/
│   │   ├── icons/
│   │   ├── src/
│   │   ├── Cargo.lock
│   │   ├── Cargo.toml
│   │   ├── build.rs
│   │   └── tauri.conf.json
│   ├── index.html
│   └── package.json
├── shared/
│   ├── bundle/
│   │   ├── linux/
│   │   └── windows/
│   ├── fonts/
│   │   ├── cyrillic-ext.woff2
│   │   ├── cyrillic.woff2
│   │   ├── latin-ext.woff2
│   │   └── latin.woff2
│   ├── icons/
│   │   ├── android/
│   │   │   ├── mipmap-anydpi-v26/
│   │   │   ├── mipmap-hdpi/
│   │   │   ├── mipmap-mdpi/
│   │   │   ├── mipmap-xhdpi/
│   │   │   ├── mipmap-xxhdpi/
│   │   │   ├── mipmap-xxxhdpi/
│   │   │   └── values/ic_launcher_background.xml
│   │   ├── ios/
│   │   ├── 128x128.png
│   │   ├── 128x128@2x.png
│   │   ├── 32x32.png
│   │   ├── 64x64.png
│   │   ├── Square107x107Logo.png
│   │   ├── Square142x142Logo.png
│   │   ├── Square150x150Logo.png
│   │   ├── Square284x284Logo.png
│   │   ├── Square30x30Logo.png
│   │   ├── Square310x310Logo.png
│   │   ├── Square44x44Logo.png
│   │   ├── Square71x71Logo.png
│   │   ├── Square89x89Logo.png
│   │   ├── StoreLogo.png
│   │   ├── icon.icns
│   │   ├── icon.ico
│   │   └── icon.png
│   ├── src-tauri-src/
│   │   ├── lib.rs
│   │   └── main.rs
│   ├── bootstrap.js
│   ├── build_frontend.py
│   ├── generate_projects.py
│   ├── icon.svg
│   └── index.html
├── windows/
│   ├── artifacts/
│   │   └── GUStay_1.0.0_x64-setup.exe
│   ├── src-tauri/
│   │   ├── bundle/
│   │   ├── capabilities/
│   │   ├── icons/
│   │   ├── src/
│   │   ├── Cargo.lock
│   │   ├── Cargo.toml
│   │   ├── build.rs
│   │   └── tauri.conf.json
│   ├── index.html
│   └── package.json
├── GUStay.html
└── README.md
```

Служебные каталоги `src-tauri/target`, `src-tauri/gen` и `node_modules`
намеренно не показаны. `android/src-tauri/gen/android` — сгенерированный
Gradle-проект, он создаётся командами Tauri CLI.

## Готовые артефакты

| Платформа | Артефакт | Размер | Статус |
|---|---|---|---|
| Linux | `linux/src-tauri/target/release/bundle/deb/GUStay_1.0.0_amd64.deb` | 2,3 МиБ | пересобран с opener |
| Linux | `linux/src-tauri/target/release/bundle/appimage/GUStay_1.0.0_amd64.AppImage` | 105,7 МиБ | пересобран с opener |
| Windows | `windows/artifacts/GUStay_1.0.0_x64-setup.exe` | 1,7 МиБ | пересобран: новая иконка + opener |
| Windows | `windows/src-tauri/target/x86_64-pc-windows-gnu/release/gustay.exe` | 3,9 МиБ | пересобран кросс-компиляцией |
| Android | `android/artifacts/GUStay_1.0.0_arm64.apk` | 6,4 МиБ | пересобран, установлен и проверен на эмуляторе |
| macOS | — | — | сборка требует macOS/Xcode |

Контрольные суммы:

```text
981e77548bd00a44c9e4150289d5ba60e186051717e86799f62387b949484b89  icons/icon.png (Android = Linux)
bbda660a015ab6b8ae2dfdf935ddc7d77b19d2b30543a64414f2dcea3e7b43d5  android/artifacts/GUStay_1.0.0_arm64.apk
725f87be8c3c26ec75c5b0cd10f7ce9cdefb5039e5f9acfbca357e42599b5183  linux/.../deb/GUStay_1.0.0_amd64.deb
32d6649a6a6c24bffb56e0a9c85c47d532a7fcdf16866a8f573048431f6bea0a  linux/.../appimage/GUStay_1.0.0_amd64.AppImage
ddb0d71d97227e9405e083163b49beff4e728a0162875a20edb13845362220c7  windows/artifacts/GUStay_1.0.0_x64-setup.exe
```

MSI для Windows на Linux не собран: для WiX нужен Windows или Wine с
установленным WiX. Цель `msi` уже прописана в конфигурации, её можно собрать
на Windows одной командой (см. ниже).

## Иконки

Единственный источник иконок — `shared/icon.svg`. Из него один раз
сгенерирован набор `shared/icons/` (`npx @tauri-apps/cli@2 icon
shared/icon.svg`), и уже этот набор копируется в проекты скриптом
`shared/generate_projects.py`. Зависимости от `/tmp` и от сети при
пересборке нет.

- `shared/icons/icon.png` — эталон: SHA-256
  `981e77548bd00a44c9e4150289d5ba60e186051717e86799f62387b949484b89`.
  Тот же файл лежит в `linux/`, `windows/`, `macos/` и `android/`
  (`src-tauri/icons/icon.png`), поэтому иконка Android совпадает с Linux
  пиксельно.
- Android: `shared/icons/android/` содержит adaptive-icon
  (`mipmap-anydpi-v26/ic_launcher.xml` + `ic_launcher_foreground.png`),
  legacy `mipmap-*` и `values/ic_launcher_background.xml` с фоном `#0B0B0B`.
  Белый фон, который Tauri ставит по умолчанию, давал бы светлое кольцо
  вокруг тёмного круглого логотипа.
- `tauri android init` создаёт Gradle-проект с иконкой Tauri, а последующие
  `tauri android build` её не обновляют. Поэтому
  `shared/generate_projects.py` (функция `sync_android_resources`) копирует
  `shared/icons/android/*` в
  `android/src-tauri/gen/android/app/src/main/res/mipmap-*` и
  `res/values/`. То есть runtime-ресурсы APK синхронизируются при каждом
  запуске генератора, а не только на этапе `init`.
- Windows: `installerIcon`/`uninstallerIcon` в `tauri.conf.json` указывают на
  `icons/icon.ico`, поэтому иконка есть и у самого установщика (без этого
  Tauri оставляет стандартную иконку NSIS).

## Ссылки и внешний браузер

В исходном `GUStay.html` часть ссылок ведёт на внешние сайты. В WebView
Tauri такой переход либо ничего не делал, либо уводил всё окно с приложения.
Теперь:

- `shared/src-tauri-src/lib.rs` подключает `tauri-plugin-opener` и отдаёт
  команду-запасной вариант `open_external` (разрешены только `http`/`https`);
- `shared/bootstrap.js` содержит `openExternalUrl(href)` и
  `installExternalLinkHandler()`: клик по любой ссылке `a[href]` с
  `http://` или `https://` перехватывается, ссылка уходит в
  `window.__TAURI__.opener.openUrl`, WebView остаётся на GUStay;
- в `capabilities/default.json` добавлено разрешение `opener:default`
  (`allow-open-url`, схемы `https://*`, `tel:*`);
- если приложение открыто в обычном браузере (без `window.__TAURI__`),
  используется `window.open`, то есть поведение сайта не меняется.

Проверено: Linux — `xdg-open` вызван с `https://store.guteam.net/stay`,
окно осталось на приложении, обработчик видит все 10 ссылок; Android —
через Chrome DevTools Protocol (`opener: true`, 10 ссылок). Windows и macOS
собраны с тем же кодом, но живьём не проверялись.

## Где лежат настройки


| Платформа | Путь |
|---|---|
| Windows | `%APPDATA%\GUStay\settings.json` |
| macOS | `~/Library/Application Support/GUStay/settings.json` |
| Linux | `${XDG_CONFIG_HOME:-~/.config}/GUStay/settings.json` |
| Android | `context.filesDir()/settings.json`, то есть `/data/data/com.guteam.gustay/files/settings.json` |

`save_settings` проверяет, что переданный JSON является объектом, пишет во
временный файл и делает `rename`, чтобы не оставить повреждённый файл при
сбое. Если файла нет, `load_settings` возвращает `{}` и приложение стартует
со значениями по умолчанию.

## Как работает сохранение

Исходное приложение обращается к `localStorage` синхронно в 238 местах.
Перед запуском приложения мост `shared/bootstrap.js`:

1. загружает `settings.json` через `load_settings`;
2. заполняет синхронный кэш;
3. подменяет `window.localStorage` совместимым фасадом;
4. вызывает `window.__gustayBoot()`, то есть исходное приложение;
5. сохраняет изменения кэша через `save_settings` с задержкой 300 мс;
6. при закрытии окна делает попытку немедленного сохранения.

Поэтому существующие вызовы `localStorage.getItem/setItem/removeItem/clear`
продолжают работать, но данные попадают в нативный JSON-файл.

## Ассоциация `.gustay`

- MIME-тип: `application/x-gustay`.
- Linux: MIME XML устанавливается в `/usr/share/mime/packages`, `.desktop`
  содержит `Exec=gustay %F` и `MimeType=application/x-gustay;`;
  `postinst.sh`/`postrm.sh` обновляют базы MIME и desktop.
- Windows: ассоциацию регистрирует установщик Tauri; NSIS-хук
  `SHChangeNotify(SHCNE_ASSOCCHANGED)` обновляет иконку и «Открыть с помощью»
  без перезапуска Explorer.
- macOS: UTI `com.guteam.gustay.theme`, роль Editor; файлы приходят через
  `RunEvent::Opened`.
- Android: `VIEW` intent-filter для `application/x-gustay` и
  `android:pathPattern=".*\\.gustay"`; файл приходит через
  `RunEvent::Opened`.

Если файл открыт до готовности WebView, Rust кладёт его в очередь
`PENDING_THEMES`, а frontend забирает очередь командой `take_pending_theme`
после подписки на `file-open`. Повторная доставка одного и того же файла
отсекается по `id`.

## Проверки, которые уже выполнены

- Linux: `cargo check`, release-сборка, запуск приложения; настройки
  сохранились в `~/.config/GUStay/settings.json` (6250 байт).
- Linux CLI: запуск `gustay /tmp/opencode/cli-test.gustay` импортировал тему,
  активная тема изменилась на `CLI Import Test`.
- Android: release APK установлен на эмулятор, приложение запустилось;
  `files/settings.json` создан (6250 байт).
- Android intent: открытие `file:///.../android-intent.gustay` с типом
  `application/x-gustay` доставило файл в работающее приложение; тема
  `Android Intent Test` появилась в списке и стала активной.
- Windows: полная кросс-сборка `x86_64-pc-windows-gnu` и NSIS-установщик;
  состав установщика проверен (`gustay.exe`, `WebView2Loader.dll`, плагины
  NSIS). В установщике 6 иконок GUStay (`RT_ICON` 16–256 px) — то есть
  используется новая иконка, а не стандартная от NSIS. Запуск на Windows не
  выполнялся.
- Иконки: `icon.png` во всех четырёх проектах совпадает с
  `shared/icons/icon.png` (SHA-256 `981e7754…`); PNG-полезная нагрузка
  `icons/icon.ico` найдена внутри собранных `gustay.exe` и установщика.
  Иконка на рабочем столе эмулятора Android совпала с Linux пиксельно
  (сравнение скриншота с эталоном — `PIXELS MATCH`).
- Ссылки: Linux — перехват клика по 10 ссылкам, `xdg-open` получил
  `https://store.guteam.net/stay`, WebView остался на GUStay; Android — те же
  10 ссылок через CDP, `opener: true`. Windows — в `gustay.exe` присутствуют
  `plugin:opener|open_url` и разрешение `allow-open-url`.
- macOS: кросс-проверка `cargo check --target x86_64-apple-darwin`
  остановилась из-за отсутствия Apple SDK/clang; артефакт не создавался.

## Сборка

Требования: Node.js 20+, Rust 1.77.2+, Tauri CLI 2.12.x. Для Linux нужны
`webkit2gtk-4.1`, `libappindicator3`, `librsvg2`, `patchelf` и стандартные
сборочные пакеты. Для Android — JDK 17, Android SDK и NDK `29.0.13846066`.

### Linux

```bash
cd /home/tigran/GUStay/linux
npx --yes @tauri-apps/cli@2 build --bundles deb,appimage
```

### Windows

На Windows 10/11 с Rust MSVC и WebView2:

```powershell
cd windows
npx --yes @tauri-apps/cli@2 build --bundles msi,nsis
```

Если MSI не нужен:

```powershell
npx --yes @tauri-apps/cli@2 build --bundles nsis
```

Кросс-сборка NSIS на Linux (экспериментально, нужны MinGW и `makensis`):

```bash
cd /home/tigran/GUStay/windows
# ALL_PROXY в этом окружении указывает на неработающий socks-прокси,
# из-за него бандлер не может скачать nsis_tauri_utils.dll с GitHub.
env -u ALL_PROXY -u all_proxy \
PATH=/tmp/opencode/nsis/bin:/tmp/opencode/mingw/root/usr/bin:$PATH \
npx --yes @tauri-apps/cli@2 build \
  --target x86_64-pc-windows-gnu --bundles nsis --no-sign
```

Если GitHub недоступен, DLL можно положить в кэш заранее, и бандлер не будет
её скачивать:

```bash
mkdir -p ~/.cache/tauri/NSIS/Plugins/x86-unicode/additional
cp nsis_tauri_utils.dll ~/.cache/tauri/NSIS/Plugins/x86-unicode/additional/
```

MinGW и NSIS для кросс-сборки распакованы в `/tmp/opencode/mingw/root/usr` и
`/tmp/opencode/nsis`; обёртка `/tmp/opencode/nsis/bin/makensis` выставляет
`NSISDIR=/tmp/opencode/nsis/usr/share/nsis`. Это временные каталоги: после
перезагрузки их нужно восстановить (`apt-get download gcc-mingw-w64-x86-64*
binutils-mingw-w64-x86-64 mingw-w64-x86-64-dev nsis nsis-common` и распаковать
через `dpkg -x`).

### macOS

На macOS с Xcode:

```bash
cd /home/tigran/GUStay/macos
npx --yes @tauri-apps/cli@2 build --bundles app,dmg
```

### Android

```bash
cd /home/tigran/GUStay/android
ANDROID_HOME=/home/tigran/Android/Sdk \
ANDROID_SDK_ROOT=/home/tigran/Android/Sdk \
NDK_HOME=/home/tigran/Android/Sdk/ndk/29.0.13846066 \
npx --yes @tauri-apps/cli@2 android build --apk --target aarch64 --ci
```

Неподписанный APK появится в
`android/src-tauri/gen/android/app/build/outputs/apk/universal/release/app-universal-release-unsigned.apk`.
Подпись и выравнивание:

```bash
BT=/home/tigran/Android/Sdk/build-tools/36.0.0
cd /home/tigran/GUStay/android/src-tauri/gen/android/app/build/outputs/apk/universal/release
$BT/zipalign -f 4 app-universal-release-unsigned.apk GUStay_1.0.0_arm64-aligned.apk
$BT/apksigner sign \
  --ks /path/to/release.keystore --ks-key-alias gustay \
  --out /home/tigran/GUStay/android/artifacts/GUStay_1.0.0_arm64.apk \
  GUStay_1.0.0_arm64-aligned.apk
```

Текущий APK подписан временным ключом
`/tmp/opencode/gustay-dev.keystore` (alias `gustay`, пароли `gustaydev`).
Для публикации нужен собственный production-ключ.

## Пересборка frontend и конфигураций

`index.html` в четырёх каталогах генерируется из `GUStay.html`. Не редактируйте
его напрямую: правьте `shared/`, затем выполните:

```bash
cd /home/tigran/GUStay
python3 shared/generate_projects.py
```

Скрипт обновит `shared/index.html`, скопирует его во все четыре проекта,
синхронизирует Rust-исходники, иконки, конфигурации и упаковочные файлы.
Иконки лежат в `shared/icons`, поэтому пересборка не зависит от `/tmp`.

## Созданные и изменённые файлы

`GUStay.html` не изменялся. Все остальные файлы проекта созданы заново:

- корень: `README.md`;
- `shared/`:
  - `bootstrap.js` — мост настроек, `localStorage`-фасад, `file-open`,
    перехват внешних ссылок (`openExternalUrl`,
    `installExternalLinkHandler`);
  - `build_frontend.py` — очистка HTML, встраивание Inter, обёртка приложения;
  - `generate_projects.py` — генерация четырёх проектов, синхронизация иконок
    и `android/.../res/mipmap-*`;
  - `src-tauri-src/lib.rs`, `main.rs` — общий Rust-бэкенд
    (`tauri-plugin-opener`, команда `open_external_url`);
  - `bundle/linux/*` — `.desktop`, MIME XML, postinst/postrm;
  - `bundle/windows/hooks.nsh` — обновление ассоциаций Explorer;
  - `fonts/*`, `icon.svg`, `icons/*` (включая `icons/android/*`), `index.html`;
- в каждом из `android/`, `linux/`, `windows/`, `macos/`:
  - `index.html`, `package.json`;
  - `src-tauri/Cargo.toml` (`tauri-plugin-opener = "2"`), `Cargo.lock`,
    `build.rs`, `tauri.conf.json`;
  - `src-tauri/src/lib.rs`, `main.rs`;
  - `src-tauri/capabilities/default.json` (`opener:default`);
  - `src-tauri/icons/*`;
- `windows/src-tauri/tauri.conf.json` — `installerIcon`/`uninstallerIcon`;
- `linux/src-tauri/bundle/linux/*`;
- `windows/src-tauri/bundle/windows/hooks.nsh`;
- `android/src-tauri/gen/android/app/src/main/res/mipmap-*` и `res/values/` —
  иконки, синхронизированные из `shared/icons/android/`;
- `android/src-tauri/gen/android/*` — сгенерировано Tauri CLI;
- артефакты в `android/artifacts`, `windows/artifacts` и
  `linux/src-tauri/target/release/bundle/`.

## Ограничения

- Windows-установщик не подписан; SmartScreen может показать предупреждение.
- MSI требует Windows (или Wine) с установленным WiX Toolset: на этой машине
  MSI не собран. NSIS-установщик собран и проверен по составу.
- macOS-приложение и DMG не собраны: на Linux нет Apple SDK/Xcode.
  Конфигурация macOS готова, сборку нужно выполнять на macOS.
- Кросс-сборка Windows NSIS на Linux требует MinGW, `makensis` и доступа к
  GitHub: бандлер скачивает `nsis_tauri_utils.dll`. Без сети к GitHub сборка
  падает с `io: Connection refused` — DLL нужно заранее положить в
  `~/.cache/tauri/NSIS/Plugins/x86-unicode/additional/`. Кроме того, в этом
  окружении сломан `ALL_PROXY` (socks на закрытом порту), поэтому сборку надо
  запускать через `env -u ALL_PROXY -u all_proxy …`.
- Android APK собран только для `arm64-v8a` и подписан временным ключом.
  AAB для Google Play не создавался.
- На Windows и Linux повторный запуск открывает новый процесс: плагин
  single-instance не подключён.
- Кросс-компиляция Windows на Linux помечена Tauri как экспериментальная;
  финальную проверку установщика, иконок в Explorer и ассоциаций нужно делать
  на Windows.
- Внешние ссылки проверены вживую только на Linux и Android; Windows и macOS
  собраны с тем же кодом, но запуск не выполнялся.
- Цвета/темы проверялись на Linux и Android; визуальная проверка Windows и
  macOS не выполнялась.

## Лицензия

Проект распространяется под лицензией [GNU General Public License v3.0](LICENSE).  
Copyright (c) 2026 GreatUserTeam.  
SPDX-License-Identifier: `GPL-3.0-or-later`.
