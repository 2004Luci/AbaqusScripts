from abaqus import *

model = mdb.models['Model-1']

print("\n--- BCs ---")
for name in model.boundaryConditions.keys():
    print("  ", name)

print("\n--- Steps ---")
for name in model.steps.keys():
    print("  ", name)

print("\n--- Constraints count ---")
print("  ", len(model.constraints.keys()))