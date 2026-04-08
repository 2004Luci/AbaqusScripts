from abaqus import *

model = mdb.models['Model-1']

print("\n--- Boundary Conditions ---")
for name, bc in model.boundaryConditions.items():
    print("  Name:", name)
    print("    Step:", bc.createStepName)
    print("    Type:", bc.__class__.__name__)

print("\n--- Steps ---")
for name in model.steps.keys():
    print("  ", name)

print("\n--- Interactions ---")
for name in model.interactions.keys():
    print("  ", name)

print("\n--- Constraints ---")
for name in model.constraints.keys():
    print("  ", name)