# -*- coding: utf-8 -*-
# WR3400_COMPLETE_MODAL_FIXED.py
# End-to-end: clean existing setup -> mesh -> BCs -> modal job -> frequency results

from abaqus import *
from abaqusConstants import *
import mesh
import regionToolset
import os
import math

# ============================================================
# CONFIGURATION
# ============================================================
JOB_NAME     = 'WR3400_Modal'
MODEL_NAME   = 'Model-1'
NUM_EIGEN    = 20
BRACKET_SEED = 4.0
WIRE_SEED    = 2.5

BRACKET_NAMES = ['wr340010_STEEL-1', 'wr340010_STEEL-2']
WIRE_PREFIX    = 'wr340010_STEEL-'
WIRE_RANGE     = range(3, 52)   # 3..51 inclusive
# ============================================================

print("\n" + "="*55)
print("  WR3400 Wire Rope Isolator — Full Modal Analysis")
print("="*55 + "\n")

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------
def safe_delete_keys(container):
    try:
        for k in list(container.keys()):
            try:
                del container[k]
            except:
                pass
    except:
        pass

def clear_part_section_assignments(part):
    """
    Remove any old section assignments left from prior runs.
    This is critical when the model was reset but part-level assignments remain.
    """
    try:
        for k in list(part.sectionAssignments.keys()):
            try:
                del part.sectionAssignments[k]
            except:
                pass
    except:
        pass

def delete_part_mesh(part):
    try:
        part.deleteMesh()
    except:
        pass

def nearest_node(instance, point):
    """
    Return the nearest node object in an instance to a given 3D point.
    """
    px, py, pz = point
    best_node = None
    best_d2 = None

    for node in instance.nodes:
        x, y, z = node.coordinates
        d2 = (x - px)**2 + (y - py)**2 + (z - pz)**2
        if best_d2 is None or d2 < best_d2:
            best_d2 = d2
            best_node = node

    return best_node, best_d2

# -------------------------------------------------------
# STEP 1: Use existing model
# -------------------------------------------------------
print("--- Step 1: Using existing model ---")

if MODEL_NAME not in mdb.models.keys():
    print("ERROR: Model not found:", MODEL_NAME)
    raise SystemExit

model = mdb.models[MODEL_NAME]
part_names = list(model.parts.keys())

print("  Parts found:", len(part_names))
for p in part_names:
    print("    -", p)
print()

# -------------------------------------------------------
# STEP 2: Identify brackets vs wires (fixed naming)
# -------------------------------------------------------
print("--- Step 2: Identifying parts (fixed naming) ---")

bracket_parts = []
wire_parts = []

for name in BRACKET_NAMES:
    if name in part_names:
        bracket_parts.append(name)
    else:
        print("  WARNING: Missing bracket:", name)

for i in WIRE_RANGE:
    name = WIRE_PREFIX + str(i)
    if name in part_names:
        wire_parts.append(name)
    else:
        print("  WARNING: Missing wire:", name)

print("  Brackets:", bracket_parts)
print("  Wires   :", len(wire_parts), "parts")

if len(bracket_parts) != 2:
    print("ERROR: Expected exactly 2 bracket parts.")
    raise SystemExit
if len(wire_parts) != 49:
    print("WARNING: Expected 49 wires, found", len(wire_parts))
print()

# -------------------------------------------------------
# STEP 3: Remove old setup that can break reruns
# -------------------------------------------------------
print("--- Step 3: Clearing old setup ---")

# Remove all old section assignments on parts
for pname in part_names:
    clear_part_section_assignments(model.parts[pname])

# Remove old meshes
for pname in part_names:
    delete_part_mesh(model.parts[pname])

# Remove old jobs
safe_delete_keys(mdb.jobs)

# Remove all steps except Initial
for sname in list(model.steps.keys()):
    if sname != 'Initial':
        try:
            del model.steps[sname]
        except:
            pass

# Remove interactions / constraints / BCs
safe_delete_keys(model.interactions)
safe_delete_keys(model.interactionProperties)
safe_delete_keys(model.constraints)
safe_delete_keys(model.boundaryConditions)

print("  Cleared old assignments, mesh, steps, interactions, constraints, BCs.\n")

# -------------------------------------------------------
# STEP 4: Create material
# -------------------------------------------------------
print("--- Step 4: Creating material ---")

if 'StainlessSteel' not in model.materials.keys():
    mat = model.Material(name='StainlessSteel')
    mat.Density(table=((7.93e-6,),))
    mat.Elastic(table=((200000.0, 0.30),))
    print("  Created: StainlessSteel")
else:
    print("  Exists : StainlessSteel ✅")

# -------------------------------------------------------
# STEP 5: Create sections
# -------------------------------------------------------
print("\n--- Step 5: Creating sections ---")

if 'BracketSection' not in model.sections.keys():
    model.HomogeneousSolidSection(
        name='BracketSection',
        material='StainlessSteel',
        thickness=None
    )
    print("  Created: BracketSection")
else:
    print("  Exists : BracketSection ✅")

if 'WireSection' not in model.sections.keys():
    model.HomogeneousSolidSection(
        name='WireSection',
        material='StainlessSteel',
        thickness=None
    )
    print("  Created: WireSection")
else:
    print("  Exists : WireSection ✅")

# -------------------------------------------------------
# STEP 6: Mesh brackets
# -------------------------------------------------------
print("\n--- Step 6: Meshing brackets ---")

for bname in bracket_parts:
    part = model.parts[bname]
    clear_part_section_assignments(part)
    delete_part_mesh(part)

    try:
        part.seedPart(size=BRACKET_SEED, deviationFactor=0.15, minSizeFactor=0.1)
        part.setMeshControls(
            regions=part.cells,
            elemShape=TET,
            technique=FREE
        )
        e1 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
        part.setElementType(regions=(part.cells,), elemTypes=(e1,))
        part.generateMesh()

        region = regionToolset.Region(cells=part.cells)
        part.SectionAssignment(region=region, sectionName='BracketSection')

        print("  OK:", bname, "| elems:", len(part.elements), "| nodes:", len(part.nodes))
    except Exception as e:
        print("  FAILED:", bname, "->", str(e))

# -------------------------------------------------------
# STEP 7: Mesh wires
# -------------------------------------------------------
print("\n--- Step 7: Meshing wires ---")

# wire_ok = 0
# wire_fail = 0

# for wname in wire_parts:
#     part = model.parts[wname]
#     clear_part_section_assignments(part)
#     delete_part_mesh(part)

#     if len(part.cells) == 0:
#         print("  WARNING: No cells in", wname)
#         wire_fail += 1
#         continue

#     try:
#         part.seedPart(size=WIRE_SEED, deviationFactor=0.1, minSizeFactor=0.05)
#         part.setMeshControls(
#             regions=part.cells,
#             elemShape=TET,
#             technique=FREE
#         )
#         e1 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
#         part.setElementType(regions=(part.cells,), elemTypes=(e1,))
#         part.generateMesh()

#         region = regionToolset.Region(cells=part.cells)
#         part.SectionAssignment(region=region, sectionName='WireSection')

#         wire_ok += 1
#     except Exception as e:
#         print("  FAILED:", wname, "->", str(e))
#         wire_fail += 1

# print("  Wires meshed OK:", wire_ok, "/", len(wire_parts))
# print("  Failed         :", wire_fail, "/", len(wire_parts))

# -------------------------------------------------------
# STEP 7: Mesh wires (FIXED + DEBUG + FALLBACK)
# -------------------------------------------------------
print("\n--- Step 7: Meshing wires (robust) ---")

wire_ok = 0
wire_fail = 0

for wname in wire_parts:
    part = model.parts[wname]
    print("\n  Meshing:", wname)

    clear_part_section_assignments(part)
    delete_part_mesh(part)

    if len(part.cells) == 0:
        print("    ❌ No solid cells")
        wire_fail += 1
        continue

    try:
        # ---- PRIMARY MESH ----
        part.seedPart(
            size=WIRE_SEED,              # FIXED
            deviationFactor=0.1,
            minSizeFactor=0.05
        )

        part.setMeshControls(
            regions=part.cells,
            elemShape=TET,
            technique=FREE
        )

        elem = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
        part.setElementType(regions=(part.cells,), elemTypes=(elem,))

        part.generateMesh()

        # ---- VALIDATION ----
        if len(part.elements) == 0:
            raise Exception("No elements generated")

        # Assign section
        region = regionToolset.Region(cells=part.cells)
        part.SectionAssignment(region=region, sectionName='WireSection')

        print("    ✅ OK | elems:", len(part.elements))
        wire_ok += 1

    except Exception as e:
        print("    ⚠️ Primary mesh failed:", str(e))

        # ---- FALLBACK MESH ----
        try:
            print("    🔁 Retrying with finer mesh...")

            part.deleteMesh()

            part.seedPart(
                size=WIRE_SEED * 0.5,   # finer
                deviationFactor=0.05,
                minSizeFactor=0.02
            )

            part.generateMesh()

            if len(part.elements) == 0:
                raise Exception("Fallback also failed")

            region = regionToolset.Region(cells=part.cells)
            part.SectionAssignment(region=region, sectionName='WireSection')

            print("    ✅ Fallback OK | elems:", len(part.elements))
            wire_ok += 1

        except Exception as e2:
            print("    ❌ FAILED:", str(e2))
            wire_fail += 1

print("\n  Wires meshed OK:", wire_ok, "/", len(wire_parts))
print("  Failed         :", wire_fail, "/", len(wire_parts))

# -------------------------------------------------------
# STEP 8: Create assembly instances
# -------------------------------------------------------
print("\n--- Step 8: Creating assembly instances ---")

assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)

for pname in part_names:
    part = model.parts[pname]
    if len(part.cells) == 0:
        continue

    if pname not in assembly.instances.keys():
        try:
            assembly.Instance(name=pname, part=part, dependent=ON)
            print("  Instanced:", pname)
        except Exception as e:
            print("  Instance failed:", pname, "->", str(e))
    else:
        print("  Already instanced:", pname)

# -------------------------------------------------------
# STEP 9: Create modal step
# -------------------------------------------------------
print("\n--- Step 9: Setting up ModalStep ---")

# Keep only Initial
for sname in list(model.steps.keys()):
    if sname != 'Initial':
        try:
            del model.steps[sname]
        except:
            pass

model.FrequencyStep(
    name='ModalStep',
    previous='Initial',
    numEigen=NUM_EIGEN,
    eigensolver=LANCZOS,
    shift=1.0
)
print("  Created: ModalStep | numEigen:", NUM_EIGEN, "| shift=1.0 ✅")

# -------------------------------------------------------
# STEP 10: Remove any leftover interactions/constraints
# -------------------------------------------------------
print("\n--- Step 10: Removing contact/constraints ---")

safe_delete_keys(model.interactions)
safe_delete_keys(model.interactionProperties)
safe_delete_keys(model.constraints)

print("  All contact and constraints removed ✅")

# -------------------------------------------------------
# STEP 11: Apply boundary conditions
# -------------------------------------------------------
print("\n--- Step 11: Applying boundary conditions ---")

safe_delete_keys(model.boundaryConditions)

# Brackets: fix all faces
for bname in bracket_parts:
    if bname not in assembly.instances.keys():
        continue

    inst = assembly.instances[bname]
    try:
        region = regionToolset.Region(faces=inst.faces[:])
        model.EncastreBC(
            name='BC_Bracket_' + bname.replace('-', '_'),
            createStepName='Initial',
            region=region
        )
        print("  EncastreBC on bracket:", bname, "✅")
    except Exception as e:
        print("  Bracket BC failed:", bname, "->", str(e))

# Wires: pin one node per wire using nearest mesh node to the first geometric vertex
# This avoids the _PICKEDSET / undefined node-set errors seen in your log.
pin_ok = 0
pin_fail = 0

for wname in wire_parts:
    if wname not in assembly.instances.keys():
        pin_fail += 1
        continue

    inst = assembly.instances[wname]

    try:
        if len(inst.vertices) == 0:
            print("  WARNING: no vertices on", wname)
            pin_fail += 1
            continue

        v = inst.vertices[0]
        v_point = v.pointOn[0]

        node, d2 = nearest_node(inst, v_point)
        if node is None:
            print("  WARNING: no mesh node found near", wname)
            pin_fail += 1
            continue

        set_name = 'PIN_' + wname.replace('-', '_')
        if set_name in assembly.sets.keys():
            try:
                del assembly.sets[set_name]
            except:
                pass

        assembly.Set(name=set_name, nodes=(node,))
        model.EncastreBC(
            name='BC_' + wname.replace('-', '_'),
            createStepName='Initial',
            region=assembly.sets[set_name]
        )

        pin_ok += 1
    except Exception as e:
        print("  Wire BC failed:", wname, "->", str(e))
        pin_fail += 1

print("  Wire pins OK   :", pin_ok, "/", len(wire_parts))
print("  Wire pins failed:", pin_fail, "/", len(wire_parts))

# -------------------------------------------------------
# STEP 12: Pre-submit model state check
# -------------------------------------------------------
print("\n--- Step 12: Pre-submit check ---")

total_e = sum(len(model.parts[p].elements) for p in part_names if len(model.parts[p].cells) > 0)
total_n = sum(len(model.parts[p].nodes) for p in part_names if len(model.parts[p].cells) > 0)
total_bc = len(model.boundaryConditions.keys())

print("  Steps       :", list(model.steps.keys()))
print("  Interactions :", list(model.interactions.keys()))
print("  Constraints  :", list(model.constraints.keys()))
print("  Total elems  :", total_e)
print("  Total nodes  :", total_n)
print("  Total BCs    :", total_bc)

if total_e == 0:
    print("ERROR: No elements generated.")
    raise SystemExit

# -------------------------------------------------------
# STEP 13: Create and submit job
# -------------------------------------------------------
print("\n--- Step 13: Submitting job ---")

if JOB_NAME in mdb.jobs.keys():
    try:
        del mdb.jobs[JOB_NAME]
    except:
        pass

job = mdb.Job(
    name=JOB_NAME,
    model=MODEL_NAME,
    description='WR3400 Modal Analysis',
    type=ANALYSIS,
    numCpus=1,
    numGPUs=0,
    memory=90,
    memoryUnits=PERCENTAGE,
    explicitPrecision=SINGLE,
    nodalOutputPrecision=SINGLE,
    echoPrint=OFF,
    modelPrint=OFF,
    contactPrint=OFF,
    historyPrint=OFF
)

job.submit(consistencyChecking=OFF)
print("  Job submitted:", JOB_NAME)
print("  Waiting for completion...\n")
job.waitForCompletion()
print("  Job finished!\n")

# -------------------------------------------------------
# STEP 14: Extract and print frequency results
# -------------------------------------------------------
print("--- Step 14: Extracting frequency results ---")
print("="*55)

try:
    import odbAccess
    odb = session.openOdb(name=JOB_NAME + '.odb')

    freq_step = odb.steps['ModalStep']
    frames = freq_step.frames

    print("\n  MODE FREQUENCIES — WR3400 Wire Rope Isolator")
    print("  " + "-"*40)
    print("  {:>6}  {:>15}  {:>15}".format("Mode", "Freq (Hz)", "Freq (rad/s)"))
    print("  " + "-"*40)

    freq_results = []
    for frame in frames:
        if frame.frameId == 0:
            continue

        desc = frame.description
        try:
            freq_hz = None

            # Try parsing frequency directly from description
            if 'Freq' in desc or 'freq' in desc:
                tokens = desc.replace(',', ' ').replace('=', ' = ').split()
                for idx, token in enumerate(tokens):
                    if token.lower().startswith('freq'):
                        for j in range(idx, min(idx + 6, len(tokens) - 1)):
                            try:
                                val = float(tokens[j + 1])
                                if val > 0:
                                    freq_hz = val
                                    break
                            except:
                                pass
                        if freq_hz is not None:
                            break

            # Fallback: parse eigenvalue and convert
            if freq_hz is None:
                if 'Value' in desc or 'Eigen' in desc:
                    tokens = desc.replace(',', ' ').replace('=', ' = ').split()
                    for idx, token in enumerate(tokens):
                        if token == '=' and idx + 1 < len(tokens):
                            try:
                                val = float(tokens[idx + 1])
                                if val > 0:
                                    freq_hz = math.sqrt(val) / (2.0 * math.pi)
                                    break
                            except:
                                pass

            if freq_hz is not None and freq_hz <= 5000.0:
                freq_results.append((frame.frameId, freq_hz))
                print("  {:>6}  {:>15.4f}  {:>15.4f}".format(
                    frame.frameId,
                    freq_hz,
                    freq_hz * 2.0 * math.pi
                ))
        except Exception as e:
            print("  Frame", frame.frameId, "parse error:", str(e))

    print("  " + "-"*40)
    print("\n  Total modes extracted up to 5000 Hz:", len(freq_results))

    if len(freq_results) == 0:
        print("\n  NOTE: Could not auto-parse frequencies.")
        print("  Please open the .odb in Abaqus Viewer,")
        print("  or check the .dat file for the frequency table.")

    odb.close()

except Exception as e:
    print("  ODB read error:", str(e))
    print("\n  *** Frequencies are in the .dat file ***")
    print("  Open:", JOB_NAME + ".dat")

# -------------------------------------------------------
# STEP 15: Read .dat file directly as backup
# -------------------------------------------------------
print("\n--- Step 15: Reading .dat file (backup) ---")

dat_file = JOB_NAME + '.dat'
if os.path.exists(dat_file):
    try:
        with open(dat_file, 'r') as f:
            lines = f.readlines()

        in_freq_block = False
        print("\n  FREQUENCY TABLE FROM .DAT FILE:")
        print("  " + "-"*55)

        for line in lines:
            if 'EIGENVALUE' in line and 'FREQUENCY' in line:
                in_freq_block = True
                print("  " + line.rstrip())
                continue

            if in_freq_block:
                stripped = line.strip()
                if stripped == '':
                    in_freq_block = False
                    continue
                print("  " + line.rstrip())

        print("  " + "-"*55)
    except Exception as e:
        print("  Could not read .dat:", str(e))
else:
    print("  .dat file not found at:", os.getcwd())
    print("  Check Abaqus working directory for:", dat_file)

# -------------------------------------------------------
# DONE
# -------------------------------------------------------
print("\n" + "="*55)
print("  ANALYSIS COMPLETE")
print("  Results in: " + JOB_NAME + ".odb  and  " + JOB_NAME + ".dat")
print("="*55 + "\n")