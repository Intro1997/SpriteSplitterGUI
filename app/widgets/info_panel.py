from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QGroupBox, QFormLayout, QMessageBox,
                               QPushButton, QFileDialog, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PIL import Image as PILImage
from sprite_splitter import Box
import os


class InfoPanel(QWidget):
    box_info_changed = Signal(tuple)

    def __init__(self, file_list):
        super().__init__()
        self._image_layout = QFormLayout()
        self.initUI()
        self.current_box: Box = None
        # returnPressed and editingFinished will
        # both trigger box info update. is_updating
        # is used to make sure we only update once
        self.is_updating = False
        self.image_width = 0
        self.image_height = 0
        self.current_image_path = None
        self.file_list = file_list

        self.origin_height_recorder = {}

    def resizeEvent(self, event):
        self.image_path_area.setMaximumHeight(
            self.get_label_font_height(self.image_path, self.image_path.text()))
        self.image_name_area.setMaximumHeight(
            self.get_label_font_height(self.image_name, self.image_name.text()))
        super().resizeEvent(event)

    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        """
        init image info panel
        """
        image_group = QGroupBox("Image Info")

        self._image_layout.setFieldGrowthPolicy(
            QFormLayout.AllNonFixedFieldsGrow)
        self._image_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._image_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignTop)

        # use fixed label width
        label_width = 60

        self.image_name_label = QLabel("Name:")
        self.image_path_label = QLabel("Path:")
        self.image_size_label = QLabel("Size:")
        self.image_mode_label = QLabel("Mode:")

        for label in [self.image_name_label, self.image_path_label,
                      self.image_size_label, self.image_mode_label]:
            label.setFixedWidth(label_width)
            label.setAlignment(Qt.AlignLeft)

        self.image_name = QLabel()
        self.image_path = QLabel()
        self.image_size = QLabel()
        self.image_mode = QLabel()

        for label in [self.image_name, self.image_path, self.image_size, self.image_mode]:
            label.setTextInteractionFlags(
                Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            # Set the mouse pointer to the text selection cursor
            label.setCursor(Qt.IBeamCursor)
            label.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.image_name.setWordWrap(True)
        self.image_path.setWordWrap(True)

        self.image_path_area = QScrollArea()
        self.image_path_area.setWidget(self.image_path)
        self.image_path_area.setWidgetResizable(True)
        self.image_path_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOn)
        self.image_path_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff)

        self.image_name_area = QScrollArea()
        self.image_name_area.setWidget(self.image_name)
        self.image_name_area.setWidgetResizable(True)
        self.image_name_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOn)
        self.image_name_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff)

        self.image_name_area.setMaximumHeight(0)
        self.image_path_area.setMaximumHeight(0)
        self.image_size.setMaximumHeight(0)
        self.image_mode.setMaximumHeight(0)
        self._image_layout.addRow(self.image_name_label, self.image_name_area)
        self._image_layout.addRow(self.image_path_label, self.image_path_area)
        self._image_layout.addRow(self.image_size_label, self.image_size)
        self._image_layout.addRow(self.image_mode_label, self.image_mode)

        image_group.setLayout(self._image_layout)
        layout.addWidget(image_group)

        """
        init box info panel
        """
        box_group = QGroupBox("Box Info")
        box_layout = QFormLayout()

        box_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        box_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        box_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        x_label = QLabel("x:")
        y_label = QLabel("y:")
        width_label = QLabel("Width:")
        height_label = QLabel("Height:")

        x_label.setToolTip(
            "This the x position of upper left point of current selected box")
        y_label.setToolTip(
            "This the y position of upper left point of current selected box")
        width_label.setToolTip("This is the width of current selected box")
        height_label.setToolTip("This is the height of current selected box")

        label_width = 45
        for label in [x_label, y_label, width_label, height_label]:
            label.setFixedWidth(label_width)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 改为左对齐

        self.x_edit = QLineEdit()
        self.y_edit = QLineEdit()
        self.width_edit = QLineEdit()
        self.height_edit = QLineEdit()

        box_layout.addRow(x_label, self.x_edit)
        box_layout.addRow(y_label, self.y_edit)
        box_layout.addRow(width_label, self.width_edit)
        box_layout.addRow(height_label, self.height_edit)

        box_group.setLayout(box_layout)
        layout.addWidget(box_group)

        """ 
        init export settings panel
        """
        export_group = QGroupBox("Export Settings")
        export_layout = QVBoxLayout()

        path_label = QLabel("Export Path:")
        self.export_path = QLineEdit()
        self.export_path.setPlaceholderText("Select export folder...")
        self.export_path.setReadOnly(True)

        button_layout = QHBoxLayout()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_export_path)
        self.export_button = QPushButton("Export")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_sprites)

        button_layout.addWidget(browse_button)
        button_layout.addWidget(self.export_button)
        button_layout.addStretch()

        export_layout.addWidget(path_label)
        export_layout.addWidget(self.export_path)
        export_layout.addLayout(button_layout)

        export_group.setLayout(export_layout)

        # set layout
        layout.addWidget(export_group)
        layout.addStretch()

        for edit in [self.x_edit, self.y_edit, self.width_edit, self.height_edit]:
            edit.setValidator(self.create_validator())
            edit.returnPressed.connect(self.on_value_changed)
            edit.editingFinished.connect(self.on_value_changed)

    def create_validator(self):
        # used in box info exitor
        from PySide6.QtGui import QIntValidator
        return QIntValidator(0, 99999)

    def get_label_font_height(self, label, font_str):
        font_metrics = QFontMetrics(self.image_path.font())
        return font_metrics.boundingRect(
            label.rect(), Qt.TextWordWrap, font_str).height()

    def update_image_info(self, image_path):
        self.current_image_path = image_path
        if not image_path:
            self.clear_image_info()
            return

        try:
            img = PILImage.open(image_path)
            self.image_name.setText(image_path.split('/')[-1])
            self.image_path.setText(image_path)
            self.image_size.setText(f"{img.width} x {img.height}")
            self.image_width = img.width
            self.image_height = img.height
            self.image_mode.setText(img.mode)

            fix_label_font = self.get_label_font_height(
                self.image_size, self.image_size.text())
            self.image_size.setMaximumHeight(fix_label_font)
            self.image_mode.setMaximumHeight(fix_label_font)

            self.image_path_area.setMaximumHeight(
                self.get_label_font_height(self.image_path, self.image_path.text()))
            self.image_name_area.setMaximumHeight(
                self.get_label_font_height(self.image_name, self.image_name.text()))

        except Exception as e:
            QMessageBox.warning(self, "Error loading image info: ", f"{e}")
            self.clear_image_info()

    def clear_image_info(self):
        self.image_name.setText("")
        self.image_path.setText("")
        self.image_size.setText("")
        self.image_mode.setText("")

    def update_box_info(self, box: Box):
        self.is_updating = True
        self.current_box = box

        if box is None:
            self.clear_box_info()
        else:
            width = box.right_bottom_corner[0] - box.left_top_corner[0] + 1
            height = box.right_bottom_corner[1] - box.left_top_corner[1] + 1
            self.x_edit.setText(str(int(box.left_top_corner[0])))
            self.y_edit.setText(str(int(box.left_top_corner[1])))
            self.width_edit.setText(str(int(abs(width))))
            self.height_edit.setText(str(int(abs(height))))

        self.is_updating = False

    def clear_box_info(self):
        self.current_box = None
        self.x_edit.setText("")
        self.y_edit.setText("")
        self.width_edit.setText("")
        self.height_edit.setText("")

    def on_value_changed(self):
        if self.is_updating or self.current_box is None:
            return

        try:
            x = int(self.x_edit.text() or 0)
            y = int(self.y_edit.text() or 0)
            width = int(self.width_edit.text() or 0)
            height = int(self.height_edit.text() or 0)

            if width <= 0 or height <= 0\
                    or x + width >= self.image_width\
                    or y + height >= self.image_height:
                self.update_box_info(self.current_box)
                return

            new_box = Box((x, y), (x + width, y + height))
            self.box_info_changed.emit(new_box)

        except ValueError:
            # restore if get invalid value
            self.update_box_info(self.current_box)

    def browse_export_path(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if path:
            self.export_path.setText(path)
            self.export_button.setEnabled(True)

    def get_current_boxes(self):
        if self.file_list is not None:
            return self.file_list.image_boxes
        return []

    def export_sprites(self):
        if not self.export_path.text() or not os.path.isdir(self.export_path.text()):
            QMessageBox.warning(self, "Invalid Path",
                                "Please select a valid export directory.")
            return

        if not self.current_image_path:
            QMessageBox.warning(
                self, "No Image", "Please select an image first.")
            return

        try:
            image = PILImage.open(self.current_image_path)
            base_name = os.path.splitext(
                os.path.basename(self.current_image_path))[0]

            boxes = self.get_current_boxes()

            if boxes is None or len(boxes) < 1:
                QMessageBox.warning(
                    self, "Export sprites failed!", "Length of boxes is zero, no need to split.")

            for i, box in enumerate(boxes):
                left, top = box.left_top_corner
                right, bottom = box.right_bottom_corner
                sprite = image.crop((left, top, right + 1, bottom + 1))

                output_path = os.path.join(
                    self.export_path.text(),
                    f"{base_name}_sprite_{i}.png"
                )
                sprite.save(output_path, "PNG")

            QMessageBox.information(
                self,
                "Export Successful",
                f"Successfully exported {len(boxes)} sprites."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export sprites: {str(e)}"
            )
