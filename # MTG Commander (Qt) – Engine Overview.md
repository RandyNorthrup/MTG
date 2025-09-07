# MTG Commander (Qt) – Engine Overview

## High‑Level Phases
Engine now exposes only 5 high‑level phases:
1. Beginning (auto Untap → Upkeep → Draw; no interaction)
2. PreCombatMain
3. Combat (waits for attackers; auto Blockers → Damage → EndCombat after declaration)
4. PostCombatMain
5. End (End Step → Cleanup internally)

Phase automation is centralized in `engine/phase_hooks.py`:
- `register_phase_controller(controller)` patches `advance_phase`
- `unlock_phases()` is invoked after opening hands & mulligans finish
- `install_phase_log_adapter(controller)` maps raw engine phases to high‑level and dedupes logging

## Logging
Only logs AFTER:
- Match entered (`controller.in_game`)
- First player decided
- Phases unlocked
No pre‑game UNTAP spam.

## UI
No top progress bar. A single banner over the hand uses:
`play_area.update_phase_banner(phase_label, active_player_name)`

## Combat
- If no potential attackers: combat auto‑skips to PostCombatMain
- Player may manually skip while waiting for attackers
- After attackers: remaining combat steps auto‑advance with short delays

## Codebase Cleanup
- Removed legacy aliases (`install_phase_control`, old dedupers)
- Consolidated phase logging & progression
- Eliminated stray / duplicated corrupted phase code
- Purged unused imports (e.g. PlayArea in main window)
- Added robust `.gitignore` (bytecode, envs, caches, game id log)

## Extending
Call sequence when creating / rebuilding game:
```python
register_phase_controller(controller)
install_phase_log_adapter(controller)
# later after mulligans:
controller.unlock_phases()
```

## Caches
Runtime caches & generated IDs ignored:
- `data/game_ids.txt`
- `data/cache/`
- `image_cache/`

Use `api.shutdown()` (invoked by MainWindow.closeEvent) for clean teardown.

## Contributing
Submit PRs focusing on:
- Deterministic phase transitions
- Minimal UI coupling (only banner update dependency)
- Avoid writing to read‑only game state attributes (e.g. game.phase if property)

