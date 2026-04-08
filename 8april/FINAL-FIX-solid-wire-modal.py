# -*- coding: utf-8 -*-
# FINAL-FIX-solid-wire-modal.py
# Accepts solid tet wires, fixes sections, remeshes, submits cleanly

from abaqus import *
from abaqusConstants import *
import mesh
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

print("\n================================")
print("  FINAL FIX — Solid Wire Modal")
print("================================\n")

# -------------------------------------------------------
# STEP 1: Kill everything dirty
# -------------------------------------------------------
print("--- Step 1: Full cleanup ---")

for name in list(model.interactions.keys()):
    try: del model.interactions[name]
    except: pass

for name in list(model.interactionProperties.keys()):
    try: del model.interactionProperties[name]
    except: pass

for name in list(model.constraints.keys()):
    try: del model.constraints[name]
    except: pass

for name in list(model.boundaryConditions.keys()):
    try: del model.boundaryConditions[name]
    except: pass

for sname in list(model.steps.keys()):
    if sname not in ['Initial', 'ModalStep']:
        try: del model.steps[sname]
        except: pass

print("  ✅ Cleanup done.\n")

# -------------------------------------------------------
# STEP 2: Ensure correct materials exist
# -------------------------------------------------------
print("--- Step 2: Materials ---")

if 'SS_WIRE' not in model.materials.keys():
    mat = model.Material(name='SS_WIRE')
    mat.Density(table=((7.93e-6,),))
    mat.Elastic(table=((200000.0, 0.30),))
    print("  Created SS_WIRE")
else:
    print("  SS_WIRE OK ✅")

if 'StainlessSteel' not in model.materials.keys():
    mat = model.Material(name='StainlessSteel')
    mat.Density(table=((7.93e-6,),))
    mat.Elastic(table=((200000.0, 0.30),))
    print("  Created StainlessSteel")
else:
    print("  StainlessSteel OK ✅")

# -------------------------------------------------------
# STEP 3: Create SOLID sections (not beam)
# -------------------------------------------------------
print("\n--- Step 3: Solid sections ---")

if 'WireSolidSection' not in model.sections.keys():
    model.HomogeneousSolidSection(
        name='WireSolidSection',
        material='SS_WIRE',
        thickness=None
    )
    print("  Created WireSolidSection (C3D4, SS_WIRE)")
else:
    print("  WireSolidSection OK ✅")

if 'BracketSection' not in model.sections.keys():
    model.HomogeneousSolidSection(
        name='BracketSection',
        material='StainlessSteel',
        thickness=None
    )
    print("  Created BracketSection")
else:
    print("  BracketSection OK ✅")

# -------------------------------------------------------
# STEP 4: Remesh wires with COARSE seed to kill distortion
# -------------------------------------------------------
print("\n--- Step 4: Remeshing wires (coarse, C3D4) ---")

WIRE_SEED = 0.15   # mm — coarse enough for 0.265mm diameter wire

wire_ok = 0
wire_fail = 0

for i in range(3, 52):
    pname = 'wr340010_STEEL-' + str(i)
    if pname not in model.parts.keys():
        continue

    part = model.parts[pname]
    cells = part.cells

    try:
        part.deleteMesh()

        part.seedPart(
            size=WIRE_SEED,
            deviationFactor=0.1,
            minSizeFactor=0.05
        )

        part.setMeshControls(
            regions=cells,
            elemShape=TET,
            technique=FREE
        )

        e1 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
        part.setElementType(
            regions=(cells,),
            elemTypes=(e1,)
        )

        part.generateMesh()

        # Assign solid section
        region = regionToolset.Region(cells=part.cells)
        part.SectionAssignment(
            region=region,
            sectionName='WireSolidSection'
        )

        wire_ok += 1

    except Exception as e:
        print("  FAILED:", pname, "->", e)
        wire_fail += 1

print("  Wires meshed OK:", wire_ok, "/ 49")
print("  Failed         :", wire_fail, "/ 49")

# -------------------------------------------------------
# STEP 5: Remesh brackets (coarser to reduce distortion)
# -------------------------------------------------------
print("\n--- Step 5: Remeshing brackets ---")

bracket_names = ['wr340010_STEEL-1', 'wr340010_STEEL-2']

for bname in bracket_names:
    part = model.parts[bname]
    cells = part.cells

    try:
        part.deleteMesh()
        part.seedPart(size=5.0, deviationFactor=0.15, minSizeFactor=0.1)
        part.setMeshControls(regions=cells, elemShape=TET, technique=FREE)

        e1 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
        part.setElementType(regions=(cells,), elemTypes=(e1,))
        part.generateMesh()

        # Assign bracket section
        region = regionToolset.Region(cells=part.cells)
        part.SectionAssignment(
            region=region,
            sectionName='BracketSection'
        )

        print("  OK:", bname,
              "| elems:", len(part.elements),
              "| nodes:", len(part.nodes))

    except Exception as e:
        print("  FAILED:", bname, "->", e)

# -------------------------------------------------------
# STEP 6: Apply EncastreBC to brackets (all faces)
# -------------------------------------------------------
print("\n--- Step 6: Bracket BCs ---")

for bname in bracket_names:
    inst = assembly.instances[bname]
    region = regionToolset.Region(faces=inst.faces[:])
    bc_name = 'BC_Fixed_' + bname.split('-')[-1]
    model.EncastreBC(
        name=bc_name,
        createStepName='Initial',
        region=region
    )
    print("  EncastreBC:", bc_name, "✅")

# -------------------------------------------------------
# STEP 7: Pin wire endpoints (all vertices)
# -------------------------------------------------------
print("\n--- Step 7: Wire endpoint BCs ---")

pin_ok = 0
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
        pin_ok += 1
    except Exception as e:
        print("  BC fail wire", i, "->", e)

print("  Wire endpoint BCs:", pin_ok, "/ 49")

# -------------------------------------------------------
# STEP 8: ModalStep
# -------------------------------------------------------
print("\n--- Step 8: ModalStep ---")

if 'ModalStep' not in model.steps.keys():
    model.FrequencyStep(
        name='ModalStep',
        previous='Initial',
        numEigen=10,
        eigensolver=LANCZOS,
        shift=1.0
    )
    print("  Created ModalStep ✅")
else:
    try:
        model.steps['ModalStep'].setValues(
            numEigen=10,
            eigensolver=LANCZOS,
            shift=1.0
        )
        print("  ModalStep updated ✅")
    except Exception as e:
        print("  ModalStep exists:", e)

# -------------------------------------------------------
# STEP 9: Final summary
# -------------------------------------------------------
print("\n================================")
print("   FINAL MODEL STATE")
print("================================")
print("Steps       :", list(model.steps.keys()))
print("Interactions:", list(model.interactions.keys()))
print("Constraints :", list(model.constraints.keys()))

total_e = sum(len(p.elements) for p in model.parts.values())
total_n = sum(len(p.nodes) for p in model.parts.values())
print("Total elements:", total_e)
print("Total nodes   :", total_n)
print("Total BCs     :", len(model.boundaryConditions.keys()))

print("\n✅ READY. Submit your job now.\n")