"""Static accessibility checks: labels, keyboard semantics, and contrast."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "src/web/templates/index.html").read_text()
CSS = (ROOT / "src/web/static/css/styles.css").read_text()
JS = (ROOT / "src/web/static/js/app.js").read_text()


def _channel(value: float) -> float:
    value = value / 255
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    red = int(hex_color[1:3], 16)
    green = int(hex_color[3:5], 16)
    blue = int(hex_color[5:7], 16)
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def _contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)))
    return (darker + 0.05) / (lighter + 0.05)


def _css_color(name: str) -> str:
    match = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{6}})", CSS)
    assert match, name
    return match.group(1).lower()


def test_page_has_language_skip_link_and_focus() -> None:
    assert "<html lang=\"en\">" in HTML
    assert 'class="skip-link"' in HTML
    assert ":focus-visible" in CSS
    assert "textContent" in JS
    assert "innerHTML" not in JS


def test_every_control_has_a_label() -> None:
    labels = set(re.findall(r"<label[^>]*\sfor=\"([^\"]+)\"", HTML))
    controls = re.findall(r"<(?:input|select|textarea)\b[^>]*\sid=\"([^\"]+)\"", HTML)
    assert controls
    missing = [control for control in controls if control not in labels]
    assert missing == []


def test_keyboard_patterns_are_in_the_script() -> None:
    assert 'role: "radio"' in JS or 'role", "radio"' in JS or 'role: "radio"' in JS
    assert "ArrowRight" in JS
    assert "ArrowLeft" in JS
    assert 'role="tablist"' in HTML
    assert "aria-live" in HTML


def test_text_contrast_clears_seven_to_one() -> None:
    paper = _css_color("paper")
    surface = _css_color("surface")
    ink = _css_color("ink")
    muted = _css_color("muted")
    pairs = [
        (ink, paper),
        (muted, paper),
        (ink, surface),
        (_css_color("band-text"), ink),
        (_css_color("alert-ink"), _css_color("alert-bg")),
        (_css_color("warn-ink"), _css_color("warn-bg")),
        (_css_color("ok-ink"), _css_color("ok-bg")),
        (_css_color("band-text"), _css_color("focus")),
    ]
    for foreground, background in pairs:
        assert _contrast(foreground, background) >= 7
