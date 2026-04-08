# -*- coding: utf-8 -*-
# safe-modal-step-setup.py

from abaqus import *
from abaqusConstants import *

model = mdb.models['Model-1']

print("\n--- Safe Modal Step Setup ---\n")

# -------------------------------------------------------
# STEP 1: Remove all BCs that reference non-Initial steps
# (BCs on 'Initial' are fine; BCs on deleted steps cause errors)
# -------------------------------------------------------
for bcName in list(model.boundaryConditions.keys()):
    try:
        bc = model.boundaryConditions[bcName]
        if bc.createStepName != 'Initial':
            del model.boundaryConditions[bcName]
            print("Deleted BC (non-Initial step):", bcName)
    except Exception as e:
        print("Could not delete BC:", bcName, "->", e)

# -------------------------------------------------------
# STEP 2: Delete all steps except Initial
# -------------------------------------------------------
for stepName in list(model.steps.keys()):
    if stepName != 'Initial':
        try:
            del model.steps[stepName]
            print("Deleted step:", stepName)
        except Exception as e:
            print("Could not delete step:", stepName, "->", e)

# -------------------------------------------------------
# STEP 3: Verify ModalStep is gone before recreating
# -------------------------------------------------------
if 'ModalStep' in model.steps.keys():
    print("WARNING: ModalStep still exists — will skip creation.")
else:
    model.FrequencyStep(
        name='ModalStep',
        previous='Initial',
        numEigen=10,
        eigensolver=LANCZOS,
        shift=1.0        # <-- frequency shift applied HERE at creation time
    )
    print("Created ModalStep with frequency shift = 1.0")

# -------------------------------------------------------
# STEP 4: Confirm final state
# -------------------------------------------------------
print("\nSteps currently in model:")
for s in model.steps.keys():
    print("  ", s)

print("\n✅ Done.\n")