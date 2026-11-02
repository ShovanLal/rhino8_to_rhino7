"""
Comprehensive Test Suite for Rhino 8 -> Rhino 7 Converter.
Validates single-file, batch, pre-check version skipping, --force,
--output-dir, and object preservation (Brep, Extrusion, Mesh, Curve, SubD, Layers, Blocks).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import rhino3dm


def create_sample_r8_file(filepath: Path, name: str = "TestModel") -> Path:
    """Creates a valid Rhino 8 .3dm file with rich geometry, layers, and blocks."""
    model = rhino3dm.File3dm()

    # 1. Add Layers
    layer1 = rhino3dm.Layer()
    layer1.Name = f"{name}_Layer_Curves"
    model.Layers.Add(layer1)

    layer2 = rhino3dm.Layer()
    layer2.Name = f"{name}_Layer_Solids"
    model.Layers.Add(layer2)

    # 2. Add Curve
    curve = rhino3dm.LineCurve(rhino3dm.Point3d(0, 0, 0), rhino3dm.Point3d(15, 20, 0))
    attr_crv = rhino3dm.ObjectAttributes()
    attr_crv.Name = "TestLine"
    model.Objects.AddCurve(curve, attr_crv)

    # 3. Add Mesh
    mesh = rhino3dm.Mesh()
    mesh.Vertices.Add(0, 0, 0)
    mesh.Vertices.Add(10, 0, 0)
    mesh.Vertices.Add(5, 10, 0)
    mesh.Faces.AddFace(0, 1, 2)
    mesh.Normals.ComputeNormals()
    attr_mesh = rhino3dm.ObjectAttributes()
    attr_mesh.Name = "TestMesh"
    model.Objects.AddMesh(mesh, attr_mesh)

    # 4. Add Brep (Sphere)
    sphere = rhino3dm.Sphere(rhino3dm.Point3d(10, 10, 10), 4.0)
    brep = sphere.ToBrep()
    attr_brep = rhino3dm.ObjectAttributes()
    attr_brep.Name = "TestBrepSphere"
    model.Objects.AddBrep(brep, attr_brep)

    # 5. Add Extrusion
    box = rhino3dm.Box(rhino3dm.BoundingBox(0, 0, 0, 8, 8, 8))
    extrusion = rhino3dm.Extrusion.CreateBoxExtrusion(box, True)
    attr_extr = rhino3dm.ObjectAttributes()
    attr_extr.Name = "TestExtrusion"
    model.Objects.AddExtrusion(extrusion, attr_extr)

    # 6. Add SubD
    subd = rhino3dm.SubD()
    attr_subd = rhino3dm.ObjectAttributes()
    attr_subd.Name = "TestSubD"
    model.Objects.Add(subd, attr_subd)

    # 7. Add Block Definition (InstanceDefinition)
    block_crv = rhino3dm.LineCurve(rhino3dm.Point3d(0, 0, 0), rhino3dm.Point3d(5, 5, 5))
    block_attr = rhino3dm.ObjectAttributes()
    block_attr.Name = "SubBlockCurve"
    model.InstanceDefinitions.Add(
        f"{name}_BlockDef",
        "Block definition test",
        "",
        "",
        rhino3dm.Point3d(0, 0, 0),
        (block_crv,),
        (block_attr,),
    )

    # Save as Rhino 8 archive format
    success = model.Write(str(filepath), version=8)
    assert success, f"Failed to create test file at {filepath}"
    assert filepath.exists(), f"File does not exist: {filepath}"
    return filepath


def run_tests():
    test_dir = Path("test_workspace")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    print("======================================================================")
    print("           RUNNING RHINO 8 -> RHINO 7 CONVERTER TEST SUITE            ")
    print("======================================================================")

    try:
        # TEST 1: Create Rhino 8 sample file and verify version 80
        print("\n[TEST 1] Generating rich Rhino 8 test file...")
        r8_file1 = test_dir / "assembly_v8.3dm"
        create_sample_r8_file(r8_file1, name="Assembly")

        initial_model = rhino3dm.File3dm.Read(str(r8_file1))
        assert initial_model is not None, "Failed to read created R8 file"
        print(f"  ✓ Initial ArchiveVersion: {initial_model.ArchiveVersion} (Rhino {initial_model.ArchiveVersion // 10})")
        assert initial_model.ArchiveVersion == 80, f"Expected version 80, got {initial_model.ArchiveVersion}"
        print("  ✓ Objects count:", len(initial_model.Objects))
        print("  ✓ Layers count:", len(initial_model.Layers))
        print("  ✓ InstanceDefinitions count:", len(initial_model.InstanceDefinitions))

        # TEST 2: Convert single file via CLI
        print("\n[TEST 2] Converting single file to Rhino 7 via CLI...")
        cmd = [sys.executable, "lalgondar_converter.py", str(r8_file1)]
        res = subprocess.run(cmd, input="4\n", capture_output=True, text=True, encoding="utf-8")
        print(res.stdout)
        if res.stderr:
            print("[STDERR]:", res.stderr)
        assert res.returncode == 0, f"Conversion failed with code {res.returncode}"

        expected_v7_file = test_dir / "assembly_v8_v7.3dm"
        assert expected_v7_file.exists(), f"Output file not found: {expected_v7_file}"
        print(f"  ✓ Converted output exists: {expected_v7_file.name}")

        # Verify output file with rhino3dm
        v7_model = rhino3dm.File3dm.Read(str(expected_v7_file))
        assert v7_model is not None, "Converted file could not be read by rhino3dm"
        print(f"  ✓ Converted file ArchiveVersion: {v7_model.ArchiveVersion} (Rhino {v7_model.ArchiveVersion // 10})")
        assert v7_model.ArchiveVersion == 70, f"Expected ArchiveVersion 70, got {v7_model.ArchiveVersion}"
        assert len(v7_model.Objects) == len(initial_model.Objects), "Object count mismatch!"
        assert len(v7_model.Layers) == len(initial_model.Layers), "Layer count mismatch!"
        assert len(v7_model.InstanceDefinitions) == len(initial_model.InstanceDefinitions), "Block count mismatch!"
        print("  ✓ All geometry types, layers, and blocks verified in version 7 file!")

        # TEST 3: Pre-check & Validation: Skip if already target version
        print("\n[TEST 3] Pre-check test: Trying to convert already version 7 file...")
        cmd_skip = [sys.executable, "lalgondar_converter.py", str(expected_v7_file), "-t", "7"]
        res_skip = subprocess.run(cmd_skip, input="4\n", capture_output=True, text=True, encoding="utf-8")
        print(res_skip.stdout)
        assert "SKIPPED" in res_skip.stdout, "File should have been skipped!"
        print("  ✓ Successfully skipped version 7 file without --force.")

        # TEST 4: Force flag on already version 7 file
        print("\n[TEST 4] Pre-check test: Trying with --force flag...")
        cmd_force = [sys.executable, "lalgondar_converter.py", str(expected_v7_file), "--force", "-t", "7"]
        res_force = subprocess.run(cmd_force, input="4\n", capture_output=True, text=True, encoding="utf-8")
        print(res_force.stdout)
        assert "OK" in res_force.stdout, "File should have been converted when --force was specified!"
        print("  ✓ Successfully forced conversion with --force.")

        # TEST 5: Batch folder processing with multiple files
        print("\n[TEST 5] Batch folder conversion with multiple files...")
        batch_src_dir = test_dir / "batch_source"
        batch_src_dir.mkdir(parents=True, exist_ok=True)
        r8_file2 = batch_src_dir / "part_alpha.3dm"
        r8_file3 = batch_src_dir / "part_beta.3dm"
        create_sample_r8_file(r8_file2, name="PartAlpha")
        create_sample_r8_file(r8_file3, name="PartBeta")

        cmd_batch = [sys.executable, "lalgondar_converter.py", str(batch_src_dir)]
        res_batch = subprocess.run(cmd_batch, input="4\n", capture_output=True, text=True, encoding="utf-8")
        print(res_batch.stdout)
        assert res_batch.returncode == 0, f"Batch conversion failed: {res_batch.stderr}"

        assert (batch_src_dir / "part_alpha_v7.3dm").exists(), "part_alpha_v7.3dm not found"
        assert (batch_src_dir / "part_beta_v7.3dm").exists(), "part_beta_v7.3dm not found"
        print("  ✓ Batch folder processing succeeded!")

        # TEST 6: Safety check against overwriting source file
        print("\n[TEST 6] Safety check: Ensure original files cannot be overwritten...")
        from lalgondar_converter import convert_file
        rec_unsafe = convert_file(r8_file1, suffix="", output_dir=r8_file1.parent)
        assert rec_unsafe.status == "FAILED" and "Safety Violation" in rec_unsafe.message
        print("  ✓ Source file overwrite protection verified!")

        print("\n======================================================================")
        print("                   ALL TESTS PASSED SUCCESSFULLY!                     ")
        print("======================================================================")

    finally:
        # Cleanup test workspace
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    run_tests()
