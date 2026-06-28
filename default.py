# -*- coding: utf-8 -*-
import json
import os
import sys
import urllib.parse

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
HANDLE = int(sys.argv[1]) if len(sys.argv) > 1 else -1

DEFAULT_MAP = {"supported_addons": []}

SERVICE_TITLES = {
    "trakt": "Trakt",
    "realdebrid": "Real-Debrid",
    "premiumize": "Premiumize",
    "alldebrid": "All-Debrid",
    "torbox": "Torbox"
}

def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{ADDON_ID}] {msg}", level)

def load_addons_map():
    path = os.path.join(ADDON_PATH, "resources", "addons_map.json")
    if not xbmcvfs.exists(path):
        log(f"addons_map.json not found: {path}", xbmc.LOGWARNING)
        return DEFAULT_MAP

    f = xbmcvfs.File(path)
    try:
        raw = f.read()
    finally:
        f.close()

    try:
        data = json.loads(raw) if raw else {}
    except Exception as e:
        log(f"Failed to parse addons_map.json: {e}", xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Authorizer", "Invalid addons_map.json", xbmcgui.NOTIFICATION_ERROR, 4000)
        return DEFAULT_MAP

    if not isinstance(data, dict):
        return DEFAULT_MAP
    if not isinstance(data.get("supported_addons"), list):
        return DEFAULT_MAP

    return data

DATA = load_addons_map()
SUPPORTED_ADDONS = DATA.get("supported_addons", [])

def addon_installed(addon_id):
    try:
        xbmcaddon.Addon(addon_id)
        return True
    except Exception:
        return False

def detected_addons():
    return [a for a in SUPPORTED_ADDONS if addon_installed(a.get("id", ""))]

def build_url(params):
    return f"{sys.argv[0]}?{urllib.parse.urlencode(params)}"

def add_item(label, params, is_folder=False):
    li = xbmcgui.ListItem(label=label)
    xbmcplugin.addDirectoryItem(HANDLE, build_url(params), li, isFolder=is_folder)

def run_action(action):
    typ = action.get("type")
    val = action.get("value")
    if not typ or not val:
        return False

    try:
        if typ == "builtin":
            xbmc.executebuiltin(val)
            return True
        if typ == "plugin":
            xbmc.executebuiltin(f"RunPlugin({val})")
            return True
    except Exception as e:
        log(f"Action failed: {action} error={e}", xbmc.LOGERROR)

    return False

def service_display_name(service_key):
    if service_key in SERVICE_TITLES:
        return SERVICE_TITLES[service_key]
    # fallback: "myservice_name" -> "Myservice Name"
    return service_key.replace("_", " ").strip().title()

def authorize(addon_id, service):
    matches = [a for a in SUPPORTED_ADDONS if a.get("id") == addon_id]
    if not matches:
        xbmcgui.Dialog().notification("Authorizer", "Addon not found in mapping.", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    target = matches[0]
    actions = target.get("services", {}).get(service, [])
    if not actions:
        xbmcgui.Dialog().notification("Authorizer", f"No {service_display_name(service)} actions configured.", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    # If multiple actions, allow explicit choice first.
    if len(actions) > 1:
        labels = [a.get("label") or f"{a.get('type')} -> {a.get('value')}" for a in actions]
        idx = xbmcgui.Dialog().select(
            f"{target.get('name', addon_id)} - {service_display_name(service)}",
            labels
        )
        if idx < 0:
            return
        if run_action(actions[idx]):
            return

    # Fallback chain (or single-action attempt)
    for action in actions:
        if run_action(action):
            return

    xbmcgui.Dialog().notification(
        "Authorizer",
        f"Unable to launch {service_display_name(service)} authorization.",
        xbmcgui.NOTIFICATION_ERROR,
        4000
    )

def addon_menu(addon_id):
    installed = [a for a in detected_addons() if a.get("id") == addon_id]
    if not installed:
        xbmcgui.Dialog().notification("Authorizer", "Addon not installed.", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    target = installed[0]
    services = target.get("services", {})
    if not isinstance(services, dict) or not services:
        xbmcgui.Dialog().notification("Authorizer", "No services configured for this addon.", xbmcgui.NOTIFICATION_ERROR, 3000)
        return

    # Stable ordering: known services first, then others alphabetically.
    known = [k for k in SERVICE_TITLES.keys() if k in services]
    extra = sorted([k for k in services.keys() if k not in SERVICE_TITLES])
    ordered_services = known + extra

    for service_key in ordered_services:
        actions = services.get(service_key, [])
        if not isinstance(actions, list) or not actions:
            continue
        label = f"{target.get('name', addon_id)} - {service_display_name(service_key)}"
        add_item(
            label,
            {"action": "authorize", "addon_id": addon_id, "service": service_key},
            is_folder=False
        )

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def root_menu():
    found = detected_addons()
    if not found:
        xbmcgui.Dialog().ok(
            "Authorizer",
            "No supported addons detected.\n\nUpdate resources/addons_map.json as needed."
        )
        xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)
        return

    for addon in found:
        add_item(
            addon.get("name", addon.get("id", "Unknown")),
            {"action": "addon_menu", "addon_id": addon.get("id", "")},
            is_folder=True
        )

    xbmcplugin.endOfDirectory(HANDLE, cacheToDisc=False)

def route():
    params = dict(urllib.parse.parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 and sys.argv[2] else {}
    action = params.get("action")

    if action == "authorize":
        authorize(params.get("addon_id", ""), params.get("service", ""))
        return

    if action == "addon_menu":
        addon_menu(params.get("addon_id", ""))
        return

    root_menu()

if __name__ == "__main__":
    route()
