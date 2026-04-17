# -*- coding: utf-8 -*-
# WR3400_CLEAN_RESET.py
# Purpose: Reset model to a clean state (keep geometry, remove everything else)

from abaqus import *
from abaqusConstants import *
import regionToolset

MODEL_NAME = 'Model-1'

print("\n" + "="*55)
print("  CLEAN RESET SCRIPT — Removing all prior setup")
print("="*55 + "\n")

# -------------------------------------------------------
# STEP 1: Access model
# -------------------------------------------------------
if MODEL_NAME not in mdb.models.keys():
    print("ERROR: Model not found:", MODEL_NAME)
    raise SystemExit

model = mdb.models[MODEL_NAME]
assembly = model.rootAssembly

part_names = list(model.parts.keys())

print("  Parts detected:", len(part_names))

# -------------------------------------------------------
# STEP 2: Delete all meshes from parts
# -------------------------------------------------------
print("\n--- Removing meshes ---")

for pname in part_names:
    part = model.parts[pname]
    try:
        part.deleteMesh()
        print("  Mesh deleted:", pname)
    except:
        pass

# -------------------------------------------------------
# STEP 3: Remove section assignments
# -------------------------------------------------------
print("\n--- Removing section assignments ---")

for pname in part_names:
    part = model.parts[pname]
    try:
        part.sectionAssignments = ()
        print("  Cleared sections:", pname)
    except:
        pass

# -------------------------------------------------------
# STEP 4: Delete materials
# -------------------------------------------------------
print("\n--- Removing materials ---")

for mat in list(model.materials.keys()):
    try:
        del model.materials[mat]
        print("  Deleted material:", mat)
    except:
        pass

# -------------------------------------------------------
# STEP 5: Delete sections
# -------------------------------------------------------
print("\n--- Removing sections ---")

for sec in list(model.sections.keys()):
    try:
        del model.sections[sec]
        print("  Deleted section:", sec)
    except:
        pass

# -------------------------------------------------------
# STEP 6: Remove steps (except Initial)
# -------------------------------------------------------
print("\n--- Removing analysis steps ---")

for sname in list(model.steps.keys()):
    if sname != 'Initial':
        try:
            del model.steps[sname]
            print("  Deleted step:", sname)
        except:
            pass

# -------------------------------------------------------
# STEP 7: Remove interactions & constraints
# -------------------------------------------------------
print("\n--- Removing interactions & constraints ---")

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

for name in list(model.constraints.keys()):
    try:
        del model.constraints[name]
    except:
        pass

print("  All interactions/constraints removed")

# -------------------------------------------------------
# STEP 8: Remove boundary conditions
# -------------------------------------------------------
print("\n--- Removing boundary conditions ---")

for name in list(model.boundaryConditions.keys()):
    try:
        del model.boundaryConditions[name]
    except:
        pass

print("  All BCs removed")

# -------------------------------------------------------
# STEP 9: Clear assembly instances
# -------------------------------------------------------
print("\n--- Clearing assembly instances ---")

for inst in list(assembly.instances.keys()):
    try:
        del assembly.instances[inst]
        print("  Removed instance:", inst)
    except:
        pass

# Reset assembly
try:
    assembly.regenerate()
except:
    pass

# -------------------------------------------------------
# STEP 10: Remove jobs
# -------------------------------------------------------
print("\n--- Removing old jobs ---")

for job in list(mdb.jobs.keys()):
    try:
        del mdb.jobs[job]
        print("  Deleted job:", job)
    except:
        pass

# -------------------------------------------------------
# DONE
# -------------------------------------------------------
print("\n" + "="*55)
print("  MODEL RESET COMPLETE ✅")
print("  Geometry preserved. Ready for fresh setup.")
print("="*55 + "\n")