# 🗺️ Universal GIS Vector Converter Desktop

Aplikasi desktop modern berbasis Python dan PySide6 untuk konversi multi-arah (*Any-to-Any*) berbagai format data spasial/GIS vektor dengan dukungan sistem koordinat (CRS) kustom dan akselerasi performa tinggi.

---

## ✨ Fitur Unggulan

- **Dukungan Format Luas (Any-to-Any)**:
  - **Input**: Shapefile (`.shp`), MapInfo (`.tab`, `.mif`), GeoJSON (`.geojson`, `.json`), GeoPackage (`.gpkg`), KML/KMZ (`.kml`, `.kmz`), GPX (`.gpx`), AutoCAD DXF (`.dxf`), FlatGeobuf (`.fgb`), CSV (`.csv` dengan koordinat lon/lat atau WKT), serta **Arsip ZIP (`.zip`)**.
  - **Output**: GeoJSON, ESRI Shapefile, GeoPackage (`.gpkg`), MapInfo TAB, KML, FlatGeobuf, dan CSV (WKT).
- **Auto-Detect Arsip ZIP**: Drag & drop file `.zip` (misal arsip Shapefile lengkap) langsung diproses secara otomatis.
- **Sistem Koordinat (CRS) & Reprojection**:
  - Pertahankan CRS Asli (*Keep Original*).
  - WGS 84 (`EPSG:4326`) untuk GPS / Web GeoJSON.
  - Web Mercator (`EPSG:3857`) untuk peta online (Google Maps, OSM).
  - Preset UTM Indonesia (Zone 46S s/d 54S).
  - Custom EPSG code input.
- **Dukungan Encoding Atribut**: UTF-8, Windows-1252 / CP1252 (untuk Shapefile lawas), dan ISO-8859-1.
- **Performa Cepat**: Didukung oleh engine `pyogrio` & `GDAL` untuk pembacaan dan penulisan dataset besar.
- **Cross-Platform**: Menggunakan Qt Desktop Services untuk membuka folder hasil di Linux, Windows, maupun macOS.
- **Fitur Batal / Cancel**: Pembatalan proses batch di tengah jalan tanpa membuat aplikasi hang.

---

## 🛠️ Prasyarat & Instalasi

### 1. Prasyarat Sistem
- Python 3.10+ (direkomendasikan Python 3.12)
- Linux / Windows / macOS

### 2. Setup Virtual Environment

1. Masuk ke direktori project:
   ```bash
   cd /home/lenovo/Projects/Geojson-converter
   ```

2. Buat virtual environment:
   ```bash
   python3 -m venv venv_gis
   ```

3. Aktifkan virtual environment:
   - **Linux / macOS**:
     ```bash
     source venv_gis/bin/activate
     ```
   - **Windows**:
     ```cmd
     venv_gis\Scripts\activate
     ```

4. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 🚀 Menjalankan Aplikasi

Pastikan virtual environment telah aktif, lalu jalankan:

```bash
python main.py
```

### Cara Penggunaan:
1. **Pilih File Input**: Drag & drop file atau klik tombol **Tambah File / ZIP** atau **Tambah Folder**.
2. **Atur Target & CRS**:
   - Pilih format output target (misal GeoJSON, GPKG, Shapefile, KML, dll).
   - Pilih target CRS (misal WGS 84 `EPSG:4326` atau UTM Zone).
   - Pilih encoding atribut bila diperlukan.
3. **Pilih Folder Output**: Tentukan folder penyimpanan hasil.
4. **Mulai Konversi**: Klik **Mulai Konversi**. Log status dan progress bar akan memantau proses secara *real-time*.

---

## 📦 Format File yang Didukung

| Format | Ekstensi Input | Driver Output |
| :--- | :--- | :--- |
| **ESRI Shapefile** | `.shp`, `.zip` | `ESRI Shapefile` |
| **MapInfo** | `.tab`, `.mif` | `MapInfo File` |
| **GeoJSON** | `.geojson`, `.json` | `GeoJSON` |
| **GeoPackage** | `.gpkg` | `GPKG` |
| **Google Earth KML/KMZ** | `.kml`, `.kmz` | `KML` |
| **GPS Exchange** | `.gpx` | - |
| **AutoCAD DXF** | `.dxf` | - |
| **FlatGeobuf** | `.fgb` | `FlatGeobuf` |
| **CSV Coordinates / WKT**| `.csv` | `CSV` (with WKT) |
| **Arsip ZIP** | `.zip` | Diekstrak otomatis |
