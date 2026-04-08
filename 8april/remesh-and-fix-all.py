# -*- coding: utf-8 -*-
# remesh-and-fix-all.py

from abaqus import *
from abaqusConstants import *
import mesh
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

print("\n==============================")
print("   Remesh + Full Fix Script")
print("==============================\n")

# -------------------------------------------------------
# STEP 1: Remesh BOTH brackets with coarser, cleaner seed
# Coarser = fewer distorted elements
# -------------------------------------------------------
print("--- Step 1: Remeshing brackets ---")
bracket_names = ['wr340010_STEEL-1', 'wr340010_STEEL-2']

for bname in bracket_names:
    part = model.parts[bname]
    cells = part.cells

    try:
        part.deleteMesh()
        print("  Deleted old mesh:", bname)
    except:
        print("  No existing mesh to delete:", bname)

    # Coarser seed = 4.0mm (was 2.0mm before = caused distortion)
    part.seedPart(size=4.0, deviationFactor=0.1, minSizeFactor=0.1)

    # Free tet — most robust for complex bracket geometry
    part.setMeshControls(regions=cells, elemShape=TET, technique=FREE)

    elemType1 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD)
    elemType2 = mesh.ElemType(elemCode=C3D4,  elemLibrary=STANDARD)
    part.setElementType(regions=(cells,), elemTypes=(elemType1, elemType2))

    part.generateMesh()
    print("  Remeshed:", bname,
          "| elements:", len(part.elements),
          "| nodes:", len(part.nodes))

print()

# -------------------------------------------------------
# STEP 2: Mesh ALL wire parts if not already meshed
# -------------------------------------------------------
print("--- Step 2: Meshing wire parts ---")

wire_seed = 5.0  # 5mm element length along wire centerline

meshed_count = 0
for i in range(3, 52):
    pname = 'wr340010_STEEL-' + str(i)
    if pname not in model.parts.keys():
        continue

    part = model.parts[pname]

    # Skip if already has elements
    if len(part.elements) > 0:
        meshed_count += 1
        continue

    edges = part.edges
    if len(edges) == 0:
        print("  WARNING: No edges on", pname)
        continue

    try:
        part.seedPart(size=wire_seed,
                      deviationFactor=0.1,
                      minSizeFactor=0.1)
        part.generateMesh()
        meshed_count += 1
    except Exception as e:
        print("  Failed to mesh", pname, "->", e)

print("  Wires meshed/confirmed:", meshed_count, "/ 49\n")

# -------------------------------------------------------
# STEP 3: Remove all constraints (broken ties)
# -------------------------------------------------------
print("--- Step 3: Removing all constraints ---")
for name in list(model.constraints.keys()):
    try:
        del model.constraints[name]
    except:
        pass
print("  Done.\n")

# -------------------------------------------------------
# STEP 4: Remove all interactions
# -------------------------------------------------------
print("--- Step 4: Removing all interactions ---")
for name in list(model.interactions.keys()):
    try:
        del model.interactions[name]
    except:
        pass
for name in list(model.interactionProperties.keys()):
    try:
        del model.interactionProperties[name]
    except:
        pass
print("  Done.\n")

# -------------------------------------------------------
# STEP 5: Remove ALL BCs and reapply cleanly
# -------------------------------------------------------
print("--- Step 5: Rebuilding all BCs ---")
for name in list(model.boundaryConditions.keys()):
    try:
        del model.boundaryConditions[name]
    except:
        pass

# Fix both brackets (all faces)
for bname in bracket_names:
    inst = assembly.instances[bname]
    region = regionToolset.Region(faces=inst.faces[:])
    bc_name = 'BC_Fixed_' + bname.split('-')[-1]
    model.EncastreBC(
        name=bc_name,
        createStepName='Initial',
        region=region
    )
    print("  EncastreBC applied:", bc_name)

# Pin all wire endpoints
pin_count = 0
for i in range(3, 52):
    wname = 'wr340010_STEEL-' + str(i)
    if wname not in assembly.instances.keys():
        continue

    inst = assembly.instances[wname]
    if len(inst.vertices) == 0:
        continue

    try:
        region = regionToolset.Region(vertices=inst.vertices)
        model.EncastreBC(
            name='BC_Pin_Wire_' + str(i),
            createStepName='Initial',
            region=region
        )
        pin_count += 1
    except Exception as e:
        print("  BC failed on wire", i, "->", e)

print("  Wire endpoint BCs applied:", pin_count)
print()

# -------------------------------------------------------
# STEP 6: Clean steps
# -------------------------------------------------------
print("--- Step 6: Verifying ModalStep ---")
for sname in list(model.steps.keys()):
    if sname not in ['Initial', 'ModalStep']:
        try:
            del model.steps[sname]
            print("  Deleted extra step:", sname)
        except:
            pass

if 'ModalStep' not in model.steps.keys():
    model.FrequencyStep(
        name='ModalStep',
        previous='Initial',
        numEigen=10,
        eigensolver=LANCZOS,
        shift=1.0
    )
    print("  Created ModalStep with shift=1.0")
else:
    try:
        model.steps['ModalStep'].setValues(
            numEigen=10,
            eigensolver=LANCZOS,
            shift=1.0
        )
        print("  ModalStep updated: numEigen=10, shift=1.0 ✅")
    except Exception as e:
        print("  ModalStep exists:", e)

# -------------------------------------------------------
# STEP 7: Final summary
# -------------------------------------------------------
print("\n==============================")
print("   Final Model State")
print("==============================")
print("Steps:", list(model.steps.keys()))
print("Interactions:", list(model.interactions.keys()))
print("Constraints:", list(model.constraints.keys()))

total_elems = 0
total_nodes = 0
for pname, part in model.parts.items():
    total_elems += len(part.elements)
    total_nodes += len(part.nodes)

print("Total elements across all parts:", total_elems)
print("Total nodes across all parts:", total_nodes)
print("Total BCs:", len(model.boundaryConditions.keys()))
print("\nBC list:")
for name in model.boundaryConditions.keys():
    print("  ", name)

print("\n✅ Done. Submit the job now.\n")