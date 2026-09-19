from PySide6.QtWidgets import QWidget, QScrollArea, QSplitter
from PySide6.QtCore import Qt, Signal, QRectF, QPropertyAnimation, Property, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QMouseEvent, QWheelEvent, QFontMetrics, QBrush, QLinearGradient

class TimelineScale:
    """Dedicated scale and coordinate conversion engine featuring strict 24-hour width plus optimized 60m right padding."""
    def __init__(self, pixels_per_minute: float = 0.55):
        self.pixels_per_minute = pixels_per_minute
        # Professional discrete zoom presets
        self.zoom_presets = [0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0]
        self.current_preset_index = 2  # Default 1.0x (~0.55 ppm baseline)
        self.right_padding_mins = 60  # 60 minutes padding

    def minute_to_x(self, minutes: int) -> int:
        return int(minutes * self.pixels_per_minute)

    def x_to_minute(self, x: float) -> int:
        if self.pixels_per_minute <= 0:
            return 0
        return int(x / self.pixels_per_minute)

    def get_total_width(self) -> int:
        total_timeline_mins = (24 * 60) + self.right_padding_mins
        return int(total_timeline_mins * self.pixels_per_minute)

    def step_zoom(self, zoom_in: bool, current_ppm: float) -> float:
        """Finds and applies the next discrete zoom preset."""
        if zoom_in:
            if self.current_preset_index < len(self.zoom_presets) - 1:
                self.current_preset_index += 1
        else:
            if self.current_preset_index > 0:
                self.current_preset_index -= 1
        
        base_ppm = 0.55
        self.pixels_per_minute = base_ppm * self.zoom_presets[self.current_preset_index]
        return self.pixels_per_minute


class TimelineCanvas(QWidget):
    """Professional self-contained Timeline Canvas with Figma-grade anchor zoom, session gradients, and hover elevation."""
    
    block_selected = Signal(str, int, int) # (category, start_mins, duration_min)
    quest_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.setMouseTracking(True)
        
        self.layout_data = {"quests": []}
        self.playhead_mins = 540
        self.selected_session_id = None
        self.hovered_session_id = None
        
        self.scale = TimelineScale(pixels_per_minute=0.55)

        self.bg_color = QColor("#141417")
        self.track_bg_color = QColor("#18181b")
        self.grid_major_color = QColor("#2a2a35")
        self.grid_minor_color = QColor("#1e1e24")
        self.grid_micro_color = QColor("#16161c")
        self.text_color = QColor("#8e8e99")
        self.playhead_color = QColor("#4F8EF7")

        # Category Colors mapping
        self.category_colors = {
            "physics": (QColor("#38bdf8"), QColor("#0284c7"), QColor("#0ea5e9"), QColor("#38bdf8")),
            "coding": (QColor("#c084fc"), QColor("#9333ea"), QColor("#a855f7"), QColor("#a855f7")),
            "academics": (QColor("#60a5fa"), QColor("#2563eb"), QColor("#3b82f6"), QColor("#3b82f6")),
            "math": (QColor("#fb923c"), QColor("#c2410c"), QColor("#f97316"), QColor("#f97316")),
            "reading": (QColor("#34d399"), QColor("#059669"), QColor("#10b981"), QColor("#10b981")),
            "default": (QColor("#71717a"), QColor("#3f3f46"), QColor("#52525b"), QColor("#71717a"))
        }
        
        self._update_canvas_geometry()

    def _get_scroll_area(self) -> QScrollArea:
        p = self.parent()
        while p is not None:
            if isinstance(p, QScrollArea):
                return p
            p = p.parent()
        return None

    def _update_canvas_geometry(self):
        new_width = self.scale.get_total_width()
        self.setFixedSize(new_width, 180)
        self.updateGeometry()
        self.update()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                event.ignore()
                return

            scroll_area = self._get_scroll_area()
            hbar = scroll_area.horizontalScrollBar() if scroll_area else None
            
            cursor_x = event.position().x()
            time_under_mouse = self.scale.x_to_minute(cursor_x)

            old_ppm = self.scale.pixels_per_minute
            zoom_in = delta > 0
            self.scale.step_zoom(zoom_in, old_ppm)
            
            if self.scale.pixels_per_minute == old_ppm:
                event.accept()
                return

            self._update_canvas_geometry()

            if scroll_area and hbar:
                new_cursor_x = self.scale.minute_to_x(time_under_mouse)
                target_scroll = new_cursor_x - cursor_x
                hbar.setValue(int(target_scroll))

            event.accept()
        else:
            scroll_area = self._get_scroll_area()
            if scroll_area:
                hbar = scroll_area.horizontalScrollBar()
                delta = event.angleDelta().y() if event.angleDelta().y() != 0 else event.angleDelta().x()
                hbar.setValue(hbar.value() - delta)
                event.accept()
            else:
                super().wheelEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        x_pos = event.position().x()
        sessions = self.layout_data.get("quests", [])
        new_hovered_id = None
        
        for session in sessions:
            start_str = session.get("start_time", "09:00")
            try:
                parts = start_str.split(":")
                s_mins = int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                s_mins = 540
            duration = session.get("planned_duration_min", 60)
            
            s_x = self.scale.minute_to_x(s_mins)
            s_w = max(self.scale.minute_to_x(duration), 30)
            
            if s_x <= x_pos <= (s_x + s_w):
                new_hovered_id = session.get("quest_id")
                break
                
        if new_hovered_id != self.hovered_session_id:
            self.hovered_session_id = new_hovered_id
            self.setCursor(Qt.CursorShape.PointingHandCursor if new_hovered_id else Qt.CursorShape.ArrowCursor)
            self.update()
        super().mouseMoveEvent(event)

    def render_timeline(self, layout_data: dict, playhead_mins: int):
        self.layout_data = layout_data or {"quests": []}
        self.playhead_mins = playhead_mins
        self._update_canvas_geometry()

    def select_quest(self, session_id: str):
        self.selected_session_id = session_id
        self.update()
        
    def showEvent(self, event):
        super().showEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        virtual_width = self.width()
        height = self.height()

        header_height = 36
        track_y = header_height + 12
        
        ppm = self.scale.pixels_per_minute
        zoom_ratio = (ppm - 0.35) / (8.0 - 0.35) if ppm > 0.35 else 0.0
        track_height = int(60 + zoom_ratio * 25)
        track_height = max(60, min(85, track_height))

        painter.fillRect(0, 0, virtual_width, header_height, self.bg_color)
        painter.fillRect(0, header_height, virtual_width, height - header_height, self.track_bg_color)

        total_minutes = 24 * 60

        if ppm >= 6.0:
            major_step, minor_step, micro_step = 60, 15, 5
        elif ppm >= 3.0:
            major_step, minor_step, micro_step = 60, 30, 10
        elif ppm >= 1.2:
            major_step, minor_step = 120, 60
            micro_step = None
        else:
            major_step, minor_step = 360, 120
            micro_step = None

        if micro_step:
            painter.setPen(QPen(self.grid_micro_color, 1))
            m = 0
            while m <= total_minutes:
                x = self.scale.minute_to_x(m)
                painter.drawLine(x, header_height, x, height)
                m += micro_step

        painter.setPen(QPen(self.grid_minor_color, 1))
        m = 0
        while m <= total_minutes:
            x = self.scale.minute_to_x(m)
            painter.drawLine(x, header_height, x, height)
            m += minor_step

        painter.setFont(QFont("Segoe UI", 8))
        last_label_right = -1000

        if ppm >= 4.0:
            label_step = 60
        elif ppm >= 1.5:
            label_step = 120
        else:
            label_step = 360

        # Draw time markers including 24:00 at the end
        for m in range(0, total_minutes + 1, label_step):
            x = self.scale.minute_to_x(m)
            painter.setPen(QPen(self.grid_major_color, 1))
            painter.drawLine(x, header_height, x, height)

            hour = m // 60
            minute = m % 60
            
            if ppm >= 6.0 and minute != 0:
                time_str = f"{hour:02d}:{minute:02d}"
            else:
                time_str = f"{hour:02d}:00"

            metrics = QFontMetrics(painter.font())
            text_width = metrics.horizontalAdvance(time_str)

            if x >= last_label_right + 8:
                painter.setPen(self.text_color)
                painter.drawText(x + 4, header_height - 6, time_str)
                last_label_right = x + text_width + 4

        # Uniform past time fill + slanting stripes overlay
        past_x = self.scale.minute_to_x(self.playhead_mins)
        if past_x > 0:
            past_rect = QRectF(0, header_height, past_x, height - header_height)
            
            # Single solid color tint (no gradient fade)
            painter.fillRect(past_rect, QColor(0, 0, 0, 90))
            
            # Slanting stripes overlay
            stripe_brush = QBrush(QColor(255, 255, 255, 12), Qt.BrushStyle.BDiagPattern)
            painter.fillRect(past_rect, stripe_brush)

        sessions = self.layout_data.get("quests", [])
        for session in sessions:
            start_str = session.get("start_time", "09:00")
            try:
                parts = start_str.split(":")
                start_mins = int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                start_mins = 540

            duration = session.get("planned_duration_min", 60)
            
            x = self.scale.minute_to_x(start_mins)
            w = max(self.scale.minute_to_x(duration), 30)
            y = track_y
            h = track_height

            category = session.get("category", "default").lower()
            top_col, bottom_col, border_col, accent_col = self.category_colors.get(category, self.category_colors["default"])

            is_selected = (session.get("quest_id") == self.selected_session_id)
            is_hovered = (session.get("quest_id") == self.hovered_session_id)

            if is_selected:
                border_col = QColor("#3b82f6")
            elif is_hovered:
                border_col = QColor("#60a5fa")
                y -= 2

            card_gradient = QLinearGradient(x, y, x, y + h)
            card_gradient.setColorAt(0.0, top_col)
            card_gradient.setColorAt(1.0, bottom_col)
            
            painter.setBrush(card_gradient)
            painter.setPen(QPen(border_col, 2.0 if (is_selected or is_hovered) else 1.0))
            painter.drawRoundedRect(x, y, w, h, 8, 8)

            if w > 16:
                painter.setBrush(accent_col)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(x + 2, y + 2, 4, h - 4, 2, 2)

            base_font_size = 8 + int(zoom_ratio * 4)
            title_font_size = max(8, min(12, base_font_size))
            title_font = QFont("Segoe UI", title_font_size, QFont.Weight.Bold)
            painter.setFont(title_font)
            
            title_text = session.get("title", "Session")
            metrics = QFontMetrics(title_font)
            text_offset_x = x + 10
            available_text_w = w - 16

            if available_text_w < 40:
                display_text = "P" if available_text_w > 15 else ""
            elif available_text_w < 70:
                display_text = metrics.elidedText("Prepare...", Qt.TextElideMode.ElideRight, available_text_w)
            elif available_text_w < 130:
                display_text = metrics.elidedText(title_text, Qt.TextElideMode.ElideRight, available_text_w)
            elif available_text_w < 220:
                display_text = metrics.elidedText(f"{title_text} Chapter 4", Qt.TextElideMode.ElideRight, available_text_w)
            else:
                display_text = title_text

            if display_text:
                if metrics.boundingRect(display_text).width() <= available_text_w:
                    painter.setPen(QColor("#ffffff"))
                    painter.drawText(text_offset_x, y + 14, available_text_w, 18, Qt.AlignmentFlag.AlignLeft, display_text)
                else:
                    elided = metrics.elidedText(display_text, Qt.TextElideMode.ElideRight, available_text_w)
                    painter.setPen(QColor("#ffffff"))
                    painter.drawText(text_offset_x, y + 14, available_text_w, 18, Qt.AlignmentFlag.AlignLeft, elided)

            if w >= 120:
                painter.setPen(QColor("#d1d5db"))
                painter.setFont(QFont("Segoe UI", 7))
                end_mins = start_mins + duration
                end_str = f"{end_mins // 60:02d}:{end_mins % 60:02d}"
                painter.drawText(text_offset_x, y + 32, available_text_w, 14, Qt.AlignmentFlag.AlignLeft, f"{start_str} – {end_str}")

                completion_pct = session.get("completion_pct", 0)
                if completion_pct > 0 and w > 180:
                    bar_y = y + h - 12
                    bar_w = w - 20
                    painter.setBrush(QColor("#18181b"))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(text_offset_x, bar_y, bar_w, 4, 2, 2)
                    
                    fill_w = int(bar_w * (completion_pct / 100.0))
                    painter.setBrush(accent_col)
                    painter.drawRoundedRect(text_offset_x, bar_y, fill_w, 4, 2, 2)

            if session.get("is_current", False):
                painter.setPen(QPen(QColor("#f59e0b"), 1.8))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(x - 1, y - 1, w + 2, h + 2, 9, 9)
                
                badge_rect = QRectF(x + w - 52, y + 4, 48, 16)
                painter.setBrush(QColor("#78350f"))
                painter.setPen(QColor("#f59e0b"))
                painter.drawRoundedRect(badge_rect, 3, 3)
                painter.setPen(QColor("#fef3c7"))
                painter.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
                painter.drawText(badge_rect, int(Qt.AlignmentFlag.AlignCenter), "CURRENT")

        playhead_x = self.scale.minute_to_x(self.playhead_mins)
        painter.setPen(QPen(self.playhead_color, 2))
        painter.drawLine(playhead_x, 0, playhead_x, height)
        
        ph_hour = self.playhead_mins // 60
        ph_min = self.playhead_mins % 60
        ph_str = f"{ph_hour:02d}:{ph_min:02d}"
        
        badge_w = 46
        badge_h = 18
        bx = max(2, min(playhead_x - badge_w // 2, virtual_width - badge_w - 2))
        
        painter.setBrush(QColor("#2563EB"))
        painter.setPen(QPen(QColor("#60A5FA"), 1))
        painter.drawRoundedRect(QRectF(bx, 2, badge_w, badge_h), 4, 4)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        painter.drawText(QRectF(bx, 2, badge_w, badge_h), int(Qt.AlignmentFlag.AlignCenter), ph_str)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            x_pos = event.position().x()
            clicked_mins = self.scale.x_to_minute(x_pos)
            
            sessions = self.layout_data.get("quests", [])
            clicked_session_id = None
            for session in sessions:
                start_str = session.get("start_time", "09:00")
                try:
                    parts = start_str.split(":")
                    s_mins = int(parts[0]) * 60 + int(parts[1])
                except (ValueError, IndexError):
                    s_mins = 540
                duration = session.get("planned_duration_min", 60)
                
                s_x = self.scale.minute_to_x(s_mins)
                s_w = max(self.scale.minute_to_x(duration), 30)
                
                if s_x <= x_pos <= (s_x + s_w):
                    clicked_session_id = session.get("quest_id")
                    break

            if clicked_session_id:
                self.quest_selected.emit(clicked_session_id)
            else:
                if clicked_mins >= self.playhead_mins:
                    clamped_mins = min(clicked_mins, 24 * 60 - 30)
                    self.block_selected.emit("academics", clamped_mins, 60)


def build_scheduler_ui_layout(main_window_widget: QWidget, timeline_canvas: TimelineCanvas, sidebar_widget: QWidget) -> QSplitter:
    """Constructs layout hierarchy allowing interactive sidebar resizing."""
    scroll_area = QScrollArea(main_window_widget)
    scroll_area.setWidget(timeline_canvas)
    scroll_area.setWidgetResizable(False)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    scroll_area.setStyleSheet("""
        QScrollArea {
            border: none;
            background: transparent;
        }
        QScrollBar:horizontal {
            height: 6px;
            background: transparent;
            margin: 0px;
            border: none;
        }
        QScrollBar::handle:horizontal {
            background: #2563EB;
            border-radius: 3px;
            min-width: 60px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #3B82F6;
        }
        QScrollBar::handle:horizontal:pressed {
            background: #60A5FA;
        }
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {
            width: 0px;
            background: none;
        }
        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {
            background: transparent;
        }
    """)

    # Flexible bounds allowing resizing
    sidebar_widget.setMinimumWidth(280)
    sidebar_widget.setMaximumWidth(500)

    splitter = QSplitter(Qt.Orientation.Horizontal, main_window_widget)
    splitter.addWidget(scroll_area)
    splitter.addWidget(sidebar_widget)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 0)
    
    splitter.setStyleSheet("""
        QSplitter::handle {
            background: #27272a;
            width: 3px;
        }
        QSplitter::handle:hover {
            background: #3b82f6;
        }
    """)

    return splitter