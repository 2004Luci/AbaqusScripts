# -*- coding: utf-8 -*-
# WR3400_COMPLETE_MODAL_FIXED.py

from abaqus import *
from abaqusConstants import *
import mesh
import regionToolset
import os
import time

# ============================================================
# CONFIGURATION
# ============================================================
JOB_NAME    = 'WR3400_Modal'
MODEL_NAME  = 'Model-1'
NUM_EIGEN   = 20
BRACKET_SEED = 4.0
WIRE_SEED    = 5.0
# ============================================================

print("\n" + "="*55)
print("  WR3400 Wire Rope Isolator — Full Modal Analysis")
print("="*55 + "\n")

# -------------------------------------------------------
# STEP 1: Use existing model
# -------------------------------------------------------
print("--- Step 1: Using existing model ---")

if MODEL_NAME not in mdb.models.keys():
    print("ERROR: Model not found:", MODEL_NAME)
    raise SystemExit

model = mdb.models[MODEL_NAME]

part_names = list(model.parts.keys())
print("  Parts found:", len(part_names))
for p in part_names:
    print("    -", p)
print()

# -------------------------------------------------------
# STEP 2: Identify brackets vs wires (FIXED)
# -------------------------------------------------------
print("--- Step 2: Identifying parts (fixed naming) ---")

bracket_parts = []
wire_parts    = []

BRACKET_NAMES = ['wr340010_STEEL-1', 'wr340010_STEEL-2']
WIRE_PREFIX   = 'wr340010_STEEL-'
WIRE_RANGE    = range(3, 52)

# Brackets
for name in BRACKET_NAMES:
    if name in part_names:
        bracket_parts.append(name)
    else:
        print("  WARNING: Missing bracket:", name)

# Wires
for i in WIRE_RANGE:
    name = WIRE_PREFIX + str(i)
    if name in part_names:
        wire_parts.append(name)
    else:
        print("  WARNING: Missing wire:", name)

print("  Brackets:", bracket_parts)
print("  Wires   :", len(wire_parts), "parts")

# Strict validation
if len(bracket_parts) != 2 or len(wire_parts) == 0:
    print("ERROR: Part identification failed. Check naming.")
    raise SystemExit

print()

# -------------------------------------------------------
# STEP 3: Materials
# -------------------------------------------------------
print("--- Step 3: Creating materials ---")

if 'StainlessSteel' not in model.materials.keys():
    mat = model.Material(name='StainlessSteel')
    mat.Density(table=((7.93e-6,),))
    mat.Elastic(table=((200000.0, 0.30),))
    print("  Created: StainlessSteel")

# -------------------------------------------------------
# STEP 4: Sections
# -------------------------------------------------------
print("\n--- Step 4: Creating sections ---")

if 'BracketSection' not in model.sections.keys():
    model.HomogeneousSolidSection(
        name='BracketSection',
        material='StainlessSteel'
    )

if 'WireSection' not in model.sections.keys():
    model.HomogeneousSolidSection(
        name='WireSection',
        material='StainlessSteel'
    )

# -------------------------------------------------------
# STEP 5: Mesh brackets
# -------------------------------------------------------
print("\n--- Step 5: Meshing brackets ---")

for bname in bracket_parts:
    part = model.parts[bname]

    try: part.deleteMesh()
    except: pass

    part.seedPart(size=BRACKET_SEED)
    part.setMeshControls(regions=part.cells, elemShape=TET, technique=FREE)

    elem = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
    part.setElementType(regions=(part.cells,), elemTypes=(elem,))
    part.generateMesh()

    region = regionToolset.Region(cells=part.cells)
    part.SectionAssignment(region=region, sectionName='BracketSection')

    print("  OK:", bname)

# -------------------------------------------------------
# STEP 6: Mesh wires
# -------------------------------------------------------
print("\n--- Step 6: Meshing wires ---")

for wname in wire_parts:
    part = model.parts[wname]

    if len(part.cells) == 0:
        continue

    try: part.deleteMesh()
    except: pass

    part.seedPart(size=WIRE_SEED, deviationFactor=0.15, minSizeFactor=0.1)
    part.setMeshControls(regions=part.cells, elemShape=TET, technique=FREE)

    elem = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
    part.setElementType(regions=(part.cells,), elemTypes=(elem,))
    part.generateMesh()

    region = regionToolset.Region(cells=part.cells)
    part.SectionAssignment(region=region, sectionName='WireSection')

print("  Wires meshed:", len(wire_parts))

# -------------------------------------------------------
# STEP 7: Assembly
# -------------------------------------------------------
print("\n--- Step 7: Assembly ---")

assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)

for pname in part_names:
    part = model.parts[pname]
    if len(part.cells) == 0:
        continue

    if pname not in assembly.instances.keys():
        assembly.Instance(name=pname, part=part, dependent=ON)

# -------------------------------------------------------
# STEP 8: Modal Step
# -------------------------------------------------------
print("\n--- Step 8: Modal step ---")

for s in list(model.steps.keys()):
    if s != 'Initial':
        del model.steps[s]

model.FrequencyStep(
    name='ModalStep',
    previous='Initial',
    numEigen=NUM_EIGEN,
    eigensolver=LANCZOS
)

# -------------------------------------------------------
# STEP 9: Cleanup interactions
# -------------------------------------------------------
print("\n--- Step 9: Cleanup ---")

for d in [model.interactions, model.constraints, model.interactionProperties]:
    for k in list(d.keys()):
        del d[k]

# -------------------------------------------------------
# STEP 10: Boundary conditions
# -------------------------------------------------------
print("\n--- Step 10: BCs ---")

for k in list(model.boundaryConditions.keys()):
    del model.boundaryConditions[k]

# Brackets fixed
for bname in bracket_parts:
    inst = assembly.instances[bname]
    region = regionToolset.Region(faces=inst.faces[:])

    model.EncastreBC(
        name='BC_' + bname,
        createStepName='Initial',
        region=region
    )

# Wires pinned
for wname in wire_parts:
    inst = assembly.instances[wname]
    if len(inst.vertices) == 0:
        continue

    region = regionToolset.Region(vertices=inst.vertices)

    model.EncastreBC(
        name='BC_' + wname,
        createStepName='Initial',
        region=region
    )

# -------------------------------------------------------
# STEP 11: Job
# -------------------------------------------------------
print("\n--- Step 11: Job ---")

if JOB_NAME in mdb.jobs.keys():
    del mdb.jobs[JOB_NAME]

job = mdb.Job(name=JOB_NAME, model=MODEL_NAME)
job.submit()
job.waitForCompletion()

print("\n✅ JOB COMPLETE")

# -------------------------------------------------------
# STEP 12: Read frequencies
# -------------------------------------------------------
print("\n--- Frequencies ---")

try:
    import odbAccess
    odb = session.openOdb(JOB_NAME + '.odb')

    for frame in odb.steps['ModalStep'].frames:
        if frame.frameId == 0:
            continue
        print(frame.description)

    odb.close()

except:
    print("Check .dat file")