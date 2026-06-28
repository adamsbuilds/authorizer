## JSON mapping

Edit `resources/addons_map.json` to define supported addons and auth actions.

Action types:
- `builtin`: executes with `xbmc.executebuiltin(...)`
- `plugin`: executes with `RunPlugin(plugin://...)`

Example service action:

```json
{
  "type": "plugin",
  "value": "plugin://plugin.video.someaddon/?action=auth_trakt",
  "label": "Direct Trakt auth"
}
