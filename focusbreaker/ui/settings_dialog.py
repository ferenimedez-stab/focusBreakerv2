from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QFrame, QLineEdit, QScrollArea, QWidget, QStackedWidget,
    QFileDialog, QMessageBox, QCheckBox, QListWidget, QListWidgetItem,
    QGridLayout, QSizePolicy, QLayout, QBoxLayout, QSpacerItem, QDialog,
    QProgressBar
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QTime
from PySide6.QtGui import QColor, QPixmap, QIcon, QKeySequence, QPainter, QBrush

from focusbreaker.config import UIConfig, AppPaths, MediaConfig, Palette
from focusbreaker.data.db import DBManager
from focusbreaker.data.models import Settings
from focusbreaker.system.media_manager import MediaManager
from focusbreaker.ui.components.dialogs import ThemedConfirmDialog, ThemedMessageDialog

def _section(title: str) -> QWidget:
    w = QWidget()
    l = QVBoxLayout(w)
    l.setContentsMargins(0, 20, 0, 8) # Add top margin for clear separation
    l.setSpacing(8)
    
    lbl = QLabel(title.upper())
    lbl.setObjectName("section_title")
    lbl.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {Palette.BRAND_PRIMARY}; letter-spacing: 2px;")
    l.addWidget(lbl)
    
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background-color: {Palette.SURFACE_DARK}; border: none;")
    l.addWidget(line)
    
    return w

class SettingsRow(QWidget):
    """A consistent setting row with label, widget, and optional subtitle."""
    def __init__(self, label: str, widget, parent=None, subtitle=""):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(4)
        
        top_l = QHBoxLayout()
        self.lbl = QLabel(label)
        self.lbl.setStyleSheet(f"color: {Palette.TEXT_PRIMARY}; font-size: 14px; font-weight: 700;")
        top_l.addWidget(self.lbl)
        top_l.addStretch()
        
        self.widget = widget
        top_l.addWidget(self.widget)
        self.main_layout.addLayout(top_l)
        
        if subtitle:
            self.sub = QLabel(subtitle)
            self.sub.setStyleSheet(f"color: {Palette.TEXT_SECONDARY}; font-size: 12px; font-weight: 500; border: none; background: transparent;")
            self.sub.setWordWrap(True)
            self.main_layout.addWidget(self.sub)
            
        self.main_layout.addSpacing(16) # Increased spacing between rows

def _spinbox(min_val: int, max_val: int, val: int, suffix: str = " MIN") -> QSpinBox:
    sb = QSpinBox()
    sb.setRange(min_val, max_val)
    sb.setValue(val)
    sb.setSuffix(suffix.upper())
    sb.setFixedWidth(130)
    sb.setFixedHeight(40)
    return sb

class SlidingToggle(QWidget):
    """A professional sliding toggle switch (HCI standard)."""
    toggled = Signal(bool)

    def __init__(self, parent=None, active_color=Palette.BRAND_PRIMARY, bg_color=Palette.TEXT_MUTED):
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self._checked = True
        self._active_color = active_color
        self._bg_color = bg_color
        self._knob_pos = 22 # Start at 'on' position
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self): return self._checked
    def setChecked(self, checked):
        self._checked = checked
        self._knob_pos = 22 if checked else 2
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._knob_pos = 22 if self._checked else 2
            self.toggled.emit(self._checked)
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        color = self._active_color if self._checked else self._bg_color
        p.setBrush(QBrush(QColor(color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        
        p.setBrush(QBrush(QColor("white")))
        p.drawEllipse(self._knob_pos, 2, 20, 20)

class KeyCaptureModal(QDialog):
    """Modal for capturing a keyboard shortcut combination."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        self.current_keys = set()
        self.final_combo = ""
        
        self._setup_ui()
        
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        # Backdrop container with specific ID to prevent inheritance
        self.bg = QFrame()
        self.bg.setObjectName("key_capture_shell")
        self.bg.setStyleSheet(f"""
            QFrame#key_capture_shell {{ 
                background-color: {Palette.SURFACE_WHITE}; 
                border-radius: 20px; 
                border: 2px solid {Palette.BRAND_PRIMARY}; 
            }}
            QLabel {{ border: none; background: transparent; }}
        """)
        root.addWidget(self.bg)
        
        l = QVBoxLayout(self.bg)
        l.setContentsMargins(30, 30, 30, 30)
        l.setSpacing(20)
        
        title = QLabel("SET ESCAPE HATCH")
        title.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {Palette.TEXT_MUTED}; letter-spacing: 1.5px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(title)
        
        self.instruction = QLabel("Press your key combination...")
        self.instruction.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Palette.TEXT_PRIMARY};")
        self.instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(self.instruction)
        
        self.combo_display = QLabel("---")
        self.combo_display.setStyleSheet(f"""
            background: {Palette.SURFACE_DARK}; 
            color: {Palette.BRAND_PRIMARY}; 
            font-family: 'JetBrains Mono'; 
            font-size: 20px; 
            font-weight: 800; 
            padding: 15px; 
            border-radius: 10px;
            border: none;
        """)
        self.combo_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(self.combo_display)
        
        self.hint = QLabel("Hold for 3 seconds to confirm")
        self.hint.setStyleSheet(f"font-size: 11px; color: {Palette.TEXT_SECONDARY};")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(self.hint)
        
        self.progress = QProgressBar()
        self.progress.setFixedHeight(6)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 3000)
        self.progress.setValue(0)
        self.progress.setStyleSheet(f"""
            QProgressBar {{ background: {Palette.SURFACE_DARK}; border-radius: 3px; border: none; }}
            QProgressBar::chunk {{ background: {Palette.BRAND_PRIMARY}; border-radius: 3px; }}
        """)
        l.addWidget(self.progress)
        
        self.hold_timer = QTimer(self)
        self.hold_timer.setInterval(50)
        self.hold_timer.timeout.connect(self._on_hold_tick)
        self.hold_start_time = 0

    def keyPressEvent(self, event):
        if event.isAutoRepeat(): return
        
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.reject()
            return
            
        self.current_keys.add(key)
        self._update_display()
        
        if not self.hold_timer.isActive():
            self.hold_start_time = QTime.currentTime().msecsSinceStartOfDay()
            self.hold_timer.start()
            
    def keyReleaseEvent(self, event):
        if event.isAutoRepeat(): return
        self.current_keys.discard(event.key())
        self._update_display()
        
        if not self.current_keys:
            self.hold_timer.stop()
            self.progress.setValue(0)

    def _update_display(self):
        names = []
        # Sort to keep standard order: Modifiers then Keys
        mods = []
        others = []
        for k in self.current_keys:
            name = self._key_to_name(k)
            if name in ["CTRL", "ALT", "SHIFT", "META"]:
                mods.append(name)
            else:
                others.append(name)
        
        names = sorted(mods) + sorted(others)
        self.final_combo = "+".join(names)
        self.combo_display.setText(self.final_combo if self.final_combo else "---")

    def _on_hold_tick(self):
        if not self.current_keys: return
        
        elapsed = QTime.currentTime().msecsSinceStartOfDay() - self.hold_start_time
        self.progress.setValue(elapsed)
        
        if elapsed >= 3000:
            self.hold_timer.stop()
            self.accept()

    def _key_to_name(self, k):
        m = {
            Qt.Key.Key_Control: "CTRL", Qt.Key.Key_Alt: "ALT", 
            Qt.Key.Key_Shift: "SHIFT", Qt.Key.Key_Meta: "META",
            Qt.Key.Key_Return: "ENTER", Qt.Key.Key_Space: "SPACE"
        }
        if k in m: return m[k]
        return QKeySequence(k).toString().upper()

class SettingsPage(QDialog):
    """
    Redesigned Settings Modal Dialog
    Modern frameless implementation with custom tab switcher.
    """
    settings_saved = Signal()

    def __init__(self, db: DBManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.settings = db.get_settings()
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        
        self.current_tab = "General"
        self._setup_ui()
        
        if parent:
            self.resize(parent.size())
            self.move(parent.mapToGlobal(parent.rect().topLeft()))

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        # Backdrop
        self.backdrop = QFrame()
        self.backdrop.setObjectName("backdrop")
        self.backdrop.setStyleSheet("QFrame#backdrop { background-color: rgba(0, 0, 0, 0.4); border-radius: 24px; }")
        root.addWidget(self.backdrop)

        # Center layout for the container
        container_outer = QVBoxLayout(self.backdrop)
        container_outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_outer.setContentsMargins(40, 40, 40, 40)

        self.container = QFrame()
        self.container.setObjectName("modal_container")
        self.container.setFixedWidth(820)
        self.container.setMaximumHeight(680)
        self.container.setStyleSheet(f"""
            QFrame#modal_container {{ 
                background-color: {Palette.SURFACE_DEFAULT}; 
                border-radius: 24px; 
                border: 1px solid {Palette.SURFACE_DARK}; 
            }}
            QLineEdit {{
                background-color: white;
                border: 1.5px solid {Palette.BORDER_DEFAULT};
                border-radius: 8px;
                padding: 10px 16px;
                font-size: 13px;
                color: {Palette.TEXT_PRIMARY};
            }}
            QLineEdit:focus {{
                border: 1.5px solid {Palette.BRAND_PRIMARY};
            }}
            QSpinBox {{
                background-color: white;
                border: 1.5px solid {Palette.BORDER_DEFAULT};
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 700;
                color: {Palette.TEXT_PRIMARY};
            }}
            QSpinBox:focus {{
                border: 1.5px solid {Palette.BRAND_PRIMARY};
            }}
            QCheckBox {{
                color: {Palette.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 500;
                spacing: 12px;
                outline: none;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 6px;
                border: 2px solid {Palette.BORDER_DEFAULT};
                background-color: white;
            }}
            QCheckBox::indicator:hover {{
                border: 2px solid {Palette.BRAND_PRIMARY};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Palette.BRAND_PRIMARY};
                border: 2px solid {Palette.BRAND_PRIMARY};
                image: url(assets/images/check_white.png);
            }}
        """)
        container_outer.addWidget(self.container)

        l = QVBoxLayout(self.container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setObjectName("settings_header")
        header.setStyleSheet(f"QFrame#settings_header {{ border-bottom: 1px solid {Palette.SURFACE_DARK}; }}")
        header.setFixedHeight(100)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(32, 0, 32, 0)
        
        title_v = QVBoxLayout()
        title_v.setSpacing(4)
        title_v.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        t_lbl = QLabel("Settings")
        t_lbl.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {Palette.TEXT_PRIMARY};")
        
        sub_lbl = QLabel("Tailor your focus experience")
        sub_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {Palette.TEXT_SECONDARY};")
        title_v.addWidget(t_lbl); title_v.addWidget(sub_lbl)
        hl.addLayout(title_v)
        hl.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                border: none; 
                border-radius: 6px; 
                color: {Palette.TEXT_SECONDARY}; 
                font-weight: 900; 
                font-size: 16px;
                font-family: 'Segoe UI';
            }} 
            QPushButton:hover {{ background: #FF5F57; color: white; }}
        """)
        close_btn.clicked.connect(self.reject)
        hl.addWidget(close_btn)
        l.addWidget(header)
        
        # Custom Tab Switcher
        tabs_container = QWidget()
        tabs_container.setFixedHeight(64)
        tabs_l = QHBoxLayout(tabs_container)
        tabs_l.setContentsMargins(32, 12, 32, 12)
        tabs_l.setSpacing(10)
        
        self.tab_btns = {}
        for name in ["General", "Focus Modes", "Emergency"]:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, n=name: self._switch_tab(n))
            tabs_l.addWidget(btn)
            self.tab_btns[name] = btn
            
        tabs_l.addStretch()
        l.addWidget(tabs_container)
        
        # Content Stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        
        self.stack.addWidget(self._scroll_wrap(self._general_tab()))
        self.stack.addWidget(self._scroll_wrap(self._timing_tab()))
        self.stack.addWidget(self._scroll_wrap(self._advanced_tab()))
        
        l.addWidget(self.stack, 1)
        
        # Footer
        footer = QFrame()
        footer.setFixedHeight(80)
        footer.setStyleSheet(f"border-top: 1px solid {Palette.SURFACE_DARK};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(32, 0, 32, 0)
        fl.addStretch()
        
        save_btn = QPushButton("Save Preferences")
        save_btn.setFixedHeight(44)
        save_btn.setMinimumWidth(180)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Palette.BRAND_PRIMARY};
                color: white;
                border: none;
                border-radius: 22px;
                font-weight: 800;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {Palette.BRAND_SECONDARY};
            }}
        """)
        save_btn.clicked.connect(self._save)
        fl.addWidget(save_btn)
        
        l.addWidget(footer)
        self._switch_tab("General")

    def _switch_tab(self, name):
        self.current_tab = name
        idx = {"General": 0, "Focus Modes": 1, "Emergency": 2}.get(name, 0)
        self.stack.setCurrentIndex(idx)
        
        for n, btn in self.tab_btns.items():
            is_active = (n == name)
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet(f"background: {Palette.BRAND_PRIMARY}; color: white; border-radius: 16px; padding: 0 20px; font-weight: 700; font-size: 12px;")
            else:
                btn.setStyleSheet(f"background: white; color: {Palette.TEXT_SECONDARY}; border: 1px solid {Palette.SURFACE_DARK}; border-radius: 16px; padding: 0 20px; font-weight: 600; font-size: 12px;")

    def _scroll_wrap(self, widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.setWidget(widget)
        return scroll

    def _general_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 10, 32, 32)
        layout.setSpacing(24)
        
        layout.addWidget(_section("Profile Settings"))
        self.username_input = QLineEdit(getattr(self.settings, 'username', 'User'))
        self.username_input.setPlaceholderText("Enter your display name")
        self.username_input.setToolTip("Your name as it appears on the dashboard greeting.")
        layout.addWidget(self.username_input)
        
        layout.addSpacing(8)
        layout.addWidget(_section("Audio & Notifications"))
        self.media_vol = _spinbox(0, 100, getattr(self.settings, 'media_volume', 80), " %")
        layout.addWidget(SettingsRow("Media Playback Volume", self.media_vol, subtitle="Volume for background music and videos during breaks."))
        
        self.alarm_vol = _spinbox(0, 100, getattr(self.settings, 'alarm_volume', 70), " %")
        layout.addWidget(SettingsRow("Break Alarm Volume", self.alarm_vol, subtitle="Sound level for break and session ending alerts."))
        
        layout.addSpacing(8)
        layout.addWidget(_section("Visual Feedback"))
        self.bright_boost = _spinbox(0, 100, getattr(self.settings, 'brightness_boost', 0), " %")
        layout.addWidget(SettingsRow("Screen Brightness Dimming", self.bright_boost, subtitle="Dims your screen during strict sessions (if supported)."))
        
        layout.addStretch()
        return w

    def _timing_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 10, 32, 32)
        layout.setSpacing(24)
        
        self._normal_work_interval = _spinbox(1, 480, self.settings.normal_work_interval)
        self._normal_break_duration = _spinbox(1, 480, self.settings.normal_break_duration)
        self._normal_snooze_duration = _spinbox(1, 480, self.settings.normal_snooze_duration)
        
        layout.addWidget(_section("Normal Focus Preferences"))
        layout.addWidget(SettingsRow("Work Window", self._normal_work_interval, subtitle="Active time before a break is triggered."))
        layout.addWidget(SettingsRow("Break Time", self._normal_break_duration, subtitle="Duration of standard rest periods."))
        layout.addWidget(SettingsRow("Snooze Time", self._normal_snooze_duration, subtitle="Delay added when you postpone a break."))
        
        layout.addSpacing(16)
        layout.addWidget(_section("Strict Focus Preferences"))
        self._strict_work_interval = _spinbox(1, 480, self.settings.strict_work_interval)
        self._strict_break_duration = _spinbox(1, 480, self.settings.strict_break_duration)
        self._strict_cooldown = _spinbox(1, 480, self.settings.strict_cooldown)
        
        layout.addWidget(SettingsRow("Work Window", self._strict_work_interval, subtitle="Mandatory high-intensity focus duration."))
        layout.addWidget(SettingsRow("Locked Break Time", self._strict_break_duration, subtitle="Forced break length (cannot be skipped)."))
        layout.addWidget(SettingsRow("Forced Rest After", self._strict_cooldown, subtitle="Mandatory downtime after completing a session."))
        
        layout.addSpacing(16)
        layout.addWidget(_section("Deep Work Preferences"))
        self._focused_mandatory_break = _spinbox(1, 480, self.settings.focused_mandatory_break)
        layout.addWidget(SettingsRow("Mandatory Post-Session Rest", self._focused_mandatory_break, subtitle="Required recovery period after deep-work sessions."))
        
        layout.addStretch()
        return w

    def _advanced_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 10, 32, 32)
        layout.setSpacing(24)
        
        layout.addWidget(_section("Emergency Override System"))
        
        # Enable Toggle
        hce_layout = QHBoxLayout()
        self.hc_enabled_lbl = QLabel("Enable Keyboard Escape Hatch")
        self.hc_enabled_lbl.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.hc_toggle = SlidingToggle()
        self.hc_toggle.setChecked(getattr(self.settings, 'escape_hatch_enabled', True))
        self.hc_toggle.toggled.connect(self._on_escape_hatch_toggled)
        hce_layout.addWidget(self.hc_enabled_lbl); hce_layout.addStretch(); hce_layout.addWidget(self.hc_toggle)
        layout.addLayout(hce_layout)
        
        # Subtitle for toggle
        hce_sub = QLabel("Allow using a key combination to force-close break windows in emergencies.")
        hce_sub.setStyleSheet(f"color: {Palette.TEXT_SECONDARY}; font-size: 12px; font-weight: 500;")
        hce_sub.setWordWrap(True)
        layout.addWidget(hce_sub)
        
        # Combo Setup Row
        layout.addSpacing(8)
        self.combo_btn = QPushButton(getattr(self.settings, 'escape_hatch_combo', 'CTRL+ALT+SHIFT+E'))
        self.combo_btn.setFixedHeight(44)
        self.combo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                border: 2px solid {Palette.BORDER_DEFAULT};
                border-radius: 8px;
                color: {Palette.BRAND_PRIMARY};
                font-family: 'JetBrains Mono';
                font-weight: 800;
                font-size: 14px;
                text-align: left;
                padding: 0 16px;
            }}
            QPushButton:hover {{ border-color: {Palette.BRAND_PRIMARY}; }}
        """)
        self.combo_btn.clicked.connect(self._setup_key_combo)
        self.combo_row = SettingsRow("Override Key Sequence", self.combo_btn, subtitle="Click to re-record your emergency shortcut.")
        layout.addWidget(self.combo_row)
        
        self.hc_dur = _spinbox(1, 5, getattr(self.settings, 'escape_hatch_duration', 3), " SEC")
        self.dur_row = SettingsRow("Activation Hold Time", self.hc_dur, subtitle="Seconds you must hold the keys to override focus.")
        layout.addWidget(self.dur_row)
        
        # Initial state sync
        self._on_escape_hatch_toggled(self.hc_toggle.isChecked())
        
        layout.addSpacing(24)
        layout.addWidget(_section("Application Maintenance"))
        reset_btn = QPushButton("Reset App Data & History")
        reset_btn.setToolTip("Permanently delete all sessions, statistics, and reset your profile name and settings.")
        reset_btn.setFixedHeight(44)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1.5px solid #FF5F57;
                color: #FF5F57;
                border-radius: 8px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: #FF5F57;
                color: white;
            }}
        """)
        reset_btn.clicked.connect(self._reset_all)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        return w

    def _setup_key_combo(self):
        dlg = KeyCaptureModal(self)
        if dlg.exec():
            new_combo = dlg.final_combo
            if new_combo:
                self.combo_btn.setText(new_combo)

    def _on_escape_hatch_toggled(self, enabled):
        self.combo_btn.setEnabled(enabled)
        self.hc_dur.setEnabled(enabled)
        # Visually dim the rows when disabled
        opacity = 1.0 if enabled else 0.5
        for row in [self.combo_row, self.dur_row]:
            row.setGraphicsEffect(None) # Clear previous
            if not enabled:
                from PySide6.QtWidgets import QGraphicsOpacityEffect
                eff = QGraphicsOpacityEffect()
                eff.setOpacity(opacity)
                row.setGraphicsEffect(eff)

    def _reset_all(self):
        dlg = ThemedConfirmDialog(
            "Wipe Data?", 
            "This will permanently delete all your work sessions, stats, and reset your name and settings. This cannot be undone.",
            parent=self,
            danger=True
        )
        if dlg.exec():
            self.db.reset_database()
            from PySide6.QtWidgets import QApplication
            QApplication.exit(1000)

    def _save(self):
        s = self.settings
        s.username = self.username_input.text().strip() or "User"
        s.media_volume = self.media_vol.value()
        s.alarm_volume = self.alarm_vol.value()
        s.brightness_boost = self.bright_boost.value()
        
        s.normal_work_interval = self._normal_work_interval.value()
        s.normal_break_duration = self._normal_break_duration.value()
        s.normal_snooze_duration = self._normal_snooze_duration.value()
        s.strict_work_interval = self._strict_work_interval.value()
        s.strict_break_duration = self._strict_break_duration.value()
        s.strict_cooldown = self._strict_cooldown.value()
        s.focused_mandatory_break = self._focused_mandatory_break.value()
        
        s.escape_hatch_enabled = self.hc_toggle.isChecked()
        s.escape_hatch_combo = self.combo_btn.text().strip().upper()
        s.escape_hatch_duration = self.hc_dur.value()
        
        self.db.save_settings(s)
        self.settings_saved.emit()
        
        msg = ThemedMessageDialog("Settings Saved", "Your preferences have been updated successfully.", self)
        msg.exec()
        self.accept()

    def mousePressEvent(self, event):
        if not self.container.geometry().contains(self.container.mapFromGlobal(event.globalPosition().toPoint())):
            self.reject()
        super().mousePressEvent(event)
