from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton
)
from PySide6.QtGui import QShortcut, QKeySequence, QPalette
from .widgets.file_list import FileListWidget
from .widgets.preview_area import PreviewArea
from .widgets.info_panel import InfoPanel
from sprite_splitter import Box
from typing import List


def is_dark_mode(app):
    palette = app.palette()
    background_color = palette.color(QPalette.Window)

    brightness = background_color.red() * 0.299 + background_color.green() * \
        0.587 + background_color.blue() * 0.114
    return brightness < 128


class MainWindow(QMainWindow,):
    def __init__(self, app):
        super().__init__()
        self.setWindowTitle("Sprite Splitter GUI")
        self.setMinimumSize(800, 600)
        self.is_dark_mode = is_dark_mode(app)
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        layout = QHBoxLayout()

        self.file_list = FileListWidget()
        self.preview_area = PreviewArea(self.file_list, self.is_dark_mode)
        self.info_panel = InfoPanel(self.file_list)

        layout.addWidget(self.file_list)
        layout.addWidget(self.preview_area)
        layout.addWidget(self.info_panel)

        layout.setStretch(0, 1)  # file list
        layout.setStretch(1, 3)  # preivew area
        layout.setStretch(2, 1)  # info panel

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)

        self.save_button.clicked.connect(self.save_changes)
        self.cancel_button.clicked.connect(self.cancel_changes)
        self.file_list.file_selected.connect(self.load_image)
        self.preview_area.box_modified.connect(self.on_box_modified)
        self.info_panel.box_info_changed.connect(self.on_box_info_changed)
        self.info_panel.get_current_boxes = self.get_current_boxes

    def setup_shortcuts(self):
        self.undo_shortcut = QShortcut(QKeySequence.Undo, self)
        self.undo_shortcut.activated.connect(
            self.preview_area.undo_last_action)

    def on_box_modified(self):
        """
        update info panel when box is updated
        """
        if self.preview_area.selected_box is not None:
            box = self.preview_area.boxes[self.preview_area.selected_box]
            self.info_panel.update_box_info(box)
        else:
            self.info_panel.update_box_info(None)
        self.save_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def on_box_info_changed(self, new_box):
        """
        re-drawing box in preview area when info data in info panel
        is modified
        """
        if self.preview_area.selected_box is not None:
            self.preview_area.boxes[self.preview_area.selected_box] = new_box
            self.preview_area.draw_boxes()

    def save_changes(self):
        self.preview_area.save_changes()
        self.file_list.image_boxes[self.file_list.currentItem().text()] = \
            self.preview_area.original_boxes.copy()
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def cancel_changes(self):
        self.preview_area.cancel_changes()
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def load_image(self, image_path, boxes: List[Box]):
        self.preview_area.load_image(image_path, boxes)
        self.info_panel.update_image_info(image_path)

    def get_current_boxes(self):
        if self.file_list.currentItem():
            return self.preview_area.boxes
        return []
