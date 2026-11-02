# LALGONDAR(Any-to-Any)converter v2.0

**Universal Rhino Archive Converter** presented in a high-contrast **Red and White ANSI / ASCII terminal GUI** on a dark background.

**Developer & Architect:** Shovan Lal Sarker  
**Copyright:** © 2026 Shovan Lal Sarker. All rights reserved.  
**License:** [MIT License](LICENSE)

---

## What's New in Version 2.0: Any-to-Any Version Conversion

**YES, Any version to Any version is 100% supported!**

Powered by the official OpenNURBS engine (`rhino3dm v8.35.0`), LALGONDAR can convert between **any two versions of Rhino (Rhino 2 through Rhino 8)**:

| Conversion Direction | Supported Versions | Use Case |
| :--- | :--- | :--- |
| **Down-Conversion** | Rhino 8 ➔ 7, 6, 5, 4, 3, 2 | Open Rhino 8 files in older Rhino licenses |
| **Up-Conversion** | Rhino 2, 3, 4, 5, 6, 7 ➔ 8 | Modernize legacy Rhino archives to Rhino 8 format |
| **Cross-Conversion** | Rhino 6 ➔ 7, Rhino 7 ➔ 6, etc. | Seamless exchange between teams on different versions |

- **Default Target:** Rhino 7 (`.3dm` files get `_v7.3dm` suffix).
- **Custom Target:** You can dynamically switch the target version to **Rhino 2, 3, 4, 5, 6, 7, or 8** right inside the interactive menu by typing `t` or `target`, or via the CLI flag `-t <version>`.

---

## Clean Workspace Overview

```text
D:\VibeCodingPlugin\
├── LALGONDAR_CONVERTER.exe   # Standalone Portable Executable (With Embedded Custom Logo)
├── LALGONDAR_CONVERTER.bat   # Double-click or Drag-and-Drop launcher
├── lalgondar_converter.py     # 100% self-contained Python source & Red/White GUI
├── test_converter.py          # Automated verification test suite
├── requirements.txt           # Minimal dependencies (rhino3dm>=8.0.0)
├── lalgondarlogo.svg          # Original vector logo
├── lalgondarlogo.ico          # Multi-resolution icon asset
├── LICENSE                    # MIT License (Copyright © 2026 Shovan Lal Sarker)
├── .gitignore                 # Excludes CAD files & bytecode
└── README.md                  # Documentation
```

---

## Key Features

- **Red & White High-Contrast Terminal GUI:** Stylized ASCII art banner, crimson borders (`╔═╦═╗`), and glossy white entity metrics.
- **Headless OpenNURBS Engine:** Powered directly by `rhino3dm v8.35.0` — no Rhino installation or license required.
- **Full Geometry Preservation:** Preserves **Breps**, **Extrusions**, **Meshes**, **Curves**, **SubDs**, **Layers**, and **Block Definitions (`InstanceDefinitions`)**.
- **Source File Immunity:** Original source files are never overwritten. Output files default to `<name>_v{target}.3dm`.
- **Pre-Check Version Validation:** Skips files that are already the target version unless `force` mode is enabled.
- **Prominent Author Credit & Post-Conversion Menu:**
  - `[1]` Convert another file or folder
  - `[2]` Open output folder directly in Windows Explorer
  - `[3]` Change Target Rhino Version (2 – 8)
  - `[4]` Exit LALGONDAR

---

## How to Run

### Method 1: Portable Standalone Executable (Zero Install)
- Double-click **`LALGONDAR_CONVERTER.exe`** to open the Red & White terminal GUI.
- Or drag-and-drop any `.3dm` file onto `LALGONDAR_CONVERTER.exe`.

### Method 2: Batch Launcher
- Double-click or drag files onto **`LALGONDAR_CONVERTER.bat`**.

### Method 3: Command Line (CLI)
```powershell
# Convert to Rhino 7 (default)
python lalgondar_converter.py "D:\Models\chair.3dm"

# Convert to Rhino 6
python lalgondar_converter.py "D:\Models\chair.3dm" -t 6

# Convert to Rhino 8
python lalgondar_converter.py "D:\Models\old_v5.3dm" -t 8
```

---

## Running the Automated Test Suite

To verify conversion integrity and geometry preservation:
```powershell
python test_converter.py
```
