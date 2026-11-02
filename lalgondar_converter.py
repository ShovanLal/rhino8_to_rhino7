#!/usr/bin/env python3
"""
===============================================================================
       LALGONDAR(8-1)converter - Standalone Rhino 8 to 7 Down-Converter
               Red & White High-Contrast Dark Terminal Edition
===============================================================================
Powered by rhino3dm (OpenNURBS). Converts Rhino 8 .3dm archives down to
Rhino 7 format without requiring Rhinoceros to be installed.
"""

from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Enable Virtual Terminal Processing for ANSI colors on Windows CMD
if os.name == "nt":
    try:
        kernel32 = ctypes.windll.kernel32
        h_stdout = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(h_stdout, ctypes.byref(mode))
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32.SetConsoleMode(h_stdout, mode.value | 0x0004 | 0x0001 | 0x0002)
    except Exception:
        pass

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import rhino3dm
except ImportError:
    print(
        "\033[1;91m[ERROR]\033[0m rhino3dm is not installed.\n"
        "Please run: \033[1;97mpip install rhino3dm\033[0m",
        file=sys.stderr,
    )
    sys.exit(1)

@dataclass
class AuditRecord:
    """Stores conversion statistics and audit metadata for a single 3dm file."""
    input_path: Path
    output_path: Optional[Path] = None
    status: str = "PENDING"  # SUCCESS, SKIPPED, FAILED
    message: str = ""
    orig_archive_version: int = 0
    orig_major_version: int = 0
    new_archive_version: int = 0
    new_major_version: int = 0
    brep_count: int = 0
    extrusion_count: int = 0
    mesh_count: int = 0
    curve_count: int = 0
    subd_count: int = 0
    other_count: int = 0
    total_objects: int = 0
    layer_count: int = 0
    idef_count: int = 0
    elapsed_ms: float = 0.0
    orig_file_size: int = 0
    new_file_size: int = 0


def format_bytes(size: int) -> str:
    """Format file size in human-readable bytes/KB/MB."""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"


def parse_major_version(archive_ver: int) -> int:
    """Convert Rhino archive version (e.g. 80, 70, 60, 50) to major version (8, 7, etc.)."""
    if archive_ver >= 10:
        return archive_ver // 10
    return archive_ver


def inspect_model_objects(model: rhino3dm.File3dm) -> Dict[str, int]:
    """
    Categorize all objects in the File3dm model into Breps, Extrusions,
    Meshes, Curves, SubDs, and other objects.
    """
    counts = {
        "breps": 0,
        "extrusions": 0,
        "meshes": 0,
        "curves": 0,
        "subds": 0,
        "other": 0,
        "total": len(model.Objects),
    }

    for obj in model.Objects:
        geom = getattr(obj, "Geometry", None)
        if geom is None:
            counts["other"] += 1
            continue

        otype = getattr(geom, "ObjectType", None)
        if otype == rhino3dm.ObjectType.Brep:
            counts["breps"] += 1
        elif otype == rhino3dm.ObjectType.Extrusion:
            counts["extrusions"] += 1
        elif otype == rhino3dm.ObjectType.Mesh:
            counts["meshes"] += 1
        elif otype == rhino3dm.ObjectType.Curve:
            counts["curves"] += 1
        elif otype == rhino3dm.ObjectType.SubD:
            counts["subds"] += 1
        else:
            counts["other"] += 1

    return counts


def convert_file(
    input_path: Path,
    output_dir: Optional[Path] = None,
    suffix: str = "_v7",
    force: bool = False,
    overwrite: bool = True,
) -> AuditRecord:
    """
    Down-converts a single Rhino .3dm file to Rhino 7 format.
    Validates original archive version and avoids overwriting original file.
    """
    record = AuditRecord(input_path=input_path)

    if not input_path.exists():
        record.status = "FAILED"
        record.message = f"File not found: {input_path}"
        return record

    if not input_path.is_file():
        record.status = "FAILED"
        record.message = f"Path is not a regular file: {input_path}"
        return record

    try:
        record.orig_file_size = input_path.stat().st_size
    except OSError:
        record.orig_file_size = 0

    if output_dir:
        target_dir = output_dir
    else:
        target_dir = input_path.parent

    out_filename = f"{input_path.stem}{suffix}.3dm"
    output_path = target_dir / out_filename
    record.output_path = output_path

    # Safety check: Never overwrite original source file
    try:
        if input_path.resolve() == output_path.resolve():
            record.status = "FAILED"
            record.message = (
                f"Safety Violation: Output path would overwrite source file '{input_path.name}'. "
                "Conversion aborted."
            )
            return record
    except Exception:
        if str(input_path.absolute()).lower() == str(output_path.absolute()).lower():
            record.status = "FAILED"
            record.message = "Safety Violation: Output path is identical to original file."
            return record

    if output_path.exists() and not (overwrite or force):
        record.status = "SKIPPED"
        record.message = (
            f"Target file already exists: {output_path.name}. "
            "Use force mode to replace."
        )
        return record

    t_start = time.perf_counter()

    try:
        model = rhino3dm.File3dm.Read(str(input_path))
    except Exception as exc:
        record.status = "FAILED"
        record.message = f"Failed to parse .3dm file: {exc}"
        return record

    if model is None:
        record.status = "FAILED"
        record.message = "File3dm.Read returned null (corrupt or unreadable file)."
        return record

    archive_version = getattr(model, "Archive3dmVersion", getattr(model, "ArchiveVersion", 0))
    record.orig_archive_version = archive_version
    record.orig_major_version = parse_major_version(archive_version)

    if record.orig_major_version <= 7 and not force:
        record.status = "SKIPPED"
        record.message = (
            f"Already version {record.orig_major_version} (Archive: {archive_version}). "
            "Skipped. Use force to re-save."
        )
        return record

    obj_counts = inspect_model_objects(model)
    record.brep_count = obj_counts["breps"]
    record.extrusion_count = obj_counts["extrusions"]
    record.mesh_count = obj_counts["meshes"]
    record.curve_count = obj_counts["curves"]
    record.subd_count = obj_counts["subds"]
    record.other_count = obj_counts["other"]
    record.total_objects = obj_counts["total"]
    record.layer_count = len(model.Layers)
    record.idef_count = len(model.InstanceDefinitions)

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        record.status = "FAILED"
        record.message = f"Cannot create output directory '{target_dir}': {exc}"
        return record

    try:
        write_success = model.Write(str(output_path), version=7)
    except Exception as exc:
        record.status = "FAILED"
        record.message = f"Exception writing Rhino 7 file: {exc}"
        return record

    if not write_success:
        record.status = "FAILED"
        record.message = "model.Write(..., version=7) returned False."
        return record

    t_end = time.perf_counter()
    record.elapsed_ms = (t_end - t_start) * 1000.0

    try:
        if output_path.exists():
            record.new_file_size = output_path.stat().st_size
            verified_model = rhino3dm.File3dm.Read(str(output_path))
            if verified_model:
                record.new_archive_version = verified_model.ArchiveVersion
                record.new_major_version = parse_major_version(record.new_archive_version)
            else:
                record.new_archive_version = 70
                record.new_major_version = 7
        else:
            record.status = "FAILED"
            record.message = "Written file not found on disk after write."
            return record
    except Exception:
        record.new_archive_version = 70
        record.new_major_version = 7

    record.status = "SUCCESS"
    record.message = "Converted successfully to Rhino 7."
    return record


def parse_raw_input_paths(raw_input: str) -> List[str]:
    """
    Safely parses single or multiple file paths from interactive input,
    handling Windows Explorer drag-and-drop quotes and whitespace.
    """
    import re
    cleaned = raw_input.strip()
    if not cleaned:
        return []

    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        inner = cleaned[1:-1].strip()
        if '"' not in inner and "'" not in inner:
            return [inner]

    matches = re.findall(r'(?:["]([^"]+)["]|[\']([^\']+)[\']|(\S+))', cleaned)
    if matches:
        paths = []
        for m in matches:
            val = m[0] or m[1] or m[2]
            if val:
                paths.append(val.strip())
        return paths

    return [cleaned.strip('"\' ')]


def collect_target_files(
    inputs: List[str], recursive: bool = True
) -> Tuple[List[Path], List[str]]:
    """Collect and validate target .3dm files."""
    collected: List[Path] = []
    errors: List[str] = []

    for raw in inputs:
        clean = raw.strip().strip('"').strip("'")
        if not clean:
            continue
        p = Path(clean)
        if not p.exists():
            errors.append(f"Input path does not exist: {clean}")
            continue

        if p.is_file():
            if p.suffix.lower() == ".3dm":
                collected.append(p)
            else:
                errors.append(f"Skipping non-3dm file: {p.name}")
        elif p.is_dir():
            pattern = "**/*.3dm" if recursive else "*.3dm"
            for f in p.glob(pattern):
                if f.is_file():
                    if f.stem.endswith("_v7"):
                        continue
                    collected.append(f)

    unique_files: List[Path] = []
    seen = set()
    for f in collected:
        try:
            resolved = f.resolve()
        except Exception:
            resolved = f.absolute()
        if resolved not in seen:
            seen.add(resolved)
            unique_files.append(f)

    return unique_files, errors

# =============================================================================
# RED & WHITE ANSI COLOR PALETTE
# =============================================================================
R_BOLD = "\033[1;91m"          # Bright Neon Red
R_MED  = "\033[38;2;239;68;68m" # Vibrant Crimson Red
R_DARK = "\033[38;2;185;28;28m" # Deep Blood Red
R_BG   = "\033[48;2;185;28;28m\033[1;97m" # Red Background with Bright White Text
W_BOLD = "\033[1;97m"          # Pure Glossy White
W_MED  = "\033[38;2;241;245;249m" # Crisp Off-White
GRAY   = "\033[38;2;148;163;184m" # Soft Slate Silver
D_GRAY = "\033[38;2;71;85;105m"  # Dark Muted Border
RESET  = "\033[0m"


def clear_screen() -> None:
    """Clear console screen."""
    os.system("cls" if os.name == "nt" else "clear")


def print_banner() -> None:
    """Render the high-impact LALGONDAR(8-1)converter Red & White ASCII Art Logo."""
    banner = f"""{R_BOLD}
   ██╗      █████╗ ██╗      ██████╗  ██████╗ ███╗   ██╗██████╗  █████╗ ██████╗ 
   ██║     ██╔══██╗██║     ██╔════╝ ██╔═══██╗████╗  ██║██╔══██╗██╔══██╗██╔══██╗
   ██║     ███████║██║     ██║  ███╗██║   ██║██╔██╗ ██║██║  ██║███████║██████╔╝
   ██║     ██╔══██║██║     ██║   ██║██║   ██║██║╚██╗██║██║  ██║██╔══██║██╔══██╗
   ███████╗██║  ██║███████╗╚██████╔╝╚██████╔╝██║ ╚████║██████╔╝██║  ██║██║  ██║
   ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝{RESET}
                {R_BG}  (8-1) CONVERTER  {RESET}  {W_BOLD}v1.0.0 // RHINO ARCHIVE ENGINE{RESET}
    {D_GRAY}─────────────────────────────────────────────────────────────────────────────────{RESET}
    {W_BOLD}CORE ENGINE:{RESET} {R_BOLD}rhino3dm v{rhino3dm.__version__}{RESET}   {W_BOLD}TARGET:{RESET} {W_MED}Rhino 70 (v7){RESET}   {W_BOLD}SAFE MODE:{RESET} {R_BOLD}SOURCE IMMUNE{RESET}
    {D_GRAY}─────────────────────────────────────────────────────────────────────────────────{RESET}
"""
    print(banner)


def print_single_card_red_white(rec: AuditRecord) -> None:
    """Print a single-file audit card in crisp red & white styling."""
    box_w = 78
    top    = f"{R_MED}╔" + "═" * (box_w - 2) + f"╗{RESET}"
    sep    = f"{R_MED}╠" + "═" * (box_w - 2) + f"╣{RESET}"
    bot    = f"{R_MED}╚" + "═" * (box_w - 2) + f"╝{RESET}"
    line   = f"{R_MED}║{RESET}"

    status_tag = f"{R_BG} SUCCESS {RESET}" if rec.status == "SUCCESS" else (
        f"{W_BOLD}[SKIPPED]{RESET}" if rec.status == "SKIPPED" else f"{R_BOLD}[FAILED]{RESET}"
    )

    print("\n" + top)
    header_text = f" {W_BOLD}LALGONDAR ARCHIVE AUDIT: {rec.input_path.name[:45]}{RESET} "
    # Calculate visible length without ANSI codes for proper alignment
    print(f"{line} {header_text:<87}{line}")
    print(sep)

    print(f"{line}  {W_BOLD}Status:{RESET}              {status_tag:<50}{line}")
    print(f"{line}  {W_BOLD}Input File:{RESET}          {rec.input_path.name:<58}{line}")
    out_name = rec.output_path.name if rec.output_path else "-"
    print(f"{line}  {W_BOLD}Output File:{RESET}         {R_BOLD}{out_name:<58}{RESET}{line}")
    
    if rec.output_path:
        out_folder = str(rec.output_path.parent)
        if len(out_folder) > 55:
            out_folder = "..." + out_folder[-52:]
        print(f"{line}  {W_BOLD}Destination:{RESET}         {out_folder:<58}{line}")

    trans_str = f"Rhino {rec.orig_major_version} (v{rec.orig_archive_version}) ➔ Rhino {rec.new_major_version} (v{rec.new_archive_version})"
    print(f"{line}  {W_BOLD}Archive Version:{RESET}     {trans_str:<58}{line}")

    size_str = f"{format_bytes(rec.orig_file_size)} ➔ {format_bytes(rec.new_file_size)}"
    print(f"{line}  {W_BOLD}File Size Delta:{RESET}     {size_str:<58}{line}")
    print(f"{line}  {W_BOLD}Conversion Speed:{RESET}    {R_BOLD}{rec.elapsed_ms:,.2f} ms{RESET}{' ' * 46}{line}")

    print(sep)
    print(f"{line}  {R_BG} PRESERVED ENTITY MATRIX {RESET}{' ' * 51}{line}")
    print(f"{line}    {W_BOLD}• Breps (Solids/Surfaces):{RESET}       {rec.brep_count:<40}{line}")
    print(f"{line}    {W_BOLD}• Extrusions (Prisms):{RESET}           {rec.extrusion_count:<40}{line}")
    print(f"{line}    {W_BOLD}• Meshes (Tri/Quad):{RESET}             {rec.mesh_count:<40}{line}")
    print(f"{line}    {W_BOLD}• Curves (NURBS/Lines):{RESET}          {rec.curve_count:<40}{line}")
    print(f"{line}    {W_BOLD}• SubDs (Subdivisions):{RESET}          {rec.subd_count:<40}{line}")
    if rec.other_count > 0:
        print(f"{line}    {W_BOLD}• Other Entities:{RESET}                {rec.other_count:<40}{line}")
    print(f"{line}    {D_GRAY}─────────────────────────────────────────{RESET}{' ' * 33}{line}")
    print(f"{line}    {W_BOLD}• Total Preserved Objects:{RESET}       {R_BOLD}{rec.total_objects:<40}{RESET}{line}")
    print(f"{line}    {W_BOLD}• Total Layers Preserved:{RESET}        {rec.layer_count:<40}{line}")
    print(f"{line}    {W_BOLD}• Block Definitions:{RESET}             {rec.idef_count:<40}{line}")

    if rec.status != "SUCCESS":
        print(sep)
        print(f"{line}  {R_BOLD}Note/Reason:{RESET} {rec.message[:60]:<61}{line}")

    print(bot + "\n")


def print_batch_table_red_white(records: List[AuditRecord]) -> None:
    """Print a multi-file conversion summary table in red & white styling."""
    if not records:
        return

    headers = [
        "Source File",
        "Output File",
        "Status",
        "Version",
        "Total",
        "Brep",
        "Extr",
        "Mesh",
        "Crv",
        "SubD",
        "Layers",
        "Blocks",
        "Time(ms)",
    ]

    rows = []
    tot_success = 0
    tot_objs = 0
    tot_breps = 0
    tot_extrs = 0
    tot_meshes = 0
    tot_crvs = 0
    tot_subds = 0
    tot_layers = 0
    tot_blocks = 0
    tot_time_ms = 0.0

    for r in records:
        in_name = r.input_path.name
        if len(in_name) > 20:
            in_name = in_name[:17] + "..."
        out_name = r.output_path.name if r.output_path else "-"
        if len(out_name) > 20:
            out_name = out_name[:17] + "..."

        if r.status == "SUCCESS":
            tot_success += 1
            tot_objs += r.total_objects
            tot_breps += r.brep_count
            tot_extrs += r.extrusion_count
            tot_meshes += r.mesh_count
            tot_crvs += r.curve_count
            tot_subds += r.subd_count
            tot_layers += r.layer_count
            tot_blocks += r.idef_count
            tot_time_ms += r.elapsed_ms

            rows.append([
                in_name,
                out_name,
                "SUCCESS",
                f"{r.orig_major_version}➔7",
                str(r.total_objects),
                str(r.brep_count),
                str(r.extrusion_count),
                str(r.mesh_count),
                str(r.curve_count),
                str(r.subd_count),
                str(r.layer_count),
                str(r.idef_count),
                f"{r.elapsed_ms:.1f}",
            ])
        else:
            rows.append([
                in_name,
                out_name,
                r.status,
                f"v{r.orig_major_version}" if r.orig_major_version else "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
                "-",
            ])

    # Widths
    col_w = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_w[idx] = max(col_w[idx], len(val))

    totals_row = [
        f"TOTAL ({tot_success}/{len(records)})",
        "",
        "",
        "",
        str(tot_objs),
        str(tot_breps),
        str(tot_extrs),
        str(tot_meshes),
        str(tot_crvs),
        str(tot_subds),
        str(tot_layers),
        str(tot_blocks),
        f"{tot_time_ms:.1f}",
    ]
    for idx, val in enumerate(totals_row):
        col_w[idx] = max(col_w[idx], len(val))

    # Borders
    top_b = f"{R_MED}╔" + "╦".join("═" * (w + 2) for w in col_w) + f"╗{RESET}"
    sep_h = f"{R_MED}╠" + "╬".join("═" * (w + 2) for w in col_w) + f"╣{RESET}"
    mid_s = f"{R_MED}╠" + "╬".join("═" * (w + 2) for w in col_w) + f"╣{RESET}"
    bot_b = f"{R_MED}╚" + "╩".join("═" * (w + 2) for w in col_w) + f"╝{RESET}"
    bar   = f"{R_MED}║{RESET}"

    print("\n" + top_b)
    # Header
    cells = [f" {W_BOLD}{h:<{col_w[i]}}{RESET} " for i, h in enumerate(headers)]
    print(bar + bar.join(cells) + bar)
    print(sep_h)

    # Rows
    for r in rows:
        row_cells = []
        for i, val in enumerate(r):
            if i == 2:  # Status
                if val == "SUCCESS":
                    val_str = f"{R_BOLD}{val:^{col_w[i]}}{RESET}"
                elif val == "SKIPPED":
                    val_str = f"{W_BOLD}{val:^{col_w[i]}}{RESET}"
                else:
                    val_str = f"{R_DARK}{val:^{col_w[i]}}{RESET}"
            elif i == 3:  # Version
                val_str = f"{W_MED}{val:^{col_w[i]}}{RESET}"
            elif i >= 4:  # Numeric
                val_str = f"{W_BOLD if i == 4 else W_MED}{val:>{col_w[i]}}{RESET}"
            else:
                val_str = f"{W_MED}{val:<{col_w[i]}}{RESET}"
            row_cells.append(f" {val_str} ")
        print(bar + bar.join(row_cells) + bar)

    # Totals Row
    print(mid_s)
    tot_cells = []
    for i, val in enumerate(totals_row):
        if i >= 4:
            val_str = f"{R_BOLD}{val:>{col_w[i]}}{RESET}"
        elif i == 0:
            val_str = f"{W_BOLD}{val:<{col_w[i]}}{RESET}"
        else:
            val_str = f"{val:<{col_w[i]}}"
        tot_cells.append(f" {val_str} ")
    print(bar + bar.join(tot_cells) + bar)
    print(bot_b + "\n")


def run_interactive_loop(preloaded_paths: Optional[List[str]] = None, initial_force: bool = False) -> None:
    """Main interactive terminal loop for LALGONDAR."""
    clear_screen()
    print_banner()

    force_mode = initial_force
    last_output_dir: Optional[Path] = None

    if preloaded_paths:
        # File(s) were dropped directly onto the .bat icon
        raw_inputs = preloaded_paths
    else:
        raw_inputs = []

    while True:
        if not raw_inputs:
            print(f"{W_BOLD} [ DROPZONE / INPUT PROMPT ]{RESET}")
            print(f"   {GRAY}• Drag & drop your Rhino 8 (.3dm) file directly here and press Enter.{RESET}")
            print(f"   {GRAY}• Or paste an entire directory path to batch convert in place.{RESET}")
            print(f"   {GRAY}• Type {R_BOLD}'force'{RESET}{GRAY} to toggle force mode (Current: {R_BOLD if force_mode else W_BOLD}{'ON' if force_mode else 'OFF'}{RESET}{GRAY}){RESET}")
            print(f"   {GRAY}• Type {R_BOLD}'q'{RESET}{GRAY} to exit.{RESET}\n")

            try:
                user_entry = input(f" {R_BOLD}[LALGONDAR] »{RESET} {W_BOLD}").strip()
                print(f"{RESET}", end="")
            except (EOFError, KeyboardInterrupt):
                print(f"\n{R_BOLD}[*] Exiting LALGONDAR converter. Goodbye!{RESET}")
                break

            if not user_entry:
                continue

            if user_entry.lower() in ("q", "quit", "exit"):
                print(f"\n{R_BOLD}[*] Exiting LALGONDAR converter. Goodbye!{RESET}")
                break

            if user_entry.lower() == "force":
                force_mode = not force_mode
                print(f" {R_BOLD}[!] Force re-save mode set to: {W_BOLD}{'ENABLED' if force_mode else 'DISABLED'}{RESET}\n")
                continue

            raw_inputs = parse_raw_input_paths(user_entry)

        files, discovery_errors = collect_target_files(raw_inputs, recursive=True)

        for err in discovery_errors:
            print(f" {R_BOLD}[!] WARNING:{RESET} {err}")

        if not files:
            print(f" {R_BOLD}[X] ERROR:{RESET} No valid .3dm files found at target. Try again.\n")
            raw_inputs = []
            continue

        tot_files = len(files)
        print(f"\n {R_BG} CONVERSION IN PROGRESS {RESET} {W_BOLD}Found {tot_files} file{'s' if tot_files != 1 else ''} to process...{RESET}\n")

        records: List[AuditRecord] = []
        for idx, file_path in enumerate(files, start=1):
            pct = int((idx / tot_files) * 26)
            bar_graph = f"{R_BOLD}" + "█" * pct + f"{D_GRAY}" + "░" * (26 - pct) + f"{RESET}"
            print(f"   [{bar_graph}] {W_BOLD}{idx}/{tot_files}{RESET} {file_path.name[:35]:<35} ... ", end="", flush=True)

            rec = convert_file(
                input_path=file_path,
                force=force_mode,
                overwrite=True,
            )
            records.append(rec)

            if rec.status == "SUCCESS":
                print(f"{R_BOLD}OK{RESET} ({rec.elapsed_ms:.1f} ms)")
                if rec.output_path:
                    last_output_dir = rec.output_path.parent
            elif rec.status == "SKIPPED":
                print(f"{W_BOLD}SKIPPED{RESET} (already <= v7)")
            else:
                print(f"{R_DARK}FAILED{RESET} ({rec.message})")

        # Present Audit Results in Red & White
        if len(records) == 1:
            print_single_card_red_white(records[0])
        else:
            print_batch_table_red_white(records)

        # Clear inputs for next loop iteration
        raw_inputs = []

        # Interactive post-conversion menu
        print(f"{R_MED}┌─────────────────────────────────────────────────────────────────────────────┐{RESET}")
        print(f"{R_MED}│{RESET}  {W_BOLD}POST-CONVERSION MENU:{RESET}{' ' * 54}{R_MED}│{RESET}")
        print(f"{R_MED}│{RESET}    {R_BOLD}[1]{RESET} {W_BOLD}Convert another file or folder{RESET}{' ' * 42}{R_MED}│{RESET}")
        if last_output_dir and last_output_dir.exists():
            print(f"{R_MED}│{RESET}    {R_BOLD}[2]{RESET} {W_BOLD}Open output folder in Windows Explorer{RESET}{' ' * 34}{R_MED}│{RESET}")
        print(f"{R_MED}│{RESET}    {R_BOLD}[3]{RESET} {W_BOLD}Exit LALGONDAR{RESET}{' ' * 58}{R_MED}│{RESET}")
        print(f"{R_MED}└─────────────────────────────────────────────────────────────────────────────┘{RESET}\n")

        try:
            choice = input(f" {R_BOLD}[Choice 1-3] »{RESET} {W_BOLD}").strip()
            print(f"{RESET}", end="")
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "2" and last_output_dir and last_output_dir.exists():
            print(f" {R_BOLD}[*]{RESET} Opening {last_output_dir} ...")
            os.startfile(str(last_output_dir))
            print()
            continue
        elif choice in ("3", "q", "exit"):
            print(f"\n{R_BOLD}[*] Thank you for using LALGONDAR(8-1)converter. Done!{RESET}\n")
            break
        else:
            clear_screen()
            print_banner()
            continue


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LALGONDAR(8-1)converter - Rhino 8 to 7 Down-Converter.",
        add_help=True,
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        default=[],
        help="One or more .3dm file or directory paths.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force conversion even if already version 7.",
    )
    args = parser.parse_args()

    # Launch interactive loop (supports dropped files as args or interactive prompt)
    run_interactive_loop(preloaded_paths=args.inputs if args.inputs else None, initial_force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
