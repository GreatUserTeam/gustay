// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (c) 2026 GreatUserTeam

//! Native backend shared by the desktop and Android GUStay builds.
//!
//! Responsibilities:
//!   * persist the frontend settings object as a JSON file in the platform
//!     specific config directory;
//!   * report the settings file path (useful for diagnostics);
//!   * accept `.gustay` files opened through the command line (Windows /
//!     Linux) or through the platform "open with" event (macOS / Android) and
//!     hand their contents to the frontend.

use std::fs;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, Runtime, Url};
use tauri_plugin_fs::{FilePath, FsExt};
use tauri_plugin_opener::OpenerExt;

/// Directory created below the platform config directory on desktop.
const SETTINGS_DIR: &str = "GUStay";
/// File name used on every platform.
const SETTINGS_FILE: &str = "settings.json";
/// Guards against an unbounded queue if the window takes a long time to load.
const MAX_PENDING_THEMES: usize = 16;

/// A `.gustay` document that has been read but not yet imported by the UI.
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ThemePayload {
    /// Stable identifier used by the frontend to de-duplicate the event and
    /// the pending-queue delivery paths.
    pub id: String,
    /// Suggested file name, e.g. `my-theme.gustay`.
    pub name: String,
    /// Raw UTF-8 contents of the theme file.
    pub content: String,
}

static PENDING_THEMES: Mutex<Vec<ThemePayload>> = Mutex::new(Vec::new());
static THEME_COUNTER: AtomicU64 = AtomicU64::new(0);

/// Returns the exact settings path required by the platform.
///
/// * Windows: `%APPDATA%\GUStay\settings.json`
/// * macOS:   `~/Library/Application Support/GUStay/settings.json`
/// * Linux:   `~/.config/GUStay/settings.json` (or `$XDG_CONFIG_HOME/...`)
/// * Android: `<context.filesDir()>/settings.json`
fn settings_path<R: Runtime>(app: &AppHandle<R>) -> Result<PathBuf, String> {
    #[cfg(target_os = "android")]
    {
        // Tauri resolves app_data_dir() to Context.dataDir on Android, which
        // is the parent of filesDir(), so append "files" to match filesDir().
        let data_dir = app
            .path()
            .app_data_dir()
            .map_err(|error| format!("не удалось определить каталог данных: {error}"))?;
        Ok(data_dir.join("files").join(SETTINGS_FILE))
    }

    #[cfg(not(target_os = "android"))]
    {
        // config_dir() is %APPDATA% on Windows, ~/Library/Application Support
        // on macOS and ~/.config on Linux.
        let config_dir = app
            .path()
            .config_dir()
            .map_err(|error| format!("не удалось определить каталог настроек: {error}"))?;
        Ok(config_dir.join(SETTINGS_DIR).join(SETTINGS_FILE))
    }
}

/// Writes the settings JSON atomically (temporary file + rename) so a crash
/// midway cannot leave a half-written settings file behind.
#[tauri::command]
fn save_settings<R: Runtime>(app: AppHandle<R>, json: String) -> Result<(), String> {
    // Reject broken payloads before they reach the disk. The frontend always
    // sends a JSON object produced by JSON.stringify().
    let parsed: serde_json::Value =
        serde_json::from_str(&json).map_err(|error| format!("некорректный JSON настроек: {error}"))?;
    if !parsed.is_object() {
        return Err("настройки должны быть JSON-объектом".to_string());
    }

    let path = settings_path(&app)?;
    let parent = path
        .parent()
        .ok_or_else(|| "у пути к settings.json нет родительского каталога".to_string())?;
    fs::create_dir_all(parent)
        .map_err(|error| format!("не удалось создать {}: {error}", parent.display()))?;

    let temporary = path.with_extension("json.tmp");
    fs::write(&temporary, json.as_bytes())
        .map_err(|error| format!("не удалось записать {}: {error}", temporary.display()))?;

    if let Err(error) = fs::rename(&temporary, &path) {
        // Windows refuses to replace an existing file with rename(); remove
        // the old file and try once more before reporting the failure.
        let _ = fs::remove_file(&path);
        fs::rename(&temporary, &path).map_err(|second_error| {
            format!(
                "не удалось заменить {}: {error}; повторная попытка: {second_error}",
                path.display()
            )
        })?;
    }

    Ok(())
}

/// Reads the settings JSON file. A missing file is not an error: the app then
/// starts with its built-in defaults and creates the file on the first change.
#[tauri::command]
fn load_settings<R: Runtime>(app: AppHandle<R>) -> Result<String, String> {
    let path = settings_path(&app)?;

    let contents = match fs::read_to_string(&path) {
        Ok(contents) => contents,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok("{}".to_string()),
        Err(error) => {
            return Err(format!(
                "не удалось прочитать {}: {error}",
                path.display()
            ))
        }
    };

    let parsed: serde_json::Value = serde_json::from_str(&contents).map_err(|error| {
        format!(
            "файл {} содержит некорректный JSON: {error}",
            path.display()
        )
    })?;
    if !parsed.is_object() {
        return Err(format!(
            "файл {} должен содержать JSON-объект",
            path.display()
        ));
    }

    Ok(contents)
}

/// Returns the absolute settings path for the "About / diagnostics" UI.
#[tauri::command]
fn get_settings_path<R: Runtime>(app: AppHandle<R>) -> Result<String, String> {
    settings_path(&app).map(|path| path.display().to_string())
}

/// Opens an external http(s) link in the system default browser.
///
/// The frontend normally uses `window.__TAURI__.opener.openUrl`, but this
/// command is a reliable fallback when the plugin's global JavaScript API is
/// not exposed by the current Tauri build.
#[tauri::command]
fn open_external<R: Runtime>(app: AppHandle<R>, url: String) -> Result<(), String> {
    let parsed = Url::parse(&url).map_err(|error| format!("некорректная ссылка {url}: {error}"))?;
    match parsed.scheme() {
        "http" | "https" => {}
        scheme => {
            return Err(format!(
                "разрешены только ссылки http/https, получена схема {scheme}"
            ))
        }
    }

    app.opener()
        .open_url(parsed.as_str(), None::<&str>)
        .map_err(|error| format!("не удалось открыть {url} во внешнем браузере: {error}"))
}

/// Takes every theme queued before the frontend was ready. The queue is
/// cleared atomically, and the frontend de-duplicates by `id` in case the same
/// document also arrived through the `file-open` event.
#[tauri::command]
fn take_pending_theme() -> Result<Vec<ThemePayload>, String> {
    let mut pending = PENDING_THEMES
        .lock()
        .map_err(|error| format!("очередь тем повреждена: {error}"))?;
    Ok(std::mem::take(&mut *pending))
}

fn next_theme_id() -> String {
    let counter = THEME_COUNTER.fetch_add(1, Ordering::Relaxed);
    let millis = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis();
    format!("{millis}-{counter}")
}

/// Derives a friendly file name from a path or URI without pulling in a
/// percent-decoding dependency.
fn theme_file_name(source: &str) -> String {
    let without_query = source
        .split(['?', '#'])
        .next()
        .unwrap_or("theme.gustay");
    let candidate = without_query
        .rsplit(['/', '\\'])
        .next()
        .filter(|name| !name.is_empty())
        .unwrap_or("theme.gustay");

    if candidate.to_ascii_lowercase().ends_with(".gustay") {
        candidate.to_string()
    } else {
        format!("{candidate}.gustay")
    }
}

/// Reads a theme from a regular path, `file://` URI or Android `content://`
/// URI. The fs plugin is used instead of `std::fs` so content URIs work on
/// Android and no path-scope configuration is needed for the Rust API.
fn read_theme<R: Runtime>(app: &AppHandle<R>, source: &str) -> Result<ThemePayload, String> {
    let file_path = if source.starts_with("content://") || source.starts_with("file://") {
        let url = Url::parse(source)
            .map_err(|error| format!("некорректный URI темы {source}: {error}"))?;
        FilePath::Url(url)
    } else {
        FilePath::Path(PathBuf::from(source))
    };

    let bytes = app
        .fs()
        .read(file_path)
        .map_err(|error| format!("не удалось прочитать тему {source}: {error}"))?;

    let content = String::from_utf8(bytes)
        .map_err(|error| format!("тема {source} не является текстовым UTF-8 файлом: {error}"))?;

    Ok(ThemePayload {
        id: next_theme_id(),
        name: theme_file_name(source),
        content,
    })
}

/// Queues a theme for the frontend and emits it immediately when a listener is
/// already attached. Errors are logged instead of being propagated because the
/// file may come from an OS event where there is nobody to report to.
fn queue_theme<R: Runtime>(app: &AppHandle<R>, source: &str) {
    let payload = match read_theme(app, source) {
        Ok(payload) => payload,
        Err(error) => {
            eprintln!("[GUStay] {error}");
            return;
        }
    };

    if let Ok(mut pending) = PENDING_THEMES.lock() {
        if pending.len() >= MAX_PENDING_THEMES {
            pending.remove(0);
        }
        pending.push(payload.clone());
    }

    if let Err(error) = app.emit("file-open", payload) {
        eprintln!("[GUStay] не удалось отправить событие file-open: {error}");
    }
}

/// Handles the `path/to/file.gustay` argument used by Windows and Linux file
/// managers. Flags inserted by desktop environments are ignored.
fn queue_cli_args<R: Runtime>(app: &AppHandle<R>) {
    for argument in std::env::args_os().skip(1) {
        let argument = argument.to_string_lossy();
        if argument.starts_with('-') {
            continue;
        }
        queue_theme(app, &argument);
    }
}

/// Application entry point shared by `main.rs` and the Android glue code.
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            queue_cli_args(app.handle());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            save_settings,
            load_settings,
            get_settings_path,
            open_external,
            take_pending_theme
        ])
        .build(tauri::generate_context!())
        .expect("не удалось собрать приложение GUStay")
        .run(|app, event| {
            #[cfg(any(
                target_os = "macos",
                target_os = "ios",
                target_os = "android"
            ))]
            if let tauri::RunEvent::Opened { urls } = event {
                for url in urls {
                    queue_theme(app, url.as_str());
                }
            }

            #[cfg(not(any(
                target_os = "macos",
                target_os = "ios",
                target_os = "android"
            )))]
            {
                let _ = (app, event);
            }
        });
}
