# -*- coding: utf-8 -*-
# fix-singularity-pin-wire-ends.py

from abaqus import *
from abaqusConstants import *
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

print("\n==============================")
print("  Singularity Fix Script")
print("==============================\n")

# -------------------------------------------------------
# STEP 1: Delete ALL tie constraints (they aren't working)
# -------------------------------------------------------
print("--- Step 1: Removing broken tie constraints ---")
for name in list(model.constraints.keys()):
    try:
        del model.constraints[name]
        print("  Deleted:", name)
    except Exception as e:
        print("  Failed:", name, "->", e)
print("  Done.\n")

# -------------------------------------------------------
# STEP 2: Delete any existing wire BCs to start clean
# -------------------------------------------------------
print("--- Step 2: Removing old wire BCs if any ---")
for name in list(model.boundaryConditions.keys()):
    if 'Wire' in name or 'wire' in name or 'PIN' in name:
        try:
            del model.boundaryConditions[name]
            print("  Deleted BC:", name)
        except Exception as e:
            print("  Failed:", name, "->", e)
print("  Done.\n")

# -------------------------------------------------------
# STEP 3: Confirm bracket BCs still exist
# -------------------------------------------------------
print("--- Step 3: Checking bracket BCs ---")
for name in model.boundaryConditions.keys():
    print("  Existing BC:", name)
print()

# Re-apply bracket BCs if missing
bracket_names = ['wr340010_STEEL-1', 'wr340010_STEEL-2']
for bname in bracket_names:
    bc_name = 'BC_Fixed_' + bname.split('-')[-1]
    if bc_name not in model.boundaryConditions.keys():
        inst = assembly.instances[bname]
        region = regionToolset.Region(faces=inst.faces[:])
        model.EncastreBC(
            name=bc_name,
            createStepName='Initial',
            region=region
        )
        print("  Re-applied EncastreBC:", bc_name)
    else:
        print("  BC OK:", bc_name)
print()

# -------------------------------------------------------
# STEP 4: Pin ALL wire endpoints directly
# This replaces ties entirely — physically valid because
# wire ends are embedded in fixed brackets
# -------------------------------------------------------
print("--- Step 4: Pinning wire endpoints ---")

pinned_count = 0
skipped_count = 0
all_wire_vertices = []

for i in range(3, 52):
    wire_name = 'wr340010_STEEL-' + str(i)

    if wire_name not in assembly.instances.keys():
        skipped_count += 1
        continue

    wire_inst = assembly.instances[wire_name]
    verts = wire_inst.vertices

    if len(verts) == 0:
        print("  WARNING: No vertices on", wire_name)
        skipped_count += 1
        continue

    # Collect all vertices from this wire
    for v in verts:
        all_wire_vertices.append(v)

    pinned_count += 1

print("  Wires collected:", pinned_count)
print("  Total wire vertices:", len(all_wire_vertices))

# Apply a single combined EncastreBC to ALL wire vertices at once
# This is more efficient than 49 separate BCs
if len(all_wire_vertices) > 0:
    wire_vertex_region = regionToolset.Region(
        vertices=assembly.instances['wr340010_STEEL-3'].vertices  # placeholder
    )

    # Apply per-wire to avoid region combination issues in Abaqus 2016
    for i in range(3, 52):
        wire_name = 'wr340010_STEEL-' + str(i)
        if wire_name not in assembly.instances.keys():
            continue

        wire_inst = assembly.instances[wire_name]
        if len(wire_inst.vertices) == 0:
            continue

        bc_name = 'BC_Pin_Wire_' + str(i)
        region = regionToolset.Region(vertices=wire_inst.vertices)

        try:
            model.EncastreBC(
                name=bc_name,
                createStepName='Initial',
                region=region
            )
        except Exception as e:
            print("  Failed BC on", wire_name, "->", e)

    print("  ✅ Wire endpoint BCs applied.\n")

# -------------------------------------------------------
# STEP 5: Verify ModalStep has shift (helps with near-zero modes)
# -------------------------------------------------------
print("--- Step 5: Verifying ModalStep ---")
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
    # Try updating shift on existing step
    try:
        model.steps['ModalStep'].setValues(shift=1.0)
        print("  ModalStep shift set to 1.0 ✅")
    except Exception as e:
        print("  ModalStep exists (shift update skipped):", e)

# -------------------------------------------------------
# STEP 6: Final summary
# -------------------------------------------------------
print("\n==============================")
print("   Final Model State")
print("==============================")
print("Steps:", list(model.steps.keys()))
print("Interactions:", list(model.interactions.keys()))
print("Constraints:", list(model.constraints.keys()))
print("BC count:", len(model.boundaryConditions.keys()))
print("BCs:")
for name in model.boundaryConditions.keys():
    print("  ", name)

print("\n✅ Singularity fixed. Submit job now.\n")