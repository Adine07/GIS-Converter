# Universal GIS Vector Converter Desktop

A modern desktop application built with Python and PySide6 for multi-directional (Any-to-Any) conversion of various spatial/GIS vector data formats with support for custom coordinate reference systems (CRS) and high-performance acceleration.

---

## Key Features

- **Comprehensive Format Support (Any-to-Any)**:
  - **Input**: Shapefile (`.shp`), MapInfo (`.tab`, `.mif`), GeoJSON (`.geojson`, `.json`), GeoPackage (`.gpkg`), KML/KMZ (`.kml`, `.kmz`), GPX (`.gpx`), AutoCAD DXF (`.dxf`), FlatGeobuf (`.fgb`), CSV (`.csv` with lon/lat coordinates or WKT), and **ZIP Archives (`.zip`)**.
  - **Output**: GeoJSON, ESRI Shapefile, GeoPackage (`.gpkg`), MapInfo TAB, KML, FlatGeobuf, and CSV (WKT).
- **Automatic ZIP Archive Detection**: Drag and drop `.zip` files (such as complete Shapefile archives) for automatic processing.
- **Coordinate Reference System (CRS) and Reprojection**:
  - Preserve original CRS.
  - WGS 84 (`EPSG:4326`) for GPS and Web GeoJSON.
  - Web Mercator (`EPSG:3857`) for online maps (Google Maps, OSM).
  - Indonesian UTM presets (Zone 46S to 54S).
  - Custom EPSG code input.
- **Attribute Encoding Support**: UTF-8, Windows-1252 / CP1252 (for legacy Shapefiles), and ISO-8859-1.
- **High Performance**: Powered by `pyogrio` and `GDAL` engines for efficient reading and writing of large datasets.
- **Cross-Platform Compatibility**: Uses Qt Desktop Services to open output folders on Linux, Windows, and macOS.
- **Batch Cancellation**: Ability to cancel batch processes without application freezing.

---

## Requirements and Installation

### 1. System Requirements
- Python 3.10 or higher (Python 3.12 recommended)
- Linux, Windows, or macOS

### 2. Virtual Environment Setup

1. Navigate to the project directory:
   ```bash
   cd /home/lenovo/Projects/Geojson-converter
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv_gis
   ```

3. Activate the virtual environment:
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

## Running the Application

Ensure the virtual environment is activated, then run:

```bash
python main.py
```

### Usage Instructions:
1. **Select Input Files**: Drag and drop files or click **Add File/ZIP** or **Add Folder** button.
2. **Configure Target Format and CRS**:
   - Select the output format (e.g., GeoJSON, GPKG, Shapefile, KML, etc.).
   - Select the target CRS (e.g., WGS 84 `EPSG:4326` or UTM Zone).
   - Select attribute encoding if required.
3. **Select Output Folder**: Specify the folder where results will be saved.
4. **Start Conversion**: Click **Start Conversion**. Status log and progress bar will monitor the process in real-time.

---

## Supported File Formats

| Format | Input Extension | Output Driver |
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
| **ZIP Archive** | `.zip` | Automatically extracted |
