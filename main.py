import sys
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QProgressBar,
    QTextEdit, QLabel, QComboBox, QLineEdit, QGroupBox, QMessageBox,
    QListView, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices

import geopandas as gpd
import pandas as pd
import shapely.wkt

# ============================================================
# DRIVER & EXTENSION CONFIGURATION
# ============================================================
SUPPORTED_INPUT_EXTS = {
    '.shp': 'ESRI Shapefile',
    '.tab': 'MapInfo File',
    '.mif': 'MapInfo File',
    '.geojson': 'GeoJSON',
    '.json': 'GeoJSON',
    '.gpkg': 'GeoPackage',
    '.kml': 'KML',
    '.kmz': 'KMZ',
    '.gpx': 'GPX',
    '.dxf': 'DXF',
    '.fgb': 'FlatGeobuf',
    '.csv': 'CSV (Coordinates / WKT)',
    '.zip': 'ZIP Archive (Shapefile/GIS)'
}

OUTPUT_FORMATS = {
    'GeoJSON (.geojson)': {
        'ext': '.geojson',
        'driver': 'GeoJSON',
        'default_crs': 'EPSG:4326'
    },
    'ESRI Shapefile (.shp)': {
        'ext': '.shp',
        'driver': 'ESRI Shapefile',
        'default_crs': None
    },
    'GeoPackage (.gpkg)': {
        'ext': '.gpkg',
        'driver': 'GPKG',
        'default_crs': None
    },
    'MapInfo TAB (.tab)': {
        'ext': '.tab',
        'driver': 'MapInfo File',
        'default_crs': None
    },
    'KML (.kml)': {
        'ext': '.kml',
        'driver': 'KML',
        'default_crs': 'EPSG:4326'
    },
    'FlatGeobuf (.fgb)': {
        'ext': '.fgb',
        'driver': 'FlatGeobuf',
        'default_crs': None
    },
    'CSV with WKT Geometry (.csv)': {
        'ext': '.csv',
        'driver': 'CSV',
        'default_crs': None
    }
}

CRS_PRESETS = [
    ("Biarkan Asli (Keep Original)", None),
    ("WGS 84 (EPSG:4326 - Derajat Desimal / GPS / GeoJSON)", "EPSG:4326"),
    ("Web Mercator (EPSG:3857 - Google Maps / OSM)", "EPSG:3857"),
    ("Indonesia UTM Zone 46S (EPSG:32746 - Aceh, Sumbar)", "EPSG:32746"),
    ("Indonesia UTM Zone 47S (EPSG:32747 - Sumut, Riau, Jambi)", "EPSG:32747"),
    ("Indonesia UTM Zone 48S (EPSG:32748 - Sumsel, Lampung, Jabar, Jakarta)", "EPSG:32748"),
    ("Indonesia UTM Zone 49S (EPSG:32749 - Jateng, DIY, Jatim, Bali, NTB Barat)", "EPSG:32749"),
    ("Indonesia UTM Zone 50S (EPSG:32750 - NTB Timur, NTT Barat, Kalsel, Kaltim)", "EPSG:32750"),
    ("Indonesia UTM Zone 51S (EPSG:32751 - NTT Timur, Sulsel, Sulbar, Sulteng)", "EPSG:32751"),
    ("Indonesia UTM Zone 52S (EPSG:32752 - Sultra, Maluku, Papua Barat)", "EPSG:32752"),
    ("Indonesia UTM Zone 53S (EPSG:32753 - Papua Tengah)", "EPSG:32753"),
    ("Indonesia UTM Zone 54S (EPSG:32754 - Papua Timur)", "EPSG:32754"),
    ("Custom EPSG Code...", "CUSTOM")
]


# ============================================================
# HELPER FUNCTIONS UNTUK PEMBACAAN & PENULISAN GIS
# ============================================================
def extract_zip_layers(zip_path, temp_dir):
    """Mengekstrak file ZIP dan mengembalikan list file GIS utama yang ditemukan."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    found_files = []
    for root, _, files in os.walk(temp_dir):
        for f in files:
            ext = Path(f).suffix.lower()
            if ext in ['.shp', '.tab', '.geojson', '.gpkg', '.kml', '.gpx', '.fgb']:
                found_files.append(os.path.join(root, f))
    return found_files


def read_gis_file(file_path, encoding=None):
    """Membaca file GIS menggunakan pyogrio / geopandas / pandas secara fleksibel."""
    ext = Path(file_path).suffix.lower()

    # 1. KMZ Handling
    if ext == '.kmz':
        temp_kmz_dir = tempfile.mkdtemp(prefix="gis_kmz_")
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_kmz_dir)
            kml_files = [os.path.join(r, f) for r, _, fs in os.walk(temp_kmz_dir) for f in fs if f.endswith('.kml')]
            if not kml_files:
                raise ValueError("Tidak ada file KML di dalam arsip KMZ.")
            gdf = gpd.read_file(kml_files[0])
            return gdf
        finally:
            shutil.rmtree(temp_kmz_dir, ignore_errors=True)

    # 2. CSV Handling
    if ext == '.csv':
        df = pd.read_csv(file_path, encoding=encoding or 'utf-8')
        wkt_col = next((col for col in df.columns if col.lower() in ['wkt', 'geom', 'geometry', 'the_geom']), None)
        if wkt_col:
            df['geometry'] = df[wkt_col].apply(lambda x: shapely.wkt.loads(str(x)) if pd.notnull(x) else None)
            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:4326")
            return gdf

        lon_col = next((c for c in df.columns if c.lower() in ['lon', 'longitude', 'lng', 'x', 'bujur']), None)
        lat_col = next((c for c in df.columns if c.lower() in ['lat', 'latitude', 'y', 'lintang']), None)
        if lon_col and lat_col:
            gdf = gpd.GeoDataFrame(
                df,
                geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
                crs="EPSG:4326"
            )
            return gdf
        raise ValueError("File CSV tidak memiliki kolom koordinat (lon/lat) atau geometri WKT.")

    # 3. GPX Handling
    if ext == '.gpx':
        for layer in ['tracks', 'waypoints', 'routes', 'track_points']:
            try:
                gdf = gpd.read_file(file_path, layer=layer)
                if not gdf.empty:
                    return gdf
            except Exception:
                continue
        return gpd.read_file(file_path)

    # 4. Standard GIS (SHP, TAB, GeoJSON, GPKG, KML, FlatGeobuf, DXF)
    try:
        kwargs = {}
        if encoding:
            kwargs['encoding'] = encoding
        return gpd.read_file(file_path, engine="pyogrio", **kwargs)
    except Exception:
        return gpd.read_file(file_path)


def sanitize_for_shapefile(gdf):
    """Sanitasi kolom dan geometri agar sesuai dengan spesifikasi ESRI Shapefile."""
    gdf = gdf.copy()

    for col in gdf.columns:
        if pd.api.types.is_datetime64_any_dtype(gdf[col]):
            gdf[col] = gdf[col].astype(str)

    geom_types = gdf.geometry.geom_type.dropna().unique()
    if len(geom_types) > 1:
        dominant_type = gdf.geometry.geom_type.value_counts().index[0]
        gdf = gdf[gdf.geometry.geom_type == dominant_type]

    return gdf


# ============================================================
# THREAD KONVERSI
# ============================================================
class ConverterThread(QThread):
    progress = Signal(str)
    progress_bar = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, input_files, target_format_key, target_crs, encoding, output_dir):
        super().__init__()
        self.input_files = input_files
        self.target_format_key = target_format_key
        self.target_crs = target_crs
        self.encoding = encoding
        self.output_dir = output_dir
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        format_info = OUTPUT_FORMATS.get(self.target_format_key)
        if not format_info:
            self.progress.emit("[ERROR] Format output tidak valid.")
            self.finished.emit(False, "Format output tidak dikenali.")
            return

        target_ext = format_info['ext']
        target_driver = format_info['driver']
        force_crs = format_info.get('default_crs')

        total_files = len(self.input_files)
        success_count = 0
        fail_count = 0

        self.progress.emit(f"Memulai konversi {total_files} file ke format {self.target_format_key}...\n")

        for idx, file_path in enumerate(self.input_files, 1):
            if self._is_cancelled:
                self.progress.emit("\n[BATAL] Proses konversi dibatalkan oleh pengguna.")
                self.finished.emit(False, "Dibatalkan oleh pengguna.")
                return

            file_p = Path(file_path)
            base_name = file_p.stem
            self.progress.emit(f"[{idx}/{total_files}] Memproses: {file_p.name}")

            temp_extract_dir = None
            try:
                if file_p.suffix.lower() == '.zip':
                    temp_extract_dir = tempfile.mkdtemp(prefix="gis_zip_")
                    sub_files = extract_zip_layers(file_path, temp_extract_dir)
                    if not sub_files:
                        raise ValueError("Tidak ditemukan file GIS (.shp, .tab, .gpkg, dll) di dalam ZIP.")
                    read_target = sub_files[0]
                    self.progress.emit(f"   Ditemukan layer di ZIP: {Path(read_target).name}")
                else:
                    read_target = file_path

                gdf = read_gis_file(read_target, encoding=self.encoding)
                if gdf is None or gdf.empty:
                    raise ValueError("Layer kosong atau tidak memiliki data geometri valid.")

                feature_count = len(gdf)
                geom_types = ", ".join(gdf.geometry.geom_type.dropna().unique())
                curr_crs = str(gdf.crs) if gdf.crs else "Tidak terdefinisi"
                self.progress.emit(f"   Info Data: {feature_count} fitur | Tipe: {geom_types} | CRS: {curr_crs}")

                final_crs = self.target_crs or force_crs
                if final_crs:
                    if gdf.crs is None:
                        self.progress.emit(f"   Menetapkan CRS: {final_crs}...")
                        gdf = gdf.set_crs(final_crs, allow_override=True)
                    elif str(gdf.crs).upper() != str(final_crs).upper():
                        self.progress.emit(f"   Reproyeksi CRS ke: {final_crs}...")
                        gdf = gdf.to_crs(final_crs)

                output_path = os.path.join(self.output_dir, f"{base_name}{target_ext}")

                if target_driver == 'CSV':
                    df_out = gdf.copy()
                    df_out['wkt_geom'] = df_out.geometry.apply(lambda g: g.wkt if g is not None else "")
                    if all(gdf.geometry.geom_type == 'Point'):
                        df_out['longitude'] = gdf.geometry.x
                        df_out['latitude'] = gdf.geometry.y
                    df_out.drop(columns=['geometry'], inplace=True, errors='ignore')
                    df_out.to_csv(output_path, index=False, encoding='utf-8')

                elif target_driver == 'ESRI Shapefile':
                    gdf = sanitize_for_shapefile(gdf)
                    gdf.to_file(output_path, driver=target_driver, engine="pyogrio")

                elif target_driver == 'KML':
                    if gdf.crs is None or str(gdf.crs) != 'EPSG:4326':
                        gdf = gdf.to_crs('EPSG:4326')
                    try:
                        gdf.to_file(output_path, driver='KML', engine='fiona')
                    except Exception:
                        gdf.to_file(output_path, driver='LIBKML')

                else:
                    try:
                        gdf.to_file(output_path, driver=target_driver, engine="pyogrio")
                    except Exception:
                        gdf.to_file(output_path, driver=target_driver)

                self.progress.emit(f"   [OK] Tersimpan: {Path(output_path).name}\n")
                success_count += 1

            except Exception as e:
                self.progress.emit(f"   [GAGAL] {str(e)}\n")
                fail_count += 1
            finally:
                if temp_extract_dir and os.path.exists(temp_extract_dir):
                    shutil.rmtree(temp_extract_dir, ignore_errors=True)

            self.progress_bar.emit(int((idx / total_files) * 100))

        summary = f"Selesai: {success_count} berhasil, {fail_count} gagal dari total {total_files} file."
        self.progress.emit("=" * 60)
        self.progress.emit(summary)
        self.finished.emit(success_count > 0, summary)


# ============================================================
# MAIN WINDOW UI
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal GIS Vector Converter")
        self.resize(960, 840)
        self.setMinimumSize(800, 680)

        self.input_files = []
        self.output_dir = ""
        self.thread = None

        self.init_ui()
        self.apply_styles()

    def _setup_combobox(self, combo):
        view = QListView()
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        view.setAutoFillBackground(True)
        combo.setView(view)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # Header Title
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        lbl_title = QLabel("Universal GIS Vector Converter")
        lbl_title.setObjectName("headerTitle")

        lbl_subtitle = QLabel("Konversi multi-format spasial: TAB, SHP, GeoJSON, GeoPackage, KML/KMZ, GPX, DXF, CSV, dan FlatGeobuf.")
        lbl_subtitle.setObjectName("headerSubtitle")

        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        main_layout.addWidget(header_widget, stretch=0)

        # ----------------------------------------------------
        # 1. GROUP BOX: INPUT FILES (DROP ZONE)
        # ----------------------------------------------------
        group_input = QGroupBox("1. File Input (Drag and Drop / Pilih File / Arsip ZIP)")
        layout_input = QVBoxLayout(group_input)
        layout_input.setSpacing(10)

        self.file_list_widget = QListWidget()
        self.file_list_widget.setAcceptDrops(True)
        self.file_list_widget.setDragEnabled(True)
        self.file_list_widget.setMinimumHeight(170)
        self.file_list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.file_list_widget.installEventFilter(self)
        layout_input.addWidget(self.file_list_widget, stretch=1)

        # Tombol File Input
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        btn_add = QPushButton("Tambah File / ZIP")
        btn_add.clicked.connect(self.add_files_dialog)
        btn_add_folder = QPushButton("Tambah Folder")
        btn_add_folder.clicked.connect(self.add_folder_dialog)
        btn_del = QPushButton("Hapus Pilihan")
        btn_del.clicked.connect(self.remove_selected)
        btn_clear = QPushButton("Kosongkan Daftar")
        btn_clear.clicked.connect(self.clear_all)

        btn_box.addWidget(btn_add)
        btn_box.addWidget(btn_add_folder)
        btn_box.addWidget(btn_del)
        btn_box.addWidget(btn_clear)
        layout_input.addLayout(btn_box)

        main_layout.addWidget(group_input, stretch=3)

        # ----------------------------------------------------
        # 2. GROUP BOX: PENGATURAN TARGET & CRS
        # ----------------------------------------------------
        group_settings = QGroupBox("2. Pengaturan Target dan Sistem Koordinat (CRS)")
        layout_settings = QVBoxLayout(group_settings)
        layout_settings.setSpacing(10)

        # Target Format Row
        row_target = QHBoxLayout()
        lbl_target = QLabel("Format Output:")
        lbl_target.setFixedWidth(160)
        self.combo_target = QComboBox()
        self._setup_combobox(self.combo_target)
        for key in OUTPUT_FORMATS.keys():
            self.combo_target.addItem(key)
        row_target.addWidget(lbl_target)
        row_target.addWidget(self.combo_target)
        layout_settings.addLayout(row_target)

        # CRS Reprojection Row
        row_crs = QHBoxLayout()
        lbl_crs = QLabel("Sistem Koordinat (CRS):")
        lbl_crs.setFixedWidth(160)
        self.combo_crs = QComboBox()
        self._setup_combobox(self.combo_crs)
        for label, val in CRS_PRESETS:
            self.combo_crs.addItem(label, val)
        self.combo_crs.currentIndexChanged.connect(self.on_crs_changed)

        self.txt_custom_epsg = QLineEdit()
        self.txt_custom_epsg.setPlaceholderText("Contoh: EPSG:32748 atau 4326")
        self.txt_custom_epsg.setVisible(False)
        self.txt_custom_epsg.setFixedWidth(200)

        row_crs.addWidget(lbl_crs)
        row_crs.addWidget(self.combo_crs)
        row_crs.addWidget(self.txt_custom_epsg)
        layout_settings.addLayout(row_crs)

        # Encoding Row
        row_enc = QHBoxLayout()
        lbl_enc = QLabel("Encoding Atribut:")
        lbl_enc.setFixedWidth(160)
        self.combo_enc = QComboBox()
        self._setup_combobox(self.combo_enc)
        self.combo_enc.addItem("Auto-Detect / UTF-8", "utf-8")
        self.combo_enc.addItem("Windows-1252 / CP1252 (Shapefile Lama)", "cp1252")
        self.combo_enc.addItem("ISO-8859-1 / Latin-1", "latin1")
        row_enc.addWidget(lbl_enc)
        row_enc.addWidget(self.combo_enc)
        layout_settings.addLayout(row_enc)

        main_layout.addWidget(group_settings, stretch=0)

        # ----------------------------------------------------
        # 3. GROUP BOX: FOLDER OUTPUT & EKSEKUSI
        # ----------------------------------------------------
        group_out = QGroupBox("3. Folder Output dan Eksekusi")
        layout_out = QVBoxLayout(group_out)
        layout_out.setSpacing(10)

        row_folder = QHBoxLayout()
        self.lbl_output = QLabel("Folder Output: (Belum dipilih)")
        self.lbl_output.setObjectName("lblOutput")
        btn_sel_output = QPushButton("Pilih Folder Output")
        btn_sel_output.clicked.connect(self.select_output_dir)
        row_folder.addWidget(self.lbl_output, stretch=1)
        row_folder.addWidget(btn_sel_output)
        layout_out.addLayout(row_folder)

        # Tombol Aksi
        row_actions = QHBoxLayout()
        row_actions.setSpacing(8)
        self.btn_convert = QPushButton("Mulai Konversi")
        self.btn_convert.setObjectName("btnConvert")
        self.btn_convert.clicked.connect(self.start_conversion)

        self.btn_cancel = QPushButton("Batalkan")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_conversion)

        self.btn_open_out = QPushButton("Buka Folder Hasil")
        self.btn_open_out.clicked.connect(self.open_output_folder)

        row_actions.addWidget(self.btn_convert)
        row_actions.addWidget(self.btn_cancel)
        row_actions.addWidget(self.btn_open_out)
        layout_out.addLayout(row_actions)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        layout_out.addWidget(self.progress_bar)

        main_layout.addWidget(group_out, stretch=0)

        # ----------------------------------------------------
        # 4. LOG CONSOLE
        # ----------------------------------------------------
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(140)
        self.log_area.setPlaceholderText("Log proses konversi akan muncul di sini...")
        main_layout.addWidget(self.log_area, stretch=2)

        self.statusBar().showMessage("Siap. Silakan pilih atau drop file GIS.")

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                color: #111827;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                font-size: 13px;
            }
            QMainWindow {
                background-color: #f3f4f6;
            }
            #headerTitle {
                font-size: 18px;
                font-weight: 700;
                color: #111827;
            }
            #headerSubtitle {
                font-size: 12px;
                color: #4b5563;
            }
            QGroupBox {
                font-size: 13px;
                font-weight: 600;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 14px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #111827;
            }
            QLabel {
                color: #111827;
                font-size: 13px;
            }
            #lblOutput {
                color: #1f2937;
                font-weight: 500;
            }
            QListWidget {
                border: 2px dashed #9ca3af;
                border-radius: 6px;
                padding: 6px;
                background-color: #fafafa;
                color: #111827;
            }
            QListWidget::item {
                background: #ffffff;
                color: #111827;
                padding: 6px 10px;
                margin: 2px 0;
                border: 1px solid #e5e7eb;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #dbeafe;
                border: 1px solid #93c5fd;
                color: #1e40af;
            }
            QPushButton {
                background-color: #f3f4f6;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
                border-color: #9ca3af;
            }
            QPushButton:pressed {
                background-color: #d1d5db;
            }
            QPushButton:disabled {
                background-color: #f3f4f6;
                color: #9ca3af;
                border-color: #e5e7eb;
            }
            #btnConvert {
                background-color: #2563eb;
                color: #ffffff;
                border: 1px solid #1d4ed8;
                font-weight: 600;
            }
            #btnConvert:hover {
                background-color: #1d4ed8;
            }
            #btnConvert:pressed {
                background-color: #1e40af;
            }
            #btnConvert:disabled {
                background-color: #93c5fd;
                color: #eff6ff;
                border-color: #93c5fd;
            }
            #btnCancel {
                background-color: #fee2e2;
                color: #991b1b;
                border: 1px solid #fca5a5;
                font-weight: 500;
            }
            #btnCancel:hover {
                background-color: #fecaca;
            }
            #btnCancel:disabled {
                background-color: #f3f4f6;
                color: #9ca3af;
                border-color: #e5e7eb;
            }
            QComboBox {
                combobox-popup: 0;
                background-color: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 5px;
                padding: 7px 12px;
                min-height: 24px;
            }
            QComboBox:hover {
                border-color: #9ca3af;
            }
            QComboBox:focus {
                border-color: #2563eb;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left-width: 0px;
                background: transparent;
            }
            QComboBox QAbstractItemView,
            QComboBox QListView {
                background-color: #ffffff;
                color: #111827;
                selection-background-color: #dbeafe;
                selection-color: #1e40af;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                outline: 0px;
                padding: 2px 0px;
                margin: 0px;
            }
            QComboBox QAbstractItemView::item,
            QComboBox QListView::item {
                min-height: 28px;
                padding: 4px 10px;
                border: none;
                margin: 0px;
                color: #111827;
                background-color: #ffffff;
            }
            QComboBox QAbstractItemView::item:hover,
            QComboBox QListView::item:hover {
                background-color: #f3f4f6;
                color: #111827;
            }
            QComboBox QAbstractItemView::item:selected,
            QComboBox QListView::item:selected {
                background-color: #dbeafe;
                color: #1e40af;
            }
            QLineEdit {
                background-color: #ffffff;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 5px;
                padding: 5px 8px;
            }
            QProgressBar {
                border: 1px solid #d1d5db;
                border-radius: 5px;
                text-align: center;
                background-color: #e5e7eb;
                color: #111827;
                font-weight: 600;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #111827;
                color: #f9fafb;
                font-family: "JetBrains Mono", "Fira Code", Consolas, monospace;
                font-size: 12px;
                border: 1px solid #374151;
                border-radius: 6px;
                padding: 8px;
            }
            QStatusBar {
                color: #374151;
                background-color: #e5e7eb;
                font-size: 12px;
                font-weight: 500;
            }
        """)

    # ============================================================
    # EVENT HANDLERS & FILE MANAGEMENT
    # ============================================================
    def eventFilter(self, obj, event):
        if obj == self.file_list_widget:
            if event.type() == event.Type.DragEnter or event.type() == event.Type.DragMove:
                event.accept()
                return True
            elif event.type() == event.Type.Drop:
                urls = event.mimeData().urls()
                for url in urls:
                    local_path = url.toLocalFile()
                    if local_path:
                        if os.path.isdir(local_path):
                            self.add_directory_recursive(local_path)
                        else:
                            self.add_single_file(local_path)
                event.accept()
                return True
        return super().eventFilter(obj, event)

    def on_crs_changed(self):
        val = self.combo_crs.currentData()
        self.txt_custom_epsg.setVisible(val == "CUSTOM")

    def add_files_dialog(self):
        ext_filter = "Format GIS (*.shp *.tab *.mif *.geojson *.json *.gpkg *.kml *.kmz *.gpx *.dxf *.fgb *.csv *.zip);;All Files (*.*)"
        files, _ = QFileDialog.getOpenFileNames(self, "Pilih File GIS", "", ext_filter)
        for f in files:
            self.add_single_file(f)

    def add_folder_dialog(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Pilih Folder GIS")
        if dir_path:
            self.add_directory_recursive(dir_path)

    def add_directory_recursive(self, dir_path):
        for root, _, files in os.walk(dir_path):
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in SUPPORTED_INPUT_EXTS:
                    self.add_single_file(os.path.join(root, f))

    def add_single_file(self, file_path):
        file_p = Path(file_path)
        ext = file_p.suffix.lower()

        if ext in ['.shx', '.dbf', '.prj', '.cpg', '.qpj', '.dat', '.map', '.id', '.ind']:
            return

        if ext not in SUPPORTED_INPUT_EXTS:
            return

        if file_path in self.input_files:
            return

        self.input_files.append(file_path)
        size_kb = os.path.getsize(file_path) / 1024
        size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"
        format_name = SUPPORTED_INPUT_EXTS.get(ext, ext.upper())

        item = QListWidgetItem(f"{file_p.name}   [{format_name}]   ({size_str})")
        item.setToolTip(file_path)
        self.file_list_widget.addItem(item)
        self.statusBar().showMessage(f"Total: {len(self.input_files)} file terpilih")

    def remove_selected(self):
        for item in self.file_list_widget.selectedItems():
            row = self.file_list_widget.row(item)
            self.file_list_widget.takeItem(row)
            self.input_files.pop(row)
        self.statusBar().showMessage(f"Total: {len(self.input_files)} file terpilih")

    def clear_all(self):
        self.input_files.clear()
        self.file_list_widget.clear()
        self.statusBar().showMessage("Daftar file dikosongkan.")

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Pilih Folder Output")
        if dir_path:
            self.output_dir = dir_path
            self.lbl_output.setText(f"Folder Output: {dir_path}")

    # ============================================================
    # EXECUTION & THREAD MANAGEMENT
    # ============================================================
    def start_conversion(self):
        if not self.input_files:
            QMessageBox.warning(self, "Peringatan", "Belum ada file yang dipilih!")
            return
        if not self.output_dir:
            QMessageBox.warning(self, "Peringatan", "Pilih folder output terlebih dahulu!")
            return

        crs_val = self.combo_crs.currentData()
        if crs_val == "CUSTOM":
            custom_code = self.txt_custom_epsg.text().strip()
            if not custom_code:
                QMessageBox.warning(self, "Peringatan", "Masukkan kode EPSG kustom (misal EPSG:32748)!")
                return
            if not custom_code.upper().startswith("EPSG:") and custom_code.isdigit():
                custom_code = f"EPSG:{custom_code}"
            target_crs = custom_code
        else:
            target_crs = crs_val

        target_format = self.combo_target.currentText()
        encoding = self.combo_enc.currentData()

        self.btn_convert.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_area.clear()

        self.thread = ConverterThread(
            input_files=list(self.input_files),
            target_format_key=target_format,
            target_crs=target_crs,
            encoding=encoding,
            output_dir=self.output_dir
        )
        self.thread.progress.connect(self.log_area.append)
        self.thread.progress_bar.connect(self.progress_bar.setValue)
        self.thread.finished.connect(self.on_conversion_finished)
        self.thread.start()

    def cancel_conversion(self):
        if self.thread and self.thread.isRunning():
            self.thread.cancel()
            self.log_area.append("[BATAL] Mengirim sinyal pembatalan...")

    def on_conversion_finished(self, success, message):
        self.btn_convert.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage(message)

        if success:
            QMessageBox.information(self, "Konversi Selesai", message)
        else:
            QMessageBox.warning(self, "Info Konversi", message)

    def open_output_folder(self):
        if self.output_dir and os.path.exists(self.output_dir):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_dir))
        else:
            QMessageBox.warning(self, "Error", "Folder output belum dipilih atau tidak ditemukan.")


# ============================================================
# MAIN ENTRYPOINT
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())