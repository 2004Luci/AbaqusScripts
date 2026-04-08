from abaqus import *
model = mdb.models['Model-1']

print("\n--- Mesh Status ---")
for partName, part in model.parts.items():
    elemCount = len(part.elements)
    nodeCount = len(part.nodes)
    print("  ", partName, "| elements:", elemCount, "| nodes:", nodeCount)