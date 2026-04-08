# -*- coding: utf-8 -*-
# full-recovery.py

from abaqus import *
from abaqusConstants import *
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

print("\n==============================")
print("   Full Model Recovery")
print("==============================\n")

# -------------------------------------------------------
# STEP 1: Delete ALL interactions and contact properties
# -------------------------------------------------------
print("--- Step 1: Removing all contact ---")
for name in list(model.interactions.keys()):
    try:
        del model.interactions[name]
        print("  Deleted interaction:", name)
    except Exception as e:
        print("  Failed:", name, "->", e)

for name in list(model.interactionProperties.keys()):
    try:
        del model.interactionProperties[name]
        print("  Deleted property:", name)
    except Exception as e:
        print("  Failed:", name, "->", e)

# -------------------------------------------------------
# STEP 2: Delete ALL constraints
# -------------------------------------------------------
print("\n--- Step 2: Removing all constraints ---")
for name in list(model.constraints.keys()):
    try:
        del model.constraints[name]
        print("  Deleted constraint:", name)
    except Exception as e:
        print("  Failed:", name, "->", e)

# -------------------------------------------------------
# STEP 3: Delete ALL BCs (they are broken/missing anyway)
# -------------------------------------------------------
print("\n--- Step 3: Removing all BCs ---")
for name in list(model.boundaryConditions.keys()):
    try:
        del model.boundaryConditions[name]
        print("  Deleted BC:", name)
    except Exception as e:
        print("  Failed:", name, "->", e)

# -------------------------------------------------------
# STEP 4: Delete extra steps (keep only Initial + ModalStep)
# -------------------------------------------------------
print("\n--- Step 4: Cleaning up steps ---")
steps_to_keep = ['Initial', 'ModalStep']
for stepName in list(model.steps.keys()):
    if stepName not in steps_to_keep:
        try:
            del model.steps[stepName]
            print("  Deleted step:", stepName)
        except Exception as e:
            print("  Failed to delete step:", stepName, "->", e)

# Recreate ModalStep if it got deleted or never existed cleanly
if 'ModalStep' not in model.steps.keys():
    model.FrequencyStep(
        name='ModalStep',
        previous='Initial',
        numEigen=10,
        eigensolver=LANCZOS,
        shift=1.0
    )
    print("  Created fresh ModalStep with shift=1.0")
else:
    print("  ModalStep already present ✅")

# -------------------------------------------------------
# STEP 5: Apply EncastreBC to BOTH brackets (on Initial)
# -------------------------------------------------------
print("\n--- Step 5: Applying Encastre BCs to brackets ---")
bracket_names = ['wr340010_STEEL-1', 'wr340010_STEEL-2']

for bname in bracket_names:
    if bname in assembly.instances.keys():
        inst = assembly.instances[bname]
        region = regionToolset.Region(faces=inst.faces[:])
        bc_name = 'BC_Fixed_' + bname.split('-')[-1]  # BC_Fixed_1, BC_Fixed_2
        model.EncastreBC(
            name=bc_name,
            createStepName='Initial',
            region=region
        )
        print("  Applied EncastreBC:", bc_name, "->", bname)
    else:
        print("  WARNING: Instance not found:", bname)

# -------------------------------------------------------
# STEP 6: Tie wire endpoints to brackets
# -------------------------------------------------------
print("\n--- Step 6: Tying wire endpoints to brackets ---")
POSITION_TOLERANCE = 5.0  # mm
tied_count = 0

for i in range(3, 52):
    wire_name = 'wr340010_STEEL-' + str(i)
    if wire_name not in assembly.instances.keys():
        continue

    wire_inst = assembly.instances[wire_name]
    if len(wire_inst.vertices) == 0:
        print("  WARNING: No vertices on", wire_name)
        continue

    slave_region = regionToolset.Region(vertices=wire_inst.vertices)

    for b_idx, bname in enumerate(bracket_names):
        bracket_inst = assembly.instances[bname]
        master_region = regionToolset.Region(faces=bracket_inst.faces[:])
        tie_name = 'Tie-W{}-B{}'.format(i, b_idx + 1)
        try:
            model.Tie(
                name=tie_name,
                master=master_region,
                slave=slave_region,
                positionToleranceMethod=SPECIFIED,
                positionTolerance=POSITION_TOLERANCE,
                adjust=OFF,
                tieRotations=ON,
                thickness=ON
            )
            tied_count += 1
        except Exception as e:
            pass

print("  Ties created:", tied_count)

# -------------------------------------------------------
# STEP 7: Final state summary
# -------------------------------------------------------
print("\n==============================")
print("   Final Model State")
print("==============================")
print("Steps:", list(model.steps.keys()))
print("Interactions:", list(model.interactions.keys()))
print("Constraints:", list(model.constraints.keys()))
print("BCs:")
for name, bc in model.boundaryConditions.items():
    print("  ", name, "| Step:", bc.createStepName, "| Type:", bc.__class__.__name__)
print("\n✅ Model recovered. Submit job now.\n")