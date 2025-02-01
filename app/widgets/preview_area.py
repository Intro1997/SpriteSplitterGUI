import sys
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QLabel
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QTimer
from PySide6.QtGui import QImage, QPixmap, QPen, QColor, QPainter
from sprite_splitter import Box
from typing import List


class PreviewArea(QGraphicsView):
    box_modified = Signal()

    def __init__(self, file_list):
        super().__init__()
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.file_list = file_list

        self.setBackgroundBrush(QColor(31, 31, 31))

        # scalling settings
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.zoom_factor = 1.0
        self.min_zoom = 1.0
        self.max_zoom = None  # set in image load

        self.current_image = None
        self.boxes: List[Box] = []
        self.original_boxes: List[Box] = []
        self.selected_box = None
        self.drag_handle = None
        self.drag_start_pos = None
        self.drag_start_rect = None

        # support undo opration
        self.undo_stack = []

        self.current_image_path = None

        # For the purpose of optimizing rendering,
        # we delay the re-rendering of the box's border
        # until 100ms after the zoom operation is completed.
        # This ensures that the border is always drawn at 1 pixel
        # width across any zoom level.
        self.redraw_timer = QTimer()
        self.redraw_timer.setSingleShot(True)
        self.redraw_timer.setInterval(100)     # 100ms
        self.redraw_timer.timeout.connect(self.draw_boxes)

        # display position info of cursor
        self.coord_label = QLabel(self)
        self.coord_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 100);
                color: white;
                padding: 5px;
                border-radius: 3px;
            }
        """)
        self.coord_label.hide()

        self.setFocusPolicy(Qt.StrongFocus)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        self.file_list.add_files(files)

    def load_image(self, image_path, boxes: List[Box]):
        # if same path, do not process
        if image_path == self.current_image_path:
            return

        # clear last state
        self.selected_box = None
        self.scene.clear()

        # load image to scene
        self.current_image = QImage(image_path)
        pixmap = QPixmap.fromImage(self.current_image)
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())
        self.scene.addPixmap(pixmap)
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.zoom_factor = 1.0
        self.current_image_path = image_path

        # save and draw box
        self.original_boxes = boxes.copy()
        self.boxes = boxes.copy()
        self.draw_boxes()

        self.max_zoom = min(
            self.current_image.width() / 10,
            self.current_image.height() / 10
        )

        self.update_coord_label_position()

    def wheelEvent(self, event):
        if not self.current_image:
            return

        modifiers = event.modifiers()
        delta_y = event.angleDelta().y()
        delta_x = event.angleDelta().x()

        scroll_step = 20  # scrolling speed

        # only use ctrl+wheel to scale
        if (not sys.platform.startswith("darwin") and modifiers == Qt.ControlModifier) or \
                (sys.platform.startswith("darwin") and modifiers == Qt.MetaModifier):

            factor = 1.1 if delta_y > 0 else 0.9
            new_zoom = self.zoom_factor * factor

            if self.min_zoom <= new_zoom <= self.max_zoom:
                self.zoom_factor = new_zoom
                self.scale(factor, factor)

                self.redraw_timer.stop()
                self.redraw_timer.start()
        # horizontal scrolling
        elif modifiers & Qt.ShiftModifier:
            delta = delta_x if delta_x != 0 else delta_y
            delta_value = scroll_step if delta > 0 else -scroll_step
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta_value
            )
        # vertical scrolling
        else:
            delta_value = scroll_step if delta_y > 0 else -scroll_step
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta_value
            )

        event.accept()

    def draw_boxes(self):
        self.scene.clear()

        if self.current_image:
            pixmap = QPixmap.fromImage(self.current_image)
            self.scene.addPixmap(pixmap)

        self.viewport().update()
        scale = self.transform().m11()  # get scalling ratio

        for i, box in enumerate(self.boxes):
            ltcx, ltcy = box.left_top_corner
            rbcx, rbcy = box.right_bottom_corner
            tbox = box.left_top_corner + (rbcx - ltcx + 1, rbcy - ltcy + 1)
            rect = QGraphicsRectItem(QRectF(*tbox))

            if i == self.selected_box:
                pen = QPen(QColor(0, 255, 0))
                pen.setWidthF(1.0 / scale)
            else:
                pen = QPen(QColor(255, 0, 0))
                pen.setWidthF(1.0 / scale)
            rect.setPen(pen)
            self.scene.addItem(rect)

            if i == self.selected_box:
                # draw control point
                control_point_size = 10 / scale
                rect_f = QRectF(*tbox)

                control_points = [
                    (rect_f.topLeft(), 'top-left'),
                    (rect_f.topRight(), 'top-right'),
                    (rect_f.bottomLeft(), 'bottom-left'),
                    (rect_f.bottomRight(), 'bottom-right'),
                    (QPointF(rect_f.center().x(), rect_f.top()), 'top'),
                    (QPointF(rect_f.center().x(), rect_f.bottom()), 'bottom'),
                    (QPointF(rect_f.left(), rect_f.center().y()), 'left'),
                    (QPointF(rect_f.right(), rect_f.center().y()), 'right')
                ]

                for point, _ in control_points:
                    handle = QGraphicsRectItem(
                        QRectF(
                            point.x() - control_point_size/2,
                            point.y() - control_point_size/2,
                            control_point_size,
                            control_point_size
                        )
                    )
                    handle.setPen(pen)
                    handle.setBrush(QColor(0, 255, 0))
                    self.scene.addItem(handle)

    def _handle_box_checked(self, i, box, pos):
        ltcx, ltcy = box.left_top_corner
        rbcx, rbcy = box.right_bottom_corner
        tbox = box.left_top_corner + (rbcx - ltcx + 1, rbcy - ltcy + 1)
        rect = QRectF(*tbox)

        """
        handling box control point click
        """
        # resize control point by scalling
        control_point_size = 10 / self.transform().m11()
        # all control point position on box
        control_point_pos_infos = [
            (rect.topLeft(), 'top-left'),
            (rect.topRight(), 'top-right'),
            (rect.bottomLeft(), 'bottom-left'),
            (rect.bottomRight(), 'bottom-right'),
            (QPointF(rect.center().x(), rect.top()), 'top'),
            (QPointF(rect.center().x(), rect.bottom()), 'bottom'),
            (QPointF(rect.left(), rect.center().y()), 'left'),
            (QPointF(rect.right(), rect.center().y()), 'right')
        ]
        for control_point_pos, control_point_type in control_point_pos_infos:
            control_point_rect = QRectF(
                control_point_pos.x() - control_point_size/2,
                control_point_pos.y() - control_point_size/2,
                control_point_size,
                control_point_size
            )
            if control_point_rect.contains(pos):
                self.selected_box = i
                self.drag_start_pos = pos
                self.drag_start_rect = rect
                self.drag_handle = control_point_type
                self.draw_boxes()
                self.box_modified.emit()
                return True

        """
        handling box click
        """
        inner_rect = QRectF(
            rect.x(),
            rect.y(),
            rect.width(),
            rect.height()
        )
        if inner_rect.contains(pos):
            self.selected_box = i
            self.drag_start_pos = pos
            self.drag_start_rect = rect
            self.drag_handle = 'move'
            self.draw_boxes()
            self.box_modified.emit()
            return True
        return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.pos())
            # do selected box check first
            if self.selected_box and \
                    self._handle_box_checked(self.selected_box, self.boxes[self.selected_box], pos):
                return

            for i, box in enumerate(self.boxes):
                if self._handle_box_checked(i, box, pos):
                    return
                elif self.selected_box == i:
                    continue
            """
            handling empty area click
            (cancel box selected)
            """
            self.selected_box = None
            self.drag_handle = None
            self.draw_boxes()
            self.box_modified.emit()

    def mouseMoveEvent(self, event):
        # handling box moving
        if event.buttons() & Qt.LeftButton and self.selected_box is not None:
            pos = self.mapToScene(event.pos())
            delta = pos - self.drag_start_pos

            image_rect = QRectF(
                0, 0, self.current_image.width() - 1, self.current_image.height() - 1)

            c_box = self.boxes[self.selected_box]
            new_box = list(c_box.left_top_corner + c_box.right_bottom_corner)

            # process drag of entire box
            if self.drag_handle == 'move':
                width = new_box[2] - new_box[0]
                height = new_box[3] - new_box[1]

                new_left = self.drag_start_rect.x() + delta.x()
                new_top = self.drag_start_rect.y() + delta.y()

                right_boundary_reached = new_left + width >= image_rect.right()
                bottom_boundary_reached = new_top + height >= image_rect.bottom()

                if right_boundary_reached and delta.x() > 0:
                    new_left = image_rect.right() - width

                if bottom_boundary_reached and delta.y() > 0:
                    new_top = image_rect.bottom() - height

                new_left = max(0, new_left)
                new_top = max(0, new_top)

                new_box[0] = int(new_left)
                new_box[1] = int(new_top)
                new_box[2] = int(new_left + width)
                new_box[3] = int(new_top + height)
            # prcess drag of control point on box
            else:
                if 'left' in self.drag_handle:
                    new_box[0] = int(max(self.drag_start_rect.x() +
                                     delta.x(), 0))
                    new_box[0] = int(min(new_box[0], new_box[2]))
                if 'right' in self.drag_handle:
                    new_right = self.drag_start_rect.right() - 1 + delta.x()
                    new_box[2] = int(
                        min(new_right, self.current_image.width()))
                if 'top' in self.drag_handle:
                    new_box[1] = int(max(self.drag_start_rect.y() +
                                     delta.y(), 0))
                    new_box[1] = int(min(new_box[1], new_box[3]))
                if 'bottom' in self.drag_handle:
                    new_bottom = self.drag_start_rect.bottom() - 1 + delta.y()
                    new_box[3] = int(
                        min(new_bottom, self.current_image.height()))
                new_box[0] = max(0, min(new_box[0], image_rect.right()))
                new_box[1] = max(0, min(new_box[1], image_rect.bottom()))
                new_box[2] = max(new_box[0], min(
                    new_box[2], image_rect.right()))
                new_box[3] = max(new_box[1], min(
                    new_box[3], image_rect.bottom()))

            self.boxes[self.selected_box] = Box(
                (new_box[0], new_box[1]), (new_box[2], new_box[3]))
            self.draw_boxes()
            self.box_modified.emit()
        # handling box control point moving
        else:
            pos = self.mapToScene(event.pos())
            cursor = Qt.ArrowCursor

            if self.selected_box is not None:
                box = self.boxes[self.selected_box]
                ltcx, ltcy = box.left_top_corner
                rbcx, rbcy = box.right_bottom_corner
                tbox = box.left_top_corner + (rbcx - ltcx + 1, rbcy - ltcy + 1)
                rect = QRectF(*tbox)
                control_point_size = 10 / self.transform().m11()

                control_points = [
                    (rect.topLeft(), Qt.SizeFDiagCursor, 'top-left'),      # ↖↘
                    (rect.topRight(), Qt.SizeBDiagCursor, 'top-right'),    # ↗↙
                    (rect.bottomLeft(), Qt.SizeBDiagCursor, 'bottom-left'),  # ↗↙
                    (rect.bottomRight(), Qt.SizeFDiagCursor, 'bottom-right'),  # ↖↘
                    (QPointF(rect.center().x(), rect.top()),
                     Qt.SizeVerCursor, 'top'),       # ↕
                    (QPointF(rect.center().x(), rect.bottom()),
                     Qt.SizeVerCursor, 'bottom'),  # ↕
                    (QPointF(rect.left(), rect.center().y()),
                     Qt.SizeHorCursor, 'left'),     # ↔
                    (QPointF(rect.right(), rect.center().y()),
                     Qt.SizeHorCursor, 'right')    # ↔
                ]

                for point, cursor_shape, _ in control_points:
                    control_point_rect = QRectF(
                        point.x() - control_point_size/2,
                        point.y() - control_point_size/2,
                        control_point_size,
                        control_point_size
                    )
                    if control_point_rect.contains(pos):
                        cursor = cursor_shape
                        break

                if cursor == Qt.ArrowCursor:
                    inner_margin = 5
                    inner_rect = QRectF(
                        rect.x() + inner_margin,
                        rect.y() + inner_margin,
                        rect.width() - 2 * inner_margin,
                        rect.height() - 2 * inner_margin
                    )
                    if inner_rect.contains(pos):
                        cursor = Qt.SizeAllCursor

            self.viewport().setCursor(cursor)

        # update cursor position label at bottom
        # right corner
        scene_pos = self.mapToScene(event.pos())
        if self.current_image:
            x = int(max(0, min(scene_pos.x(), self.current_image.width() - 1)))
            y = int(max(0, min(scene_pos.y(), self.current_image.height() - 1)))

            self.coord_label.setText(f"x: {x}, y: {y}")
            self.coord_label.adjustSize()

            if not self.coord_label.isVisible():
                self.coord_label.show()
            self.update_coord_label_position()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.selected_box is not None:
            # Update the coordinates of the upper left and lower right corners
            box = self.boxes[self.selected_box]
            lx, ly = box.left_top_corner
            rx, ry = box.right_bottom_corner
            box.left_top_corner = (min(lx, rx), min(ly, ry))
            box.right_bottom_corner = (max(lx, rx), max(ly, ry))

            # save tmp box to undo stack
            self.undo_stack.append(self.boxes.copy())
            self.box_modified.emit()
        super().mouseReleaseEvent(event)

    def undo_last_action(self):
        if self.undo_stack:
            self.boxes = self.undo_stack.pop()
            self.draw_boxes()
            if not self.undo_stack:
                self.box_modified.emit()

    def save_changes(self):
        self.original_boxes = self.boxes.copy()
        self.undo_stack.clear()

    def cancel_changes(self):
        self.boxes = self.original_boxes.copy()
        self.undo_stack.clear()
        self.draw_boxes()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_coord_label_position()

    def update_coord_label_position(self):
        if self.coord_label:
            margin = 10
            label_width = self.coord_label.width()
            label_height = self.coord_label.height()
            new_x = self.width() - label_width - margin
            new_y = self.height() - label_height - margin
            self.coord_label.move(new_x, new_y)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.coord_label.hide()

    def keyPressEvent(self, event):
        """
        handling delete key input
        (delete the selected box)
        """
        if event.key() == Qt.Key_Delete and self.selected_box is not None:
            self.undo_stack.append(self.boxes.copy())
            self.boxes.pop(self.selected_box)
            self.selected_box = None
            self.draw_boxes()
            self.box_modified.emit()
            event.accept()
        else:
            super().keyPressEvent(event)
