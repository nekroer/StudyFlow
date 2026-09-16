import math
import json
from PySide6.QtCore import Qt, QPointF, QRectF, Signal as pyqtSignal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import QWidget, QSizePolicy
from app.backend.paths import TIMER_SIZE_CONFIG_FILE


class CircularTimer(QWidget):
    """
    A 60-minute Visual Time-Timer widget supporting Opaque Single Colors 
    and a Rainbow multi-band arc layout with dynamic resizability.
    """

    timerFinished = pyqtSignal()
    timeChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._max_seconds = 3600  # Explicitly set full 60-minute scale
        self._remaining_seconds = 3600
        self._is_dragging = False

        self._bg_color = QColor(255, 255, 255)
        self._dial_color = QColor(20, 25, 35)        
        self._needle_color = QColor(220, 20, 20)      

        self.current_theme = "rainbow"
        self._wedge_color = QColor("#0096D6")        

        self._rainbow_colors = [
            QColor("#E74C3C"),   # Red
            QColor("#E67E22"),   # Orange
            QColor("#F1C40F"),   # Yellow
            QColor("#2ECC71"),   # Green
            QColor("#0096D6"),   # Light Blue
            QColor("#9B59B6"),   # Purple
        ]

        # Load size directly from config or fallback to default 420px
        timer_size = 420
        if TIMER_SIZE_CONFIG_FILE.exists():
            try:
                config_data = json.loads(TIMER_SIZE_CONFIG_FILE.read_text(encoding="utf-8"))
                timer_size = config_data.get("timer_size", 420)
            except Exception:
                pass

        self.setFixedSize(timer_size, timer_size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_theme(self, theme_key: str, hex_code: str = "#0096D6"):
        self.current_theme = theme_key
        if hex_code:
            self._wedge_color = QColor(hex_code)
        self.update()

    def set_duration(self, total_seconds: int):
        self._remaining_seconds = min(self._max_seconds, max(0, total_seconds))
        self.update()

    def update_time(self, remaining_seconds: int):
        if not self._is_dragging:
            self._remaining_seconds = max(0, min(self._max_seconds, remaining_seconds))
            self.update()

    def get_remaining_seconds(self) -> int:
        return self._remaining_seconds

    def mousePressEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._update_time_from_pos(event.position())

    def mouseMoveEvent(self, event):
        if self.isEnabled() and self._is_dragging:
            self._update_time_from_pos(event.position())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

    def _update_time_from_pos(self, pos: QPointF):
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()

        angle = math.degrees(math.atan2(dx, -dy))
        if angle < 0:
            angle += 360.0

        fraction = angle / 360.0
        calculated_seconds = int(fraction * self._max_seconds)
        calculated_seconds = round(calculated_seconds / 60) * 60
        self._remaining_seconds = max(0, min(self._max_seconds, calculated_seconds))
        
        self.timeChanged.emit(self._remaining_seconds)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        size = min(width, height)
        center = QPointF(width / 2.0, height / 2.0)

        radius = (size / 2.0) - max(10, size * 0.04)
        inner_knob_radius = radius * 0.22
        wedge_radius = radius * 0.78
        rainbow_inner_radius = radius * 0.28

        # 1. Background White Dial
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._bg_color))
        painter.drawEllipse(center, radius, radius)

        # 2. Main Timer Display
        fraction = self._remaining_seconds / self._max_seconds
        sweep_angle = fraction * 360.0

        if fraction > 0:
            if self.current_theme == "rainbow":
                num_bands = len(self._rainbow_colors)
                band_thickness = (wedge_radius - rainbow_inner_radius) / num_bands

                for idx, color in enumerate(self._rainbow_colors):
                    r_out = wedge_radius - (idx * band_thickness)
                    pen = QPen(color, band_thickness + 0.5)
                    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
                    painter.setPen(pen)

                    r_mid = r_out - (band_thickness / 2.0)
                    rect_mid = QRectF(center.x() - r_mid, center.y() - r_mid, r_mid * 2, r_mid * 2)
                    painter.drawArc(rect_mid, int(90 * 16), int(-sweep_angle * 16))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(self._wedge_color))
                wedge_rect = QRectF(
                    center.x() - wedge_radius,
                    center.y() - wedge_radius,
                    wedge_radius * 2,
                    wedge_radius * 2,
                )
                painter.drawPie(wedge_rect, int(90 * 16), int(-sweep_angle * 16))

        # 3. Numbers Around Dial
        num_font = QFont("Segoe UI", max(8, int(size * 0.038)), QFont.Weight.Bold)
        painter.setFont(num_font)
        painter.setPen(self._dial_color)
        number_radius = radius * 0.88

        for i in range(12):
            val = i * 5
            angle_deg = (i * 30) - 90
            angle_rad = math.radians(angle_deg)

            x = center.x() + number_radius * math.cos(angle_rad)
            y = center.y() + number_radius * math.sin(angle_rad)

            txt_rect = QRectF(x - 20, y - 15, 40, 30)
            painter.drawText(txt_rect, Qt.AlignmentFlag.AlignCenter, str(val))

        # 4. Minute Ticks
        pen_tick = QPen(self._dial_color, max(1, int(size * 0.004)))
        painter.setPen(pen_tick)
        tick_outer = radius * 0.80
        tick_inner_major = radius * 0.73
        tick_inner_minor = radius * 0.76

        for minute in range(60):
            angle_deg = (minute * 6) - 90
            angle_rad = math.radians(angle_deg)

            t_inner = tick_inner_major if (minute % 5 == 0) else tick_inner_minor
            p1 = QPointF(
                center.x() + tick_outer * math.cos(angle_rad),
                center.y() + tick_outer * math.sin(angle_rad),
            )
            p2 = QPointF(
                center.x() + t_inner * math.cos(angle_rad),
                center.y() + t_inner * math.sin(angle_rad),
            )
            painter.drawLine(p1, p2)

        # 5. Pointer Needle Line
        if fraction > 0:
            needle_angle_rad = math.radians(-sweep_angle + 90)
            p_start = QPointF(
                center.x() + inner_knob_radius * 0.8 * math.cos(needle_angle_rad),
                center.y() - inner_knob_radius * 0.8 * math.sin(needle_angle_rad),
            )
            p_end = QPointF(
                center.x() + tick_outer * math.cos(needle_angle_rad),
                center.y() - tick_outer * math.sin(needle_angle_rad),
            )

            needle_pen = QPen(self._needle_color, max(2, int(size * 0.008)))
            needle_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(needle_pen)
            painter.drawLine(p_start, p_end)

        # 6. Center Knob
        knob_rect = QRectF(
            center.x() - inner_knob_radius,
            center.y() - inner_knob_radius,
            inner_knob_radius * 2,
            inner_knob_radius * 2,
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
        painter.drawEllipse(knob_rect.adjusted(3, 3, 3, 3))

        painter.setPen(QPen(QColor(200, 205, 210), 2))
        painter.setBrush(QBrush(QColor(245, 245, 248)))
        painter.drawEllipse(knob_rect)

        painter.end()
    
    def update_size(self, new_size: int):
        self.setFixedSize(new_size, new_size)
        self.updateGeometry()  # Tells the layout manager to update its geometry
        self.update()