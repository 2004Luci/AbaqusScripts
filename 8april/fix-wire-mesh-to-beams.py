# -*- coding: utf-8 -*-
# fix-wire-mesh-to-beams.py
# Wires are currently solid tets — convert to B31 beams

from abaqus import *
from abaqusConstants import *
import mesh
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

print("\n==============================")
print("  Wire Mesh Fix: Solid -> B31")
print("==============================\n")

WIRE_SEED = 5.0  # mm element length along wire

fixed_count = 0
failed_count = 0

for i in range(3, 52):
    pname = 'wr340010_STEEL-' + str(i)
    if pname not in model.parts.keys():
        continue

    part = model.parts[pname]

    # Step A: Delete existing solid mesh
    try:
        part.deleteMesh()
    except:
        pass

    # Step B: Set element type to B31 (linear beam, 2 nodes)
    edges = part.edges
    if len(edges) == 0:
        print("  WARNING: No edges on", pname)
        failed_count += 1
        continue

    try:
        elemType_beam = mesh.ElemType(
            elemCode=B31,
            elemLibrary=STANDARD
        )
        part.setElementType(
            regions=(edges,),
            elemTypes=(elemType_beam,)
        )
    except Exception as e:
        print("  ElemType failed on", pname, "->", e)
        failed_count += 1
        continue

    # Step C: Seed and mesh
    try:
        part.seedPart(
            size=WIRE_SEED,
            deviationFactor=0.1,
            minSizeFactor=0.1
        )
        part.generateMesh()

        n_elem = len(part.elements)
        n_node = len(part.nodes)
        ratio = round(float(n_node) / float(n_elem), 2) if n_elem > 0 else 0

        if ratio <= 1.2:
            print("  OK  ", pname,
                  "| elems:", n_elem,
                  "| nodes:", n_node,
                  "| ratio:", ratio, "<- beam ✅")
            fixed_count += 1
        else:
            print("  WARN", pname,
                  "| elems:", n_elem,
                  "| nodes:", n_node,
                  "| ratio:", ratio, "<- still solid?")
            failed_count += 1

    except Exception as e:
        print("  Mesh failed on", pname, "->", e)
        failed_count += 1

print("\n  Fixed:", fixed_count, "/ 49")
print("  Failed:", failed_count, "/ 49")

# -------------------------------------------------------
# Verify BCs still intact
# -------------------------------------------------------
print("\n--- BC Check ---")
print("  Total BCs:", len(model.boundaryConditions.keys()))
bracket_bcs = [n for n in model.boundaryConditions.keys()
               if 'Fixed' in n]
wire_bcs = [n for n in model.boundaryConditions.keys()
            if 'Pin' in n]
print("  Bracket BCs:", len(bracket_bcs))
print("  Wire pin BCs:", len(wire_bcs))

# Re-apply wire endpoint BCs if they got wiped
if len(wire_bcs) == 0:
    print("\n  Wire BCs missing — reapplying...")
    pin_count = 0
    for i in range(3, 52):
        wname = 'wr340010_STEEL-' + str(i)
        if wname not in assembly.instances.keys():
            continue
        inst = assembly.instances[wname]
        if len(inst.vertices) == 0:
            continue
        try:
            region = regionToolset.Region(vertices=inst.vertices)
            model.EncastreBC(
                name='BC_Pin_Wire_' + str(i),
                createStepName='Initial',
                region=region
            )
            pin_count += 1
        except Exception as e:
            pass
    print("  Wire BCs reapplied:", pin_count)

# -------------------------------------------------------
# Final summary
# -------------------------------------------------------
print("\n==============================")
print("   Final Summary")
print("==============================")

total_e = 0
total_n = 0
for pname, part in model.parts.items():
    total_e += len(part.elements)
    total_n += len(part.nodes)

print("Total elements (all parts):", total_e)
print("Total nodes    (all parts):", total_n)
print("Steps:", list(model.steps.keys()))
print("Interactions:", list(model.interactions.keys()))
print("Constraints:", list(model.constraints.keys()))
print("Total BCs:", len(model.boundaryConditions.keys()))
print("\n✅ Submit the job now.\n")