# -*- coding: utf-8 -*-
# clean-modal-setup.py
# Removes all contact, ties wire ENDPOINTS to bracket faces only

from abaqus import *
from abaqusConstants import *
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

print("\n==============================")
print("  Clean Modal Setup Script")
print("==============================\n")

# -------------------------------------------------------
# STEP 1: Nuke ALL interactions and contact properties
# -------------------------------------------------------
print("--- Step 1: Removing all contact ---")
for name in list(model.interactions.keys()):
    try:
        del model.interactions[name]
        print("  Deleted interaction:", name)
    except Exception as e:
        print("  Could not delete:", name, "->", e)

for name in list(model.interactionProperties.keys()):
    try:
        del model.interactionProperties[name]
        print("  Deleted property:", name)
    except Exception as e:
        print("  Could not delete:", name, "->", e)

# Also remove any existing tie constraints from previous bad run
for name in list(model.constraints.keys()):
    try:
        del model.constraints[name]
        print("  Deleted constraint:", name)
    except Exception as e:
        print("  Could not delete constraint:", name, "->", e)

print("  ✅ All contact and constraints removed.\n")

# -------------------------------------------------------
# STEP 2: Collect bracket face regions (master surfaces)
# -------------------------------------------------------
print("--- Step 2: Building bracket master surfaces ---")

bracket_names = ['wr340010_STEEL-1', 'wr340010_STEEL-2']

# Collect faces from BOTH brackets into one combined region
all_bracket_faces = []
for bname in bracket_names:
    inst = assembly.instances[bname]
    for face in inst.faces:
        all_bracket_faces.append(face)

# Build a combined Region from both bracket instances
bracket_face_seq_1 = assembly.instances[bracket_names[0]].faces[:]
bracket_face_seq_2 = assembly.instances[bracket_names[1]].faces[:]

print("  Bracket-1 faces:", len(bracket_face_seq_1))
print("  Bracket-2 faces:", len(bracket_face_seq_2))

# -------------------------------------------------------
# STEP 3: Tie ONLY wire endpoints (vertices) to brackets
# Wire beams touch brackets only at their ends — not along length
# -------------------------------------------------------
print("\n--- Step 3: Creating Tie constraints at wire endpoints ---")

POSITION_TOLERANCE = 3.0  # mm — adjust if wires still don't connect
tied_count = 0
skipped_count = 0

for i in range(3, 52):  # STEEL-3 to STEEL-51
    wire_name = 'wr340010_STEEL-' + str(i)
    
    if wire_name not in assembly.instances.keys():
        skipped_count += 1
        continue
    
    wire_inst = assembly.instances[wire_name]
    wire_vertices = wire_inst.vertices
    
    if len(wire_vertices) == 0:
        print("  WARNING: No vertices on", wire_name, "— skipping")
        skipped_count += 1
        continue
    
    # Slave region = wire endpoints (vertices only, NOT all edges)
    slave_region = regionToolset.Region(vertices=wire_vertices)
    
    # Try tying to bracket-1 first
    tied_this_wire = False
    
    for b_idx, bname in enumerate(bracket_names):
        bracket_inst = assembly.instances[bname]
        master_region = regionToolset.Region(
            faces=bracket_inst.faces[:]
        )
        
        tie_name = 'Tie-Wire{}-Brkt{}'.format(i, b_idx + 1)
        
        try:
            model.Tie(
                name=tie_name,
                master=master_region,
                slave=slave_region,
                positionToleranceMethod=SPECIFIED,
                positionTolerance=POSITION_TOLERANCE,
                adjust=OFF,          # OFF avoids nodal adjustment warnings
                tieRotations=ON,
                thickness=ON
            )
            tied_this_wire = True
        except Exception as e:
            # Not every wire touches every bracket — this is expected
            pass
    
    if tied_this_wire:
        tied_count += 1
    else:
        skipped_count += 1

print("\n  Wires successfully tied:", tied_count)
print("  Wires skipped (no nearby bracket):", skipped_count)

# -------------------------------------------------------
# STEP 4: Verify modal step exists with shift
# -------------------------------------------------------
print("\n--- Step 4: Verifying ModalStep ---")
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
    print("  ModalStep already exists ✅")

# -------------------------------------------------------
# STEP 5: Summary
# -------------------------------------------------------
print("\n==============================")
print("  Final Model State")
print("==============================")
print("  Steps:", list(model.steps.keys()))
print("  Interactions:", list(model.interactions.keys()))
print("  Constraints:", list(model.constraints.keys()))
print("\n✅ Model ready. Submit your job now.\n")