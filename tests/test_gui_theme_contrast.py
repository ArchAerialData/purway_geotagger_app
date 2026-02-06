from __future__ import annotations

from purway_geotagger.gui.style_sheet import get_theme_colors


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _linearize(channel: int) -> float:
    c = channel / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return (0.2126 * _linearize(r)) + (0.7152 * _linearize(g)) + (0.0722 * _linearize(b))


def _contrast_ratio(foreground: str, background: str) -> float:
    l_fg = _luminance(foreground)
    l_bg = _luminance(background)
    lighter = max(l_fg, l_bg)
    darker = min(l_fg, l_bg)
    return (lighter + 0.05) / (darker + 0.05)


def _assert_contrast(theme: str, fg_key: str, bg_key: str, minimum: float) -> None:
    colors = get_theme_colors(theme)
    ratio = _contrast_ratio(colors[fg_key], colors[bg_key])
    assert ratio >= minimum, (
        f"{theme}: '{fg_key}' on '{bg_key}' has {ratio:.2f}:1 contrast "
        f"(required >= {minimum:.2f}:1)"
    )


def test_theme_text_contrast() -> None:
    for theme in ("light", "dark"):
        _assert_contrast(theme, "text_primary", "window_bg", 4.5)
        _assert_contrast(theme, "text_secondary", "window_bg", 4.5)


def test_theme_button_contrast() -> None:
    for theme in ("light", "dark"):
        _assert_contrast(theme, "button_primary_fg", "primary", 4.5)
        _assert_contrast(theme, "button_primary_fg", "primary_hover", 4.5)
        _assert_contrast(theme, "button_primary_fg", "primary_pressed", 4.5)
        _assert_contrast(theme, "button_run_fg", "success", 4.5)
        _assert_contrast(theme, "button_run_fg", "success_hover", 4.5)
        _assert_contrast(theme, "button_run_fg", "success_pressed", 4.5)


def test_theme_status_text_contrast() -> None:
    for theme in ("light", "dark"):
        _assert_contrast(theme, "status_info", "window_bg", 4.5)
        _assert_contrast(theme, "status_success_text", "window_bg", 4.5)
        _assert_contrast(theme, "status_error_text", "window_bg", 4.5)


def test_theme_section_separation() -> None:
    for theme in ("light", "dark"):
        _assert_contrast(theme, "card_border", "surface_bg", 1.4)
        _assert_contrast(theme, "input_border", "input_bg", 1.2)
