#!/usr/bin/env python3
"""Generate the four independent Tauri v2 projects.

The canonical frontend, Rust sources, icons and Linux/Windows bundle helpers
live in shared/. This script copies them into android/, linux/, windows/ and
macos/, and writes each platform's tauri.conf.json, Cargo.toml and capabilities.

Run from the repository root:  python3 shared/generate_projects.py
"""

from __future__ import annotations

import json
import shutil
import stat
from pathlib import Path

import build_frontend

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
# Icons generated once by `npx @tauri-apps/cli@2 icon shared/icon.svg` and
# committed next to the source SVG, so regeneration works without /tmp.
ICON_SOURCE = SHARED / "icons"
PLATFORMS = ("android", "linux", "windows", "macos")

PRODUCT_NAME = "GUStay"
VERSION = "1.0.0"
IDENTIFIER = "net.guteam.gustay"
BINARY_NAME = "gustay"
HOMEPAGE = "https://stay.guteam.net/"
DESCRIPTION = "Утилита, не дающая экрану погаснуть, с темами оформления."

ICON_FILES = [
    "32x32.png",
    "64x64.png",
    "128x128.png",
    "128x128@2x.png",
    "icon.icns",
    "icon.ico",
    "icon.png",
]
ICON_BUNDLE_PATHS = [f"icons/{name}" for name in ICON_FILES]

FILE_ASSOCIATION = {
    "ext": ["gustay"],
    "name": "GUStay Theme",
    "description": "Тема оформления GUStay",
    "mimeType": "application/x-gustay",
    "role": "Editor",
    "rank": "Owner",
    "exportedType": {
        "identifier": "net.guteam.gustay.theme",
        "conformsTo": ["public.json", "public.data"],
    },
    "androidIntentActionFilters": ["view"],
}

CSP = (
    "default-src 'self'; "
    "img-src 'self' data: blob:; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self' data:; "
    "script-src 'self' 'unsafe-inline'; "
    "media-src 'self' data: blob:; "
    "connect-src ipc: http://ipc.localhost; "
    "object-src 'none'"
)

CARGO_TOML = """[package]
name = "gustay"
version = "1.0.0"
description = "GUStay - keep the screen awake with theme support"
authors = ["GUTeam"]
edition = "2021"
rust-version = "1.77.2"

[lib]
name = "gustay_lib"
crate-type = ["staticlib", "cdylib", "rlib"]

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-fs = "2"
tauri-plugin-opener = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"

[profile.release]
codegen-units = 1
lto = true
opt-level = "s"
panic = "abort"
strip = true
"""

BUILD_RS = """fn main() {
    tauri_build::build()
}
"""

PACKAGE_JSON = {
    "name": "gustay-{platform}",
    "private": True,
    "version": VERSION,
    "description": "GUStay native shell for {platform}",
    "scripts": {"tauri": "tauri", "dev": "tauri dev", "build": "tauri build"},
    "devDependencies": {"@tauri-apps/cli": "^2.12.4"},
}


GITIGNORE = """/target
/gen
node_modules
*.log
"""


def base_config(platform: str) -> dict:
    targets = {
        "android": "all",
        "linux": ["deb", "appimage"],
        "windows": ["msi", "nsis"],
        "macos": ["app", "dmg"],
    }[platform]

    config: dict = {
        "$schema": "https://schema.tauri.app/config/2",
        "productName": PRODUCT_NAME,
        "version": VERSION,
        "identifier": IDENTIFIER,
        "build": {
            # Only the generated index.html is embedded. The parent directory
            # also contains src-tauri/target, which must not be bundled.
            "frontendDist": ["../index.html"],
        },
        "app": {
            "withGlobalTauri": True,
            "windows": [
                {
                    "label": "main",
                    "title": PRODUCT_NAME,
                    "width": 1280,
                    "height": 820,
                    "minWidth": 900,
                    "minHeight": 600,
                    "center": True,
                    "resizable": True,
                    "fullscreen": False,
                }
            ],
            "security": {
                "csp": CSP,
                # The app creates <style> elements at runtime for themes, so
                # Tauri must not replace 'unsafe-inline' with a hash-only policy.
                "dangerousDisableAssetCspModification": True,
            },
        },
        "bundle": {
            "active": True,
            "targets": targets,
            "icon": ICON_BUNDLE_PATHS,
            "fileAssociations": [FILE_ASSOCIATION],
            "category": "Utility",
            "shortDescription": "Не даёт экрану погаснуть",
            "longDescription": DESCRIPTION,
            "copyright": "© GUTeam",
            "publisher": "GUTeam",
            "homepage": HOMEPAGE,
        },
        "plugins": {},
    }

    if platform == "linux":
        config["bundle"]["linux"] = {
            "deb": {
                "depends": [],
                "desktopTemplate": "bundle/linux/gustay.desktop",
                "files": {
                    "/usr/share/mime/packages/net.guteam.gustay.xml": "bundle/linux/net.guteam.gustay.xml"
                },
                "postInstallScript": "bundle/linux/postinst.sh",
                "postRemoveScript": "bundle/linux/postrm.sh",
            },
            "appimage": {
                "bundleMediaFramework": False,
            },
        }

    if platform == "windows":
        config["bundle"]["windows"] = {
            "nsis": {
                "installMode": "both",
                "installerHooks": "bundle/windows/hooks.nsh",
                # Without these Tauri keeps the stock NSIS icon on the
                # installer/uninstaller executable, while the installed app and
                # its shortcuts already use the GUStay icon.
                "installerIcon": "icons/icon.ico",
                "uninstallerIcon": "icons/icon.ico",
                "languages": ["Russian", "English"],
                "displayLanguageSelector": True,
            }
        }

    if platform == "macos":
        config["bundle"]["macOS"] = {
            "minimumSystemVersion": "10.15",
            "dmg": {
                "windowSize": {"width": 660, "height": 400},
                "appPosition": {"x": 180, "y": 170},
                "applicationFolderPosition": {"x": 480, "y": 170},
            },
        }

    if platform == "android":
        config["bundle"]["android"] = {
            "minSdkVersion": 24,
        }

    return config


ANDROID_ICON_BACKGROUND = """<?xml version="1.0" encoding="utf-8"?>
<resources>
  <color name="ic_launcher_background">#0B0B0B</color>
</resources>
"""


def write_android_icon_background(values_dir: Path) -> None:
    """Use the same dark background as the desktop icon.

    The Tauri icon generator defaults the adaptive-icon background to white,
    which would add a white ring around GUStay's dark circular artwork.
    """
    values_dir.mkdir(parents=True, exist_ok=True)
    (values_dir / "ic_launcher_background.xml").write_text(
        ANDROID_ICON_BACKGROUND, encoding="utf-8"
    )


def sync_android_resources(project: Path, icons_dir: Path) -> None:
    """Copy adaptive/legacy launcher icons into the generated Gradle project.

    `tauri android init` creates the Gradle project with Tauri's default
    launcher icon and later `tauri android build` calls do not refresh it.
    Copying the generated Android icon set here keeps the APK icon identical
    to the desktop icon on every build.
    """
    res_dir = (
        project
        / "src-tauri"
        / "gen"
        / "android"
        / "app"
        / "src"
        / "main"
        / "res"
    )
    source = icons_dir / "android"
    if not res_dir.is_dir() or not source.is_dir():
        return

    for entry in source.iterdir():
        destination = res_dir / entry.name
        if entry.is_dir():
            shutil.copytree(entry, destination, dirs_exist_ok=True)
        else:
            shutil.copyfile(entry, destination)

    write_android_icon_background(source / "values")
    write_android_icon_background(res_dir / "values")


def prepare_project(platform: str) -> Path:
    project = ROOT / platform
    tauri_dir = project / "src-tauri"
    src_dir = tauri_dir / "src"
    icons_dir = tauri_dir / "icons"

    src_dir.mkdir(parents=True, exist_ok=True)
    icons_dir.mkdir(parents=True, exist_ok=True)
    (tauri_dir / "capabilities").mkdir(parents=True, exist_ok=True)

    # Shared Rust sources are copied so every directory remains a standalone
    # project (a Windows checkout does not need Unix symlink support).
    for name in ("lib.rs", "main.rs"):
        shutil.copyfile(SHARED / "src-tauri-src" / name, src_dir / name)

    # Desktop icons.
    if not ICON_SOURCE.exists():
        raise SystemExit(
            f"icon source {ICON_SOURCE} is missing; run `npx @tauri-apps/cli@2 icon {SHARED / 'icon.svg'}` first"
        )
    for icon in ICON_FILES:
        destination = icons_dir / icon
        shutil.copyfile(ICON_SOURCE / icon, destination)

    # Android adaptive icons are consumed by Gradle, not by tauri.conf.json.
    android_icons = ICON_SOURCE / "android"
    if platform == "android" and android_icons.is_dir():
        shutil.copytree(android_icons, icons_dir / "android", dirs_exist_ok=True)
        sync_android_resources(project, icons_dir)

    if platform == "linux":
        linux_bundle = tauri_dir / "bundle" / "linux"
        linux_bundle.mkdir(parents=True, exist_ok=True)
        for name in ("gustay.desktop", "net.guteam.gustay.xml", "postinst.sh", "postrm.sh"):
            shutil.copyfile(SHARED / "bundle" / "linux" / name, linux_bundle / name)
        for script in ("postinst.sh", "postrm.sh"):
            path = linux_bundle / script
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    if platform == "windows":
        windows_bundle = tauri_dir / "bundle" / "windows"
        windows_bundle.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            SHARED / "bundle" / "windows" / "hooks.nsh",
            windows_bundle / "hooks.nsh",
        )

    (tauri_dir / "Cargo.toml").write_text(CARGO_TOML, encoding="utf-8")
    (tauri_dir / "build.rs").write_text(BUILD_RS, encoding="utf-8")
    (tauri_dir / "tauri.conf.json").write_text(
        json.dumps(base_config(platform), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (tauri_dir / "capabilities" / "default.json").write_text(
        json.dumps(
            {
                "$schema": "../gen/schemas/desktop-schema.json",
                "identifier": "default",
                "description": "Основное окно GUStay",
                "windows": ["main"],
                "permissions": ["core:default", "opener:default"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (tauri_dir / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    package_json = json.loads(json.dumps(PACKAGE_JSON).replace("{platform}", platform))
    (project / "package.json").write_text(
        json.dumps(package_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return project


def main() -> None:
    build_frontend.main()
    for platform in PLATFORMS:
        prepare_project(platform)
        print(f"generated {ROOT / platform}")


if __name__ == "__main__":
    main()
