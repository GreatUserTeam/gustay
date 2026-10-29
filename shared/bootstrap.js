/*
 * SPDX-License-Identifier: GPL-3.0-or-later
 * Copyright (c) 2026 GreatUserTeam
 *
 * GUStay native bridge (shared by all desktop/mobile builds).
 *
 * The original web app uses localStorage synchronously in more than two
 * hundred places. Rewriting every call site to async code would be invasive
 * and would change the behaviour of the app, so this bridge keeps a small
 * synchronous in-memory cache that is:
 *
 *   1. hydrated from the native JSON settings file before the app starts;
 *   2. exposed through a localStorage-compatible object;
 *   3. persisted back to disk with a 300 ms debounce.
 *
 * It also exposes the requested async helpers (saveSettings / loadSettings),
 * the settings file path, and the `.gustay` "file-open" integration.
 */
(function () {
  'use strict';

  var TAURI = window.__TAURI__ || null;
  var hasTauri = !!(TAURI && TAURI.core && typeof TAURI.core.invoke === 'function');
  var SETTINGS_DEBOUNCE_MS = 300;

  // Prototype-less object so arbitrary theme keys cannot collide with
  // Object.prototype members.
  var cache = Object.create(null);
  var persistTimer = 0;
  var persistRunning = false;
  var persistAgain = false;
  var seenThemeIds = Object.create(null);

  function logError(message, error) {
    if (window.console && window.console.error) {
      window.console.error('[GUStay] ' + message, error || '');
    }
  }

  function invoke(command, args) {
    if (!hasTauri) {
      return Promise.reject(new Error('Tauri IPC is not available'));
    }
    return TAURI.core.invoke(command, args);
  }

  function hasOwn(object, key) {
    return Object.prototype.hasOwnProperty.call(object, key);
  }

  /* ------------------------------------------------------------------ */
  /* Settings persistence                                               */
  /* ------------------------------------------------------------------ */

  function settingsJson() {
    return JSON.stringify(cache);
  }

  function persistSettings() {
    if (!hasTauri) {
      return Promise.resolve();
    }

    // Coalesce concurrent writes: only one IPC call may be in flight.
    if (persistRunning) {
      persistAgain = true;
      return Promise.resolve();
    }

    persistRunning = true;
    return invoke('save_settings', { json: settingsJson() })
      .catch(function (error) {
        logError('failed to save settings', error);
      })
      .then(function () {
        persistRunning = false;
        if (persistAgain) {
          persistAgain = false;
          schedulePersist();
        }
      });
  }

  function schedulePersist() {
    if (!hasTauri) {
      return;
    }
    if (persistTimer) {
      window.clearTimeout(persistTimer);
    }
    persistTimer = window.setTimeout(function () {
      persistTimer = 0;
      persistSettings();
    }, SETTINGS_DEBOUNCE_MS);
  }

  /* ------------------------------------------------------------------ */
  /* localStorage-compatible facade                                     */
  /* ------------------------------------------------------------------ */

  var storageFacade = {
    getItem: function (key) {
      key = String(key);
      return hasOwn(cache, key) ? cache[key] : null;
    },
    setItem: function (key, value) {
      cache[String(key)] = String(value);
      schedulePersist();
    },
    removeItem: function (key) {
      delete cache[String(key)];
      schedulePersist();
    },
    clear: function () {
      Object.keys(cache).forEach(function (key) {
        delete cache[key];
      });
      schedulePersist();
    },
    key: function (index) {
      var keys = Object.keys(cache);
      index = Number(index);
      return index >= 0 && index < keys.length ? keys[index] : null;
    }
  };

  Object.defineProperty(storageFacade, 'length', {
    enumerable: true,
    get: function () {
      return Object.keys(cache).length;
    }
  });

  function installStorageFacade() {
    try {
      Object.defineProperty(window, 'localStorage', {
        configurable: true,
        enumerable: true,
        get: function () {
          return storageFacade;
        }
      });
      return;
    } catch (error) {
      logError('could not replace window.localStorage, patching Storage.prototype', error);
    }

    // Fallback for engines that refuse to redefine the Window property.
    try {
      var proto = window.Storage && window.Storage.prototype;
      if (!proto) {
        return;
      }
      proto.getItem = storageFacade.getItem;
      proto.setItem = storageFacade.setItem;
      proto.removeItem = storageFacade.removeItem;
      proto.clear = storageFacade.clear;
      proto.key = storageFacade.key;
      Object.defineProperty(proto, 'length', {
        configurable: true,
        get: function () {
          return storageFacade.length;
        }
      });
    } catch (error) {
      logError('could not patch Storage.prototype', error);
    }
  }

  /* ------------------------------------------------------------------ */
  /* Public async helpers                                               */
  /* ------------------------------------------------------------------ */

  function saveSettings(key, value) {
    storageFacade.setItem(key, value);
    return persistSettings();
  }

  function loadSettings(key) {
    return Promise.resolve(storageFacade.getItem(key));
  }

  function getSettingsPath() {
    return invoke('get_settings_path');
  }

  /* ------------------------------------------------------------------ */
  /* External links                                                     */
  /* ------------------------------------------------------------------ */

  // Opens an http(s) URL in the OS default browser. The opener plugin's
  // global API is used when available; the Rust `open_external` command is a
  // fallback for builds where plugin globals are not injected.
  function openExternalUrl(href) {
    var tauri = window.__TAURI__ || TAURI;
    var opener = tauri && tauri.opener;

    if (opener && typeof opener.openUrl === 'function') {
      return Promise.resolve(opener.openUrl(href)).catch(function (error) {
        logError('failed to open external link', error);
      });
    }

    if (tauri && tauri.core && typeof tauri.core.invoke === 'function') {
      return tauri.core.invoke('open_external', { url: href }).catch(function (error) {
        logError('failed to open external link', error);
      });
    }

    // Development fallback when the page is opened in a normal browser.
    window.open(href, '_blank', 'noopener,noreferrer');
    return Promise.resolve();
  }

  function installExternalLinkHandler() {
    document.addEventListener(
      'click',
      function (event) {
        var target = event.target;
        if (!target || typeof target.closest !== 'function') {
          return;
        }
        var anchor = target.closest('a[href]');
        var href = anchor && (anchor.getAttribute('href') || '');
        if (!/^https?:\/\//i.test(href)) {
          return;
        }

        // Keep the WebView on the current page. Tauri/WebView2/WebKit would
        // otherwise create an in-app window or replace the application.
        event.preventDefault();
        openExternalUrl(href);
      },
      true
    );
  }

  /* ------------------------------------------------------------------ */
  /* .gustay file handling                                              */
  /* ------------------------------------------------------------------ */

  function importThemePayload(payload) {
    if (!payload || typeof payload.content !== 'string' || !payload.content) {
      return;
    }

    if (payload.id) {
      if (seenThemeIds[payload.id]) {
        return;
      }
      seenThemeIds[payload.id] = true;
    }

    var api = window.GUStayNative;
    if (!api || typeof api.importTheme !== 'function') {
      logError('theme import is not ready yet', payload.name);
      return;
    }

    try {
      var name = payload.name || 'theme.gustay';
      var file = new File([payload.content], name, {
        type: 'application/x-gustay',
        lastModified: Date.now()
      });
      api.importTheme(file);
    } catch (error) {
      logError('failed to hand the theme to the app', error);
    }
  }

  function listenForFiles() {
    if (!hasTauri || !TAURI.event || typeof TAURI.event.listen !== 'function') {
      return Promise.resolve();
    }

    return TAURI.event
      .listen('file-open', function (event) {
        importThemePayload(event && event.payload);
      })
      .catch(function (error) {
        logError('failed to listen for file-open events', error);
      });
  }

  function importPendingThemes() {
    return invoke('take_pending_theme')
      .then(function (pending) {
        if (Array.isArray(pending)) {
          pending.forEach(importThemePayload);
        } else if (pending) {
          importThemePayload(pending);
        }
      })
      .catch(function (error) {
        logError('failed to read the pending theme', error);
      });
  }

  /* ------------------------------------------------------------------ */
  /* Startup                                                            */
  /* ------------------------------------------------------------------ */

  function hydrateSettings() {
    if (!hasTauri) {
      return Promise.resolve();
    }

    return invoke('load_settings')
      .then(function (raw) {
        if (!raw) {
          return;
        }
        var parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
          throw new Error('settings file does not contain a JSON object');
        }
        Object.keys(parsed).forEach(function (key) {
          cache[key] = String(parsed[key]);
        });
      })
      .catch(function (error) {
        logError('failed to load settings, starting with defaults', error);
      });
  }

  function start() {
    return hydrateSettings()
      .then(function () {
        installStorageFacade();
        installExternalLinkHandler();

        window.saveSettings = saveSettings;
        window.loadSettings = loadSettings;
        window.getSettingsPath = getSettingsPath;

        window.GUStayNative = window.GUStayNative || {};
        window.GUStayNative.saveSettings = saveSettings;
        window.GUStayNative.loadSettings = loadSettings;
        window.GUStayNative.getSettingsPath = getSettingsPath;
        window.GUStayNative.flushSettings = persistSettings;
        window.GUStayNative.storage = storageFacade;

        // The application IIFE defines window.__gustayBoot in the shared
        // HTML transformation. Keeping it wrapped lets us finish hydration
        // before any synchronous localStorage read happens.
        if (typeof window.__gustayBoot !== 'function') {
          throw new Error('GUStay application bootstrap is missing');
        }
        window.__gustayBoot();

        document.documentElement.classList.add('gustay-ready');

        return listenForFiles().then(importPendingThemes);
      })
      .catch(function (error) {
        logError('startup failed', error);
        // Never leave the user with an invisible window.
        document.documentElement.classList.add('gustay-ready');
      });
  }

  // Best-effort flush when the window is closing. The 300 ms debounce means
  // at most a few tens of milliseconds of edits can be lost on a hard kill.
  window.addEventListener('pagehide', function () {
    if (persistTimer) {
      window.clearTimeout(persistTimer);
      persistTimer = 0;
    }
    persistSettings();
  });

  start();
})();
