# -*- coding: utf-8 -*-
# force-beam-mesh.py

from abaqus import *
from abaqusConstants import *
import mesh
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

print("\n==============================")
print("  Force B31 Beam Mesh on Wires")
print("==============================\n")

# -------------------------------------------------------
# STEP 1: Kill Step-2 and Step-3 (they are back again)
# -------------------------------------------------------
print("--- Step 1: Cleaning extra steps ---")
for sname in list(model.steps.keys()):
    if sname not in ['Initial', 'ModalStep']:
        try:
            del model.steps[sname]
            print("  Deleted:", sname)
        except Exception as e:
            print("  Could not delete:", sname, "->", e)
print()

# -------------------------------------------------------
# STEP 2: Check wire geometry type
# -------------------------------------------------------
print("--- Step 2: Wire geometry check ---")
sample = model.parts['wr340010_STEEL-3']
print("  Cells  :", len(sample.cells))
print("  Faces  :", len(sample.faces))
print("  Edges  :", len(sample.edges))
print("  Vertices:", len(sample.vertices))
print()

# -------------------------------------------------------
# STEP 3: Force LINE mesh on all wire parts
# -------------------------------------------------------
print("--- Step 3: Forcing B31 beam mesh ---")

WIRE_SEED = 5.0
fixed = 0
failed = 0

for i in range(3, 52):
    pname = 'wr340010_STEEL-' + str(i)
    if pname not in model.parts.keys():
        continue

    part = model.parts[pname]
    edges = part.edges

    if len(edges) == 0:
        print("  SKIP (no edges):", pname)
        failed += 1
        continue

    try:
        # Delete existing mesh first
        part.deleteMesh()

        # CRITICAL: Set mesh controls to LINE on edges only
        part.setMeshControls(
            regions=edges,
            elemShape=LINE
        )

        # Set element type to B31
        elemType_B31 = mesh.ElemType(
            elemCode=B31,
            elemLibrary=STANDARD
        )
        part.setElementType(
            regions=(edges,),
            elemTypes=(elemType_B31,)
        )

        # Seed and generate
        part.seedPart(
            size=WIRE_SEED,
            deviationFactor=0.1,
            minSizeFactor=0.1
        )
        part.generateMesh()

        n_e = len(part.elements)
        n_n = len(part.nodes)
        ratio = round(float(n_n)/float(n_e), 2) if n_e > 0 else 0

        if ratio <= 1.2:
            print("  BEAM ✅", pname, "| elems:", n_e, "| nodes:", n_n, "| ratio:", ratio)
            fixed += 1
        else:
            print("  STILL SOLID ❌", pname, "| ratio:", ratio)
            failed += 1

    except Exception as e:
        print("  ERROR on", pname, "->", e)
        failed += 1

print("\n  Beam-meshed:", fixed, "/ 49")
print("  Failed     :", failed, "/ 49\n")

# -------------------------------------------------------
# STEP 4: If ALL still failed, print cell count
# This tells us if we need a completely different approach
# -------------------------------------------------------
if fixed == 0:
    print("--- Step 4: GEOMETRY DIAGNOSIS ---")
    print("  Wire parts have solid cell geometry.")
    print("  Checking if cells exist on sample part...")
    sample = model.parts['wr340010_STEEL-3']
    print("  Cells:", len(sample.cells))
    print("  This confirms wires are SOLID CYLINDERS, not line bodies.")
    print("  Will need to suppress cells and mesh edges only.\n")

    # Last resort: try suppressing cell mesh controls
    # and forcing only edge meshing
    print("--- Step 4b: Attempting cell suppression approach ---")
    fixed2 = 0
    for i in range(3, 52):
        pname = 'wr340010_STEEL-' + str(i)
        if pname not in model.parts.keys():
            continue
        part = model.parts[pname]

        try:
            part.deleteMesh()
            cells = part.cells
            edges = part.edges

            # Set cells to use NO meshing (suppress solid mesh)
            if len(cells) > 0:
                part.setMeshControls(
                    regions=cells,
                    elemShape=TET,
                    technique=FREE,
                    allowMapped=False
                )
                # Override with line controls on edges
                part.setMeshControls(
                    regions=edges,
                    elemShape=LINE
                )

            elemType_B31 = mesh.ElemType(
                elemCode=B31,
                elemLibrary=STANDARD
            )
            part.setElementType(
                regions=(edges,),
                elemTypes=(elemType_B31,)
            )

            part.seedEdgeBySize(
                edges=edges,
                size=WIRE_SEED,
                deviationFactor=0.1,
                constraint=FINER
            )
            part.generateMesh()

            n_e = len(part.elements)
            n_n = len(part.nodes)
            ratio = round(float(n_n)/float(n_e), 2) if n_e > 0 else 0
            print("  ", pname, "| elems:", n_e, "| nodes:", n_n, "| ratio:", ratio)
            if ratio <= 1.2:
                fixed2 += 1
        except Exception as e:
            print("  ERROR", pname, "->", e)

    print("\n  Beam-meshed (attempt 2):", fixed2, "/ 49")

# -------------------------------------------------------
# STEP 5: Final state
# -------------------------------------------------------
print("\n--- Final State ---")
print("Steps:", list(model.steps.keys()))
total_e = sum(len(p.elements) for p in model.parts.values())
total_n = sum(len(p.nodes) for p in model.parts.values())
print("Total elements:", total_e)
print("Total nodes:", total_n)
print("BCs:", len(model.boundaryConditions.keys()))