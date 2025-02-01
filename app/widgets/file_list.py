from PySide6.QtWidgets import QListWidget, QMessageBox
from PySide6.QtCore import Signal
from PIL import Image
from sprite_splitter import AlphaSpriteSplitter


class FileListWidget(QListWidget):
    file_selected = Signal(str, list)

    def __init__(self):
        super().__init__()
        self.files = []
        self.itemClicked.connect(self.on_item_clicked)
        self._sprite_splitters = {}
        self.image_boxes = {}

    def add_files(self, file_paths):
        failed_files = []
        new_file = 0
        old_index = -1
        for path in file_paths:
            if path in self.files:
                old_index = self.files.index(path)
                continue
            else:
                new_file += 1
            try:
                Image.open(path)
                self.files.append(path)
                self.addItem(path)
            except Exception:
                failed_files.append(path)

        if failed_files:
            QMessageBox.warning(
                self,
                "Failed to open files",
                f"The following files could not be opened:\n{
                    '\n'.join(failed_files)}"
            )

        # choose the last valid file
        if new_file == 0:
            self.setCurrentRow(old_index)
            self.on_item_clicked(self.item(old_index))
        else:
            file_cnt = self.count()
            if file_cnt > 0 and self.currentItem() is not file_cnt - 1:
                self.setCurrentRow(file_cnt - 1)
                self.on_item_clicked(self.item(file_cnt - 1))

    def on_item_clicked(self, item):
        try:
            img_file_path = item.text()
            if not self._sprite_splitters.get(img_file_path):
                self._sprite_splitters[img_file_path] = AlphaSpriteSplitter(
                    img_file_path)
            if not self.image_boxes.get(img_file_path):
                self.image_boxes[img_file_path] = \
                    self._sprite_splitters[img_file_path].get_sprite_boxes()

            boxes = self.image_boxes[img_file_path]
            self.file_selected.emit(img_file_path, boxes)
        except Exception as e:
            QMessageBox.warning(self, "Open select file failed: ", f"{e}")
