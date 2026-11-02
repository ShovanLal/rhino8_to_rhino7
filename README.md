# LALGONDAR(8-1)converter

A standalone Rhino 8 to Rhino 7 (`.3dm`) down-converter presented in a high-contrast **Red and White ANSI / ASCII terminal GUI** on a dark background. Powered by [`rhino3dm`](https://github.com/mcneel/rhino3dm) without requiring Rhino to be installed.

---

## Clean Workspace Overview

```text
D:\VibeCodingPlugin\
├── LALGONDAR_CONVERTER.bat   # Double-click or Drag-and-Drop launcher
├── rhino_converter.bat        # Convenient alias launcher
├── lalgondar_converter.py     # 100% self-contained Python engine & Red/White GUI
├── test_converter.py          # Automated verification test suite
├── requirements.txt           # Minimal dependencies (rhino3dm>=8.0.0)
└── README.md                  # Documentation
```

---

## Key Features

- **Red & White High-Contrast Terminal GUI:** Stylized ASCII art banner, crimson borders (`╔═╦═╗`), and glossy white entity metrics.
- **Headless OpenNURBS Engine:** Powered directly by `rhino3dm v8.35.0` — no license or Rhino installation needed.
- **Full Geometry Preservation:** Preserves **Breps**, **Extrusions**, **Meshes**, **Curves**, **SubDs**, **Layers**, and **Block Definitions (`InstanceDefinitions`)**.
- **Source File Immunity:** Original Rhino 8 files are never overwritten. Output files default to `<name>_v7.3dm`.
- **Pre-Check Version Validation:** Skips files that are already version 7 or lower unless `force` mode is enabled.
- **Interactive Post-Conversion Menu:**
  - `[1]` Convert another file or folder
  - `[2]` Open output folder directly in Windows Explorer
  - `[3]` Exit

---

## How to Run

### Method 1: Desktop Drag-and-Drop (Instant)
- Drag and drop any `.3dm` file (or multiple files) directly onto the **`LALGONDAR_CONVERTER.bat`** icon.
- The `_v7.3dm` file is generated in the same directory, and the Red/White audit matrix displays on screen.

### Method 2: Double-Click Interactive Mode
- Double-click **`LALGONDAR_CONVERTER.bat`**.
- Drag your file into the terminal prompt (or paste a path) and press <kbd>Enter</kbd>.

### Method 3: Command Line
```powershell
python lalgondar_converter.py "D:\Models\chair.3dm"
```

---

## Running the Automated Test Suite

To verify conversion integrity and geometry preservation:
```powershell
python test_converter.py
```
