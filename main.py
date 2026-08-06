import sys
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QFileDialog, QProgressBar, QTextEdit,
    QLabel, QRadioButton, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, QEvent

import geopandas as gpd

# ============================================================
# 1. THREAD KONVERSI
# ============================================================
class ConverterThread(QThread):
    progress = Signal(str)
    progress_bar = Signal(int)
    finished = Signal(bool)

    def __init__(self, main_files, file_pendukung, conversion_type, output_dir):
        super().__init__()
        self.main_files = main_files
        self.file_pendukung = file_pendukung   # dict: main_file -> list of supporting files
        self.conversion_type = conversion_type
        self.output_dir = output_dir

    def run(self):
        total = len(self.main_files)
        for idx, main_file in enumerate(self.main_files, 1):
            try:
                base_name = Path(main_file).stem
                self.progress.emit(f"[{idx}/{total}] Membaca: {Path(main_file).name}")

                # GeoPandas akan otomatis baca file pendukung jika ada di folder yang sama
                gdf = gpd.read_file(main_file)
                self.progress.emit(f"[{idx}/{total}] Konversi: {base_name}")

                # --- TAB → SHP ---
                if self.conversion_type == 'tab_to_shp':
                    output_path = os.path.join(self.output_dir, f"{base_name}.shp")
                    gdf.to_file(output_path, driver='ESRI Shapefile')
                    self.progress.emit(f"[{idx}/{total}] ✅ Berhasil: {base_name}.shp")

                # --- TAB → GeoJSON ---
                elif self.conversion_type == 'tab_to_geojson':
                    output_path = os.path.join(self.output_dir, f"{base_name}.geojson")
                    if gdf.crs is not None and gdf.crs != 'EPSG:4326':
                        gdf = gdf.to_crs('EPSG:4326')
                    gdf.to_file(output_path, driver='GeoJSON')
                    self.progress.emit(f"[{idx}/{total}] ✅ Berhasil: {base_name}.geojson")

                # --- SHP → GeoJSON ---
                elif self.conversion_type == 'shp_to_geojson':
                    output_path = os.path.join(self.output_dir, f"{base_name}.geojson")
                    if gdf.crs is not None and gdf.crs != 'EPSG:4326':
                        gdf = gdf.to_crs('EPSG:4326')
                    gdf.to_file(output_path, driver='GeoJSON')
                    self.progress.emit(f"[{idx}/{total}] ✅ Berhasil: {base_name}.geojson")

                self.progress_bar.emit(int((idx / total) * 100))

            except Exception as e:
                self.progress.emit(f"[{idx}/{total}] ❌ ERROR: {Path(main_file).name} - {str(e)}")

        self.progress.emit("🎉 Semua file selesai dikonversi!")
        self.finished.emit(True)


# ============================================================
# 2. MAIN WINDOW
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🗺️ GIS File Converter")
        self.setMinimumSize(700, 600)

        # State
        self.main_files = []                     # hanya file .tab atau .shp (tampil di UI)
        self.file_pendukung = {}                 # dict: main_file -> list of supporting files
        self.output_dir = ""
        self.conversion_type = "tab_to_shp"

        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Radio Button
        radio_layout = QHBoxLayout()
        self.radio_tab_shp = QRadioButton("TAB → SHP")
        self.radio_tab_geojson = QRadioButton("TAB → GeoJSON")
        self.radio_shp_geojson = QRadioButton("SHP → GeoJSON")
        self.radio_tab_shp.setChecked(True)

        self.radio_tab_shp.toggled.connect(self.on_conversion_changed)
        self.radio_tab_geojson.toggled.connect(self.on_conversion_changed)
        self.radio_shp_geojson.toggled.connect(self.on_conversion_changed)

        radio_layout.addWidget(self.radio_tab_shp)
        radio_layout.addWidget(self.radio_tab_geojson)
        radio_layout.addWidget(self.radio_shp_geojson)
        layout.addLayout(radio_layout)

        # Drop Zone
        self.file_list_widget = QListWidget()
        self.file_list_widget.setAcceptDrops(True)
        self.file_list_widget.setDragEnabled(True)
        self.file_list_widget.setMinimumHeight(150)
        self.file_list_widget.setStyleSheet("""
            QListWidget {
                border: 2px dashed #aaa;
                border-radius: 8px;
                padding: 10px;
                background: #ffffff;
            }
            QListWidget::item {
                color: #000000;
                background: #f0f0f0;
                padding: 4px;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background: #cce5ff;
                color: #000000;
            }
        """)
        self.file_list_widget.installEventFilter(self)
        layout.addWidget(self.file_list_widget)

        # Tombol File
        file_btn_layout = QHBoxLayout()
        btn_add_files = QPushButton("📂 Pilih File")
        btn_add_files.clicked.connect(self.add_files)
        btn_remove_selected = QPushButton("🗑️ Hapus Terpilih")
        btn_remove_selected.clicked.connect(self.remove_selected)
        btn_clear_all = QPushButton("🧹 Kosongkan")
        btn_clear_all.clicked.connect(self.clear_all)

        file_btn_layout.addWidget(btn_add_files)
        file_btn_layout.addWidget(btn_remove_selected)
        file_btn_layout.addWidget(btn_clear_all)
        layout.addLayout(file_btn_layout)

        # Output Folder
        output_layout = QHBoxLayout()
        self.lbl_output = QLabel("📁 Folder output: (belum dipilih)")
        btn_output = QPushButton("📂 Pilih Folder")
        btn_output.clicked.connect(self.select_output)
        output_layout.addWidget(self.lbl_output)
        output_layout.addWidget(btn_output)
        layout.addLayout(output_layout)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Log
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(150)
        layout.addWidget(self.log_area)

        # Aksi
        action_layout = QHBoxLayout()
        btn_convert = QPushButton("🚀 Konversi")
        btn_convert.clicked.connect(self.start_conversion)
        btn_open_output = QPushButton("📂 Buka Folder Output")
        btn_open_output.clicked.connect(self.open_output_folder)
        action_layout.addWidget(btn_convert)
        action_layout.addWidget(btn_open_output)
        layout.addLayout(action_layout)

        self.statusBar().showMessage("Ready")

    # ============================================================
    # 3. EVENT HANDLERS
    # ============================================================

    def eventFilter(self, obj, event):
        if obj == self.file_list_widget:
            if event.type() == QEvent.DragEnter:
                event.accept()
                return True
            elif event.type() == QEvent.DragMove:
                event.accept()
                return True
            elif event.type() == QEvent.Drop:
                urls = event.mimeData().urls()
                for url in urls:
                    file_path = url.toLocalFile()
                    if file_path:
                        self.add_single_file(file_path)
                event.accept()
                return True
        return super().eventFilter(obj, event)

    def on_conversion_changed(self):
        if self.radio_tab_shp.isChecked():
            self.conversion_type = "tab_to_shp"
        elif self.radio_tab_geojson.isChecked():
            self.conversion_type = "tab_to_geojson"
        elif self.radio_shp_geojson.isChecked():
            self.conversion_type = "shp_to_geojson"
        self.log_area.clear()
        self.statusBar().showMessage(f"Mode: {self.conversion_type}")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Pilih file GIS",
            "",
            "GIS Files (*.tab *.shp);;All Files (*.*)"   # <-- hanya tampilkan .tab dan .shp di dialog
        )
        for f in files:
            self.add_single_file(f)

    def add_single_file(self, file_path):
        """Hanya tampilkan file .tab atau .shp di UI; file pendukung disimpan di background."""
        ext = Path(file_path).suffix.lower()

        # Hanya proses jika ekstensi .tab atau .shp
        if ext not in ['.tab', '.shp']:
            return

        # Cegah duplikat
        if file_path in self.main_files:
            return

        # Tambahkan ke daftar utama
        self.main_files.append(file_path)
        self.file_list_widget.addItem(Path(file_path).name)

        # Cari dan simpan file pendukung (tanpa ditampilkan di UI)
        base_dir = os.path.dirname(file_path)
        base_name = Path(file_path).stem
        pendukung_list = []

        if ext == '.tab':
            for ext_pendukung in ['.dat', '.map', '.id', '.ind']:
                pendukung = os.path.join(base_dir, f"{base_name}{ext_pendukung}")
                if os.path.exists(pendukung):
                    pendukung_list.append(pendukung)
        elif ext == '.shp':
            for ext_pendukung in ['.shx', '.dbf', '.prj']:
                pendukung = os.path.join(base_dir, f"{base_name}{ext_pendukung}")
                if os.path.exists(pendukung):
                    pendukung_list.append(pendukung)

        self.file_pendukung[file_path] = pendukung_list
        self.statusBar().showMessage(f"{len(self.main_files)} file(s) dipilih | Mode: {self.conversion_type}")

    def remove_selected(self):
        selected = self.file_list_widget.currentRow()
        if selected >= 0:
            main_file = self.main_files.pop(selected)
            if main_file in self.file_pendukung:
                del self.file_pendukung[main_file]
            self.file_list_widget.takeItem(selected)

    def clear_all(self):
        self.main_files.clear()
        self.file_pendukung.clear()
        self.file_list_widget.clear()
        self.statusBar().showMessage("Semua file dihapus")

    def select_output(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Pilih folder output")
        if dir_path:
            self.output_dir = dir_path
            self.lbl_output.setText(f"📁 Folder output: {dir_path}")

    # ============================================================
    # 4. KONVERSI
    # ============================================================

    def start_conversion(self):
        if not self.main_files:
            QMessageBox.warning(self, "Error", "Belum ada file yang dipilih!")
            return
        if not self.output_dir:
            QMessageBox.warning(self, "Error", "Pilih folder output terlebih dahulu!")
            return

        # Filter file utama berdasarkan mode
        filtered_files = []
        for f in self.main_files:
            ext = Path(f).suffix.lower()
            if self.conversion_type in ['tab_to_shp', 'tab_to_geojson'] and ext == '.tab':
                filtered_files.append(f)
            elif self.conversion_type == 'shp_to_geojson' and ext == '.shp':
                filtered_files.append(f)

        if not filtered_files:
            QMessageBox.warning(
                self,
                "Error",
                f"Tidak ada file yang sesuai untuk {self.conversion_type}"
            )
            return

        # Jalankan thread
        self.thread = ConverterThread(
            filtered_files,
            self.file_pendukung,
            self.conversion_type,
            self.output_dir
        )
        self.thread.progress.connect(self.log_area.append)
        self.thread.progress_bar.connect(self.progress_bar.setValue)
        self.thread.finished.connect(self.on_conversion_finished)

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_area.clear()
        self.log_area.append(f"⏳ Memulai konversi {self.conversion_type}...")
        self.thread.start()

    def on_conversion_finished(self, success):
        self.progress_bar.setVisible(False)
        if success:
            self.log_area.append("✅ Konversi selesai!")
            QMessageBox.information(self, "Selesai", "Semua file berhasil dikonversi!")
        else:
            self.log_area.append("❌ Konversi gagal, cek log untuk detail.")

    def open_output_folder(self):
        if self.output_dir and os.path.exists(self.output_dir):
            os.system(f'xdg-open "{self.output_dir}"')
        else:
            QMessageBox.warning(self, "Error", "Folder output tidak ditemukan.")


# ============================================================
# 5. MAIN
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())