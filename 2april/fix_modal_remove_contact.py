# -*- coding: utf-8 -*-

from abaqus import *

model = mdb.models['Model-1']

print("\nRemoving contact definitions...\n")

# ---------------------------------------
# 1. DELETE ALL INTERACTIONS
# ---------------------------------------
for name in list(model.interactions.keys()):
    try:
        del model.interactions[name]
        print("Deleted interaction:", name)
    except:
        print("Failed to delete interaction:", name)

# ---------------------------------------
# 2. DELETE ALL INTERACTION PROPERTIES
# ---------------------------------------
for name in list(model.interactionProperties.keys()):
    try:
        del model.interactionProperties[name]
        print("Deleted interaction property:", name)
    except:
        print("Failed to delete property:", name)

# ---------------------------------------
# 3. CLEAN CONTACT PAIRS (if any leftover)
# ---------------------------------------
try:
    if 'GeneralContact' in model.interactions:
        del model.interactions['GeneralContact']
        print("Removed General Contact explicitly")
except:
    pass

print("\n✅ Contact completely removed.\n")
print("👉 Now re-submit the job (modal will run cleanly)")