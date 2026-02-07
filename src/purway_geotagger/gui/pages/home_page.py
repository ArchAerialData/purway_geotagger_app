from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Signal, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QRadialGradient
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from purway_geotagger.core.modes import RunMode
from purway_geotagger.exif.exiftool_writer import is_exiftool_available


class _AnimatedModeCardHeader(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setProperty("cssClass", "mode_card_header")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(52)
        self._phase = 0.0
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(40)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start()

    def _tick(self) -> None:
        # 40ms * 250 ticks ~= 10s cycle to match the web reference animation speed.
        self._phase += 0.004
        if self._phase >= 1.0:
            self._phase -= 1.0
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._anim_timer.isActive():
            self._anim_timer.start()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._anim_timer.stop()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        rect = self.rect().adjusted(0, 0, -1, -1)
        if rect.isEmpty():
            return

        app = QApplication.instance()
        dark_mode = bool(app.property("darkMode")) if app else False

        # Literal palette port from replit-local card-header-theme.css.
        # Keep the same hue family in both modes; only tweak alpha/border for contrast.
        base = QColor(15, 15, 15, 232 if dark_mode else 214)           # #0f0f0f
        glow = QColor(255, 255, 255, 13)                               # #ffffff0d
        g1 = QColor(29, 27, 167, 188 if dark_mode else 174)            # #1d1ba7
        g2 = QColor(35, 95, 215, 176 if dark_mode else 164)            # #235fd7
        cool_gray_1 = QColor(255, 255, 255, 10 if dark_mode else 24)
        cool_gray_2 = QColor(42, 42, 42, 128 if dark_mode else 96)     # #2a2a2a
        border = QColor(94, 111, 136, 126 if dark_mode else 138)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        radius = 12.0
        left = float(rect.left())
        top = float(rect.top())
        right = float(rect.right())
        bottom = float(rect.bottom())

        # Top-only rounded strip so the gradient reads as a professional card header band.
        path = QPainterPath()
        path.moveTo(left, bottom)
        path.lineTo(left, top + radius)
        path.quadTo(left, top, left + radius, top)
        path.lineTo(right - radius, top)
        path.quadTo(right, top, right, top + radius)
        path.lineTo(right, bottom)
        path.closeSubpath()
        painter.fillPath(path, base)

        # Mirror the web keyframe behavior:
        # start -> midpoint (at 50%) -> start, smoothed with cosine easing.
        ping_pong = 0.5 - 0.5 * math.cos(2.0 * math.pi * self._phase)

        x1_pct = 87.96875 + (15.0 - 87.96875) * ping_pong
        y1_pct = 91.1328125 + (15.0 - 91.1328125) * ping_pong
        x2_pct = 13.3984375 + (61.2109375 - 13.3984375) * ping_pong
        y2_pct = 82.734375 + (13.75 - 82.734375) * ping_pong

        w = max(1.0, float(rect.width()))
        h = max(1.0, float(rect.height()))
        c1x = float(rect.left()) + (x1_pct / 100.0) * w
        c1y = float(rect.top()) + (y1_pct / 100.0) * h
        c2x = float(rect.left()) + (x2_pct / 100.0) * w
        c2y = float(rect.top()) + (y2_pct / 100.0) * h

        glow_grad = QRadialGradient(float(rect.left()) + 0.04 * w, float(rect.top()) + 0.03 * h, max(w, h) * 1.1)
        glow_grad.setColorAt(0.0, glow)
        glow_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setCompositionMode(QPainter.CompositionMode_Screen)
        painter.fillPath(path, glow_grad)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        radial_1 = QRadialGradient(c1x, c1y, max(w, h) * 1.2)
        radial_1.setColorAt(0.0, g1)
        radial_1.setColorAt(1.0, QColor(g1.red(), g1.green(), g1.blue(), 0))
        painter.fillPath(path, radial_1)

        radial_2 = QRadialGradient(c2x, c2y, max(w, h) * 1.2)
        radial_2.setColorAt(0.0, g2)
        radial_2.setColorAt(1.0, QColor(g2.red(), g2.green(), g2.blue(), 0))
        painter.fillPath(path, radial_2)

        gray_mix = QLinearGradient(float(rect.left()), float(rect.top()), float(rect.right()), float(rect.bottom()))
        gray_mix.setColorAt(0.0, cool_gray_1)
        gray_mix.setColorAt(0.55, QColor(cool_gray_1.red(), cool_gray_1.green(), cool_gray_1.blue(), int(cool_gray_1.alpha() * 0.6)))
        gray_mix.setColorAt(1.0, cool_gray_2)
        painter.fillPath(path, gray_mix)

        painter.setPen(border)
        painter.drawPath(path)


class _ModeCard(QFrame):
    activated = Signal()

    def __init__(
        self,
        *,
        title: str,
        badge_text: str,
        bullets: list[str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("cssClass", "mode_card")
        self.setProperty("hovered", "false")
        self.setProperty("lastUsed", "false")
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(210)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8.0)
        shadow.setOffset(0.0, 2.0)
        shadow.setColor(QColor(0, 0, 0, 64))
        self.setGraphicsEffect(shadow)
        self._shadow_effect = shadow
        self._shadow_anim = QPropertyAnimation(self._shadow_effect, b"blurRadius", self)
        self._shadow_anim.setDuration(140)
        self._shadow_anim.setEasingCurve(QEasingCurve.InOutQuad)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._header_frame = _AnimatedModeCardHeader(self)
        header = QHBoxLayout(self._header_frame)
        header.setContentsMargins(16, 10, 16, 10)
        header.setSpacing(8)

        badge = QLabel(badge_text)
        badge.setAlignment(Qt.AlignCenter)
        badge.setProperty("cssClass", "mode_card_icon")
        header.addWidget(badge)

        title_label = QLabel(title)
        title_label.setProperty("cssClass", "mode_card_title")
        title_label.setWordWrap(True)
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        header.addWidget(title_label, 1)

        chevron = QLabel(">")
        chevron.setProperty("cssClass", "mode_card_chevron")
        chevron.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(chevron)
        layout.addWidget(self._header_frame)

        body = QWidget(self)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 12, 16, 14)
        body_layout.setSpacing(10)

        divider = QFrame()
        divider.setProperty("cssClass", "mode_card_divider")
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Plain)
        body_layout.addWidget(divider)

        desc = QLabel(_bullets_html(bullets))
        desc.setWordWrap(True)
        desc.setTextFormat(Qt.RichText)
        desc.setProperty("cssClass", "mode_card_bullets")
        body_layout.addWidget(desc)
        body_layout.addStretch(1)

        hint = QLabel("Click anywhere to open")
        hint.setProperty("cssClass", "mode_card_hint")
        body_layout.addWidget(hint)
        layout.addWidget(body, 1)

        for widget in (self._header_frame, body, badge, title_label, chevron, desc, hint, divider):
            widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def set_last_used(self, is_last_used: bool) -> None:
        target = "true" if is_last_used else "false"
        if self.property("lastUsed") == target:
            return
        self.setProperty("lastUsed", target)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._set_hovered(True)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._set_hovered(False)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and self.rect().contains(event.pos()):
            self.activated.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.activated.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def _set_hovered(self, hovered: bool) -> None:
        target = "true" if hovered else "false"
        if self.property("hovered") != target:
            self.setProperty("hovered", target)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        self._shadow_anim.stop()
        self._shadow_anim.setStartValue(self._shadow_effect.blurRadius())
        self._shadow_anim.setEndValue(16.0 if hovered else 8.0)
        self._shadow_anim.start()


class HomePage(QWidget):
    mode_selected = Signal(RunMode)
    wind_data_selected = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._mode_cards: dict[RunMode, _ModeCard] = {}
        self._card_order: list[_ModeCard] = []
        self._current_card_columns = 3
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(40, 40, 40, 40)

        # Header Container (Horizontal split)
        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(40)

        # Left: Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(8)
        
        title = QLabel("Select a report type")
        title.setProperty("cssClass", "h1")
        
        subtitle = QLabel("Choose the workflow that matches the reports you need to deliver.")
        subtitle.setProperty("cssClass", "subtitle")
        subtitle.setWordWrap(True)

        self._last_mode_label = QLabel("")
        self._last_mode_label.setProperty("cssClass", "status_info")
        self._last_mode_label.setWordWrap(True)

        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        text_layout.addWidget(self._last_mode_label)
        
        # Right: System Status Card
        status_card = QFrame()
        status_card.setProperty("cssClass", "card")
        status_card.setFixedWidth(280)
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(16, 16, 16, 16)
        status_layout.setSpacing(10)
        
        st_title = QLabel("System Status")
        st_title.setProperty("cssClass", "label_strong")
        
        # ExifTool Check
        et_row = QWidget()
        et_layout = QHBoxLayout(et_row)
        et_layout.setContentsMargins(0, 0, 0, 0)
        et_layout.setSpacing(8)
        
        has_et = is_exiftool_available()
        et_icon = QLabel()
        if has_et:
            et_icon.setText("✓")
            et_icon.setProperty("cssClass", "status_success")
        else:
            et_icon.setText("✕")
            et_icon.setProperty("cssClass", "status_error")

        et_lbl = QLabel("ExifTool Ready")
        et_lbl.setProperty("cssClass", "status_success")
        if not has_et:
            et_lbl.setText("ExifTool Missing")
            et_lbl.setProperty("cssClass", "status_error")

        et_layout.addWidget(et_icon)
        et_layout.addWidget(et_lbl)
        et_layout.addStretch()
        
        status_layout.addWidget(st_title)
        status_layout.addWidget(et_row)
        status_layout.addStretch()

        header_layout.addLayout(text_layout, 1) # Text takes available space
        header_layout.addWidget(status_card)    # Card is fixed width

        layout.addWidget(header_container)

        cards_wrap = QWidget()
        cards_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cards_layout = QGridLayout(cards_wrap)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)
        self._cards_wrap = cards_wrap
        self._cards_layout = cards_layout

        card_specs = (
            (
                "Methane Reports Only",
                "M",
                [
                    "Clean methane CSVs using a PPM threshold.",
                    "Inject EXIF metadata in-place.",
                    "Optional KMZ output.",
                ],
                RunMode.METHANE,
            ),
            (
                "Encroachment Reports Only",
                "E",
                [
                    "Copy JPGs to a single output folder.",
                    "Renaming and chronological indexing.",
                    "Use templates or manual client codes.",
                ],
                RunMode.ENCROACHMENT,
            ),
            (
                "Methane + Encroachments",
                "C",
                [
                    "Single guided flow with confirmation.",
                    "Methane stays in-place, encroachments copy out.",
                    "Separate settings for each output type.",
                ],
                RunMode.COMBINED,
            ),
            (
                "Wind Data DOCX",
                "W",
                [
                    "Generate Wind Data DOCX files from the production template.",
                    "Use manual Start/End inputs or autofill weather values.",
                    "Preview final output strings before saving.",
                ],
                None,
            ),
        )

        for title_text, badge_text, bullets, mode in card_specs:
            card = self._make_mode_card(
                title=title_text,
                badge_text=badge_text,
                bullets=bullets,
            )
            if mode is None:
                card.activated.connect(self.wind_data_selected.emit)
            else:
                card.activated.connect(lambda mode=mode: self.mode_selected.emit(mode))
                self._mode_cards[mode] = card
            self._card_order.append(card)

        layout.addWidget(cards_wrap, 1)
        QTimer.singleShot(0, self._relayout_mode_cards)

    def set_last_mode(self, mode: RunMode | None) -> None:
        if mode is None:
            self._last_mode_label.setText("")
            for card in self._mode_cards.values():
                card.set_last_used(False)
            return
        self._last_mode_label.setText(f"Last used: {_mode_label(mode)}")
        for run_mode, card in self._mode_cards.items():
            card.set_last_used(run_mode == mode)

    def _make_mode_card(
        self,
        *,
        title: str,
        badge_text: str,
        bullets: list[str],
    ) -> _ModeCard:
        card = _ModeCard(
            title=title,
            badge_text=badge_text,
            bullets=bullets,
            parent=self,
        )
        return card

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout_mode_cards()

    def _relayout_mode_cards(self) -> None:
        if not hasattr(self, "_cards_layout"):
            return
        available_width = self._cards_wrap.width()
        if available_width < 200:
            # Offscreen/layout-startup fallback where child width is not yet resolved.
            available_width = max(320, self.width() - 80)
        else:
            available_width = max(320, available_width)
        spacing = self._cards_layout.horizontalSpacing()
        min_card_width = 320
        max_columns = 2 if len(self._card_order) == 4 else 3
        columns = max(
            1,
            min(max_columns, int((available_width + spacing) / (min_card_width + spacing))),
        )
        if columns != self._current_card_columns:
            self._current_card_columns = columns

        while self._cards_layout.count():
            self._cards_layout.takeAt(0)

        row_count = (len(self._card_order) + columns - 1) // columns
        for idx, card in enumerate(self._card_order):
            row = idx // columns
            col = idx % columns
            self._cards_layout.addWidget(card, row, col)

        max_stretch_columns = max(3, len(self._card_order))
        max_stretch_rows = max(3, len(self._card_order))
        for col in range(max_stretch_columns):
            self._cards_layout.setColumnStretch(col, 1 if col < columns else 0)
        for row in range(max_stretch_rows):
            self._cards_layout.setRowStretch(row, 1 if row < row_count else 0)


def _bullets_html(items: list[str]) -> str:
    if not items:
        return ""
    rows = "".join(f"<li style='margin-bottom: 6px; line-height: 1.3;'>{item}</li>" for item in items)
    return f"<ul style='margin: 0; padding-left: 18px;'>{rows}</ul>"


def _mode_label(mode: RunMode) -> str:
    return {
        RunMode.METHANE: "Methane Reports Only",
        RunMode.ENCROACHMENT: "Encroachment Reports Only",
        RunMode.COMBINED: "Methane + Encroachments",
    }.get(mode, mode.value)
