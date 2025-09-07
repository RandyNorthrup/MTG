def update_phase_ui(main_win):
    """
    Prefix active player's name to progress bar / phase label.
    """
    try:
        ap = getattr(main_win.game, 'active_player', 0)
        pname = main_win.game.players[ap].name if main_win.game.players else "?"
    except Exception:
        pname = "?"
    bar = getattr(main_win.play_area, 'phase_progress_bar', None)
    if bar is not None:
        try:
            base = getattr(bar, '_orig_format', None)
            if base is None:
                base = bar.format() if hasattr(bar, 'format') else "%v/%m"
                if not base: base = "%v/%m"
                bar._orig_format = base
            bar.setFormat(f"{pname} - {base}")
        except Exception:
            pass
    lbl = getattr(main_win.play_area, 'phase_label', None)
    if lbl is not None:
        try:
            base_txt = getattr(lbl, '_orig_text', None)
            if base_txt is None:
                base_txt = lbl.text(); lbl._orig_text = base_txt
            lbl.setText(f"{pname} - {base_txt}")
        except Exception:
            pass
