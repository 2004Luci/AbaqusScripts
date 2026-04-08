# -*- coding: utf-8 -*-

from abaqus import *

model = mdb.models['Model-1']

print("\n🔴 Removing ALL contact definitions...\n")

# ---------------------------------------
# 1. DELETE INTERACTIONS
# ---------------------------------------
for name in list(model.interactions.keys()):
    del model.interactions[name]
    print("Deleted interaction:", name)

# ---------------------------------------
# 2. DELETE INTERACTION PROPERTIES
# ---------------------------------------
for name in list(model.interactionProperties.keys()):
    del model.interactionProperties[name]
    print("Deleted interaction property:", name)

# ---------------------------------------
# 3. DELETE CONTACT CONTROLS (extra safety)
# ---------------------------------------
try:
    for name in list(model.contactControls.keys()):
        del model.contactControls[name]
        print("Deleted contact control:", name)
except:
    pass

print("\n✅ ALL CONTACT REMOVED COMPLETELY\n")