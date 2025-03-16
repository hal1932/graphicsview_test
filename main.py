from typing import *

import sys
import math

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *


class rectf:

    @staticmethod
    def scale(rect: QRectF, value: QPointF):
        return QRectF(
            QPointF(rect.left() * value.x(), rect.top() * value.y()),
            QPointF(rect.right() * value.x(), rect.bottom() * value.y())
        )
    
    @staticmethod
    def translate(rect: QRectF, value: QPointF):
        return QRectF(
            QPointF(rect.left() + value.x(), rect.top() + value.y()),
            rect.size()
        )


class GraphicsView(QGraphicsView):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__mouse_press_pos = QPointF()
        self.__last_mouse_pos = QPointF()

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setScene(GraphicsScene())
        self.setSceneRect(self.scene().sceneRect())
    
    def resizeEvent(self, event: QResizeEvent):
        scene_rect = self.scene().sceneRect()
        size = event.size()
        view_rect = QRectF(scene_rect.left(), scene_rect.top(), size.width(), size.height())
        self.setSceneRect(view_rect)
        self.scene().update_grid(view_rect)
    
    def wheelEvent(self, event: QWheelEvent):
        if Qt.KeyboardModifier.AltModifier in event.modifiers():
            delta = event.angleDelta().x()
            scale = 1 + (0.05 if delta < 0 else -0.05)
            view_rect = self.sceneRect()

            pos = event.position()
            pos = QPoint(pos.x(), pos.y())
            pivot = self.mapToScene(pos)

            view_rect = self.__scale(scale, pivot)
            self.scene().update_grid(view_rect)
        
        return super().wheelEvent(event)
    
    def mousePressEvent(self, event: QMouseEvent):
        self.__last_mouse_pos = event.position()
        self.__mouse_press_pos = event.position()
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if Qt.KeyboardModifier.AltModifier in event.modifiers():
            delta = self.__last_mouse_pos - event.position()

            if Qt.MouseButton.MiddleButton in event.buttons():
                view_rect = self.sceneRect()
                scale_x = view_rect.width() / self.width()
                scale_y = view_rect.height() / self.height()

                delta = QPointF(delta.x() * scale_x, delta.y() * scale_y)
                view_rect = self.__move(delta)
                self.scene().update_grid(view_rect)

            elif Qt.MouseButton.RightButton in event.buttons():
                scale = 1 + (0.01 if delta.x() > 0 else -0.01)
                view_rect = self.sceneRect()

                pos = self.__mouse_press_pos
                pos = QPoint(pos.x(), pos.y())
                pivot = self.mapToScene(pos)
                
                view_rect = self.__scale(scale, pivot)
                self.scene().update_grid(view_rect)

        self.__last_mouse_pos = event.position()
        return super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        self.__last_mouse_pos = QPointF()
        self.__mouse_press_pos = QPointF()
        return super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_F:
            view_rect = self.sceneRect()
            delta = QPointF(-view_rect.left() - view_rect.width() / 2.0, -view_rect.top() - view_rect.height() / 2.0)
            view_rect = self.__move(delta)
            self.scene().update_grid(view_rect)
            
        return super().keyPressEvent(event)
    
    def add_item(self):
        self.scene().add_item()
    
    def __move(self, value: QPointF) -> QRectF:
        view_rect = self.sceneRect()

        view_rect = rectf.translate(view_rect, value)
        self.setSceneRect(view_rect)

        m = QTransform()
        m.scale(self.width() / view_rect.width(), self.height() / view_rect.height())
        m.translate(value.x(), value.y())
        self.setTransform(m)

        return view_rect
    
    def __scale(self, value: QPointF, pivot: QPointF) -> QRectF:
        view_rect = self.sceneRect()

        view_rect = rectf.translate(view_rect, -pivot)
        view_rect = rectf.scale(view_rect, QPointF(value, value))
        view_rect = rectf.translate(view_rect, pivot)

        self.setSceneRect(view_rect)

        m = QTransform()
        m.scale(self.width() / view_rect.width(), self.height() / view_rect.height())
        self.setTransform(m)

        return view_rect


class GraphicsScene(QGraphicsScene):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.__grid = SceneGrid()
        self.sceneRectChanged.connect(self.update_grid)

        for i in range(10):
            x = (i - 5) * 50
            y = (i - 5) * 50
            item = TestItem(QRectF(x, y, 50, 50))
            self.addItem(item)
        
    def drawBackground(self, painter: QPainter, rect: QRectF):
        self.__grid.draw(painter)

        painter.setPen(QColor(255, 0, 0))
        painter.drawRect(self.sceneRect())

        painter.drawEllipse(-5, -5, 10, 10)
    
    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent):
        if self.itemAt(event.scenePos(), QTransform()):
            return super().contextMenuEvent(event)
        print('SCENE ctx')
    
    def update_grid(self, rect: QRectF):
        self.__grid.update(rect)
        
    def add_item(self):
        rect = self.itemsBoundingRect()
        item = TestItem(QRectF(rect.bottomRight(), QSizeF(50, 50)))
        self.addItem(item)
        self.update()


class SceneGrid(object):

    def __init__(self):
        self.update_unit = 500
        self.cell_size = 100
        self.__rect = QRectF()
        self.__lines: List[QLine] = []

    def update(self, rect: QRectF):
        def _fit(_v, _start):
            _ofs = _v % self.update_unit
            if not _start:
                _ofs = self.update_unit - _ofs
            if _ofs == 0:
                _ofs = self.update_unit
            return _v + (-1 if _start else 1) * _ofs
        
        left = _fit(rect.left(), True)
        top = _fit(rect.top(), True)
        right = _fit(rect.right(), False)
        bottom = _fit(rect.bottom(), False)

        gr = self.__rect
        ofs_left = math.fabs(left - gr.left())
        ofs_top = math.fabs(top - gr.top())
        ofs_right = math.fabs(right - gr.right())
        ofs_bottom = math.fabs(bottom - gr.bottom())
        if ofs_left < self.update_unit and ofs_top < self.update_unit and ofs_right < self.update_unit and ofs_bottom < self.update_unit:
            return
        
        lines = []

        y = top
        while y <= bottom:
            lines.append(QLine(left, y, right, y))
            y += self.cell_size
        
        x = left
        while x <= right:
            lines.append(QLine(x, top, x, bottom))
            x += self.cell_size
        
        self.__rect = rect
        self.__lines = lines
    
    def draw(self, painter: QPainter):
        painter.setPen(QColor(200, 200, 200))
        painter.drawLines(self.__lines)


class TestItem(QGraphicsItem):

    def __init__(self, rect: QRectF, parent: QGraphicsItem = None):
        super().__init__(parent)
        self.rect = rect
    
    def boundingRect(self):
        return self.rect
    
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget]):
        painter.setPen(QColor(0, 0, 255))
        painter.drawRect(option.rect)
    
    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent):
        print('ITEM ctx')


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle('Graphics View Test')

        view = GraphicsView()

        btn = QPushButton('AAA')
        btn.clicked.connect(view.add_item)

        lyt = QVBoxLayout()
        lyt.addWidget(view)
        lyt.addWidget(btn)

        w = QWidget()
        w.setLayout(lyt)
        self.setCentralWidget(w)


def main():
    app = QApplication()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
