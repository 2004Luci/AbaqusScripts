# -*- coding: utf-8 -*-
# WR3400_COMPLETE_MODAL.py
# End-to-end: mesh -> BCs -> modal job -> frequency results

from abaqus import *
from abaqusConstants import *
import mesh
import regionToolset
import os
import time

# ============================================================
# CONFIGURATION — EDIT THESE BEFORE RUNNING
# ============================================================
JOB_NAME    = 'WR3400_Modal'
MODEL_NAME  = 'Model-1'
NUM_EIGEN   = 20          # number of modes to extract
BRACKET_SEED = 5.0        # mm — bracket mesh seed
WIRE_SEED    = 0.15       # mm — wire mesh seed
# ============================================================

print("\n" + "="*55)
print("  WR3400 Wire Rope Isolator — Full Modal Analysis")
print("="*55 + "\n")

# -------------------------------------------------------
# STEP 1: Use existing model
# -------------------------------------------------------
print("--- Step 1: Using existing model ---")

if MODEL_NAME not in mdb.models.keys():
    print("ERROR: Model not found:", MODEL_NAME)
    print("Please make sure the imported geometry is already present in the model database.")
    raise SystemExit

model = mdb.models[MODEL_NAME]

part_names = list(model.parts.keys())
print("  Parts found:", len(part_names))
for p in part_names:
    print("    -", p)
print()

# -------------------------------------------------------
# STEP 2: Identify brackets vs wires
# -------------------------------------------------------
print("--- Step 2: Identifying parts ---")

bracket_parts = []
wire_parts    = []

for pname in part_names:
    part = model.parts[pname]
    # Brackets have many more cells/faces than wires
    # Wires are small solid cylinders with few faces
    n_cells = len(part.cells)
    n_faces = len(part.faces)
    if n_cells == 0:
        print("  WARNING: No cells in", pname, "— skipping")
        continue
    # Heuristic: brackets have more faces (complex shape)
    # wires are small — use part name if available
    pname_lower = pname.lower()
    if 'steel-1' in pname_lower or 'steel-2' in pname_lower:
        bracket_parts.append(pname)
    else:
        wire_parts.append(pname)

# Fallback if naming is different in imported STEP
if len(bracket_parts) == 0 or len(wire_parts) == 0:
    print("  Name-based detection failed. Using face-count heuristic.")
    bracket_parts = []
    wire_parts    = []
    parts_by_faces = sorted(
        [(pname, len(model.parts[pname].faces)) for pname in part_names
         if len(model.parts[pname].cells) > 0],
        key=lambda x: x[1],
        reverse=True
    )
    # Top 2 by face count = brackets
    for i, (pname, nf) in enumerate(parts_by_faces):
        if i < 2:
            bracket_parts.append(pname)
        else:
            wire_parts.append(pname)

print("  Brackets:", bracket_parts)
print("  Wires   :", len(wire_parts), "parts")
print()

# -------------------------------------------------------
# STEP 3: Create materials
# -------------------------------------------------------
print("--- Step 3: Creating materials ---")

if 'StainlessSteel' not in model.materials.keys():
    mat = model.Material(name='StainlessSteel')
    mat.Density(table=((7.93e-6,),))
    mat.Elastic(table=((200000.0, 0.30),))
    print("  Created: StainlessSteel")
else:
    print("  Exists : StainlessSteel ✅")

# -------------------------------------------------------
# STEP 4: Create sections
# -------------------------------------------------------
print("\n--- Step 4: Creating sections ---")

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
# STEP 5: Mesh brackets
# -------------------------------------------------------
print("\n--- Step 5: Meshing brackets ---")

for bname in bracket_parts:
    part = model.parts[bname]
    cells = part.cells
    try:
        part.deleteMesh()
    except:
        pass
    try:
        part.seedPart(
            size=BRACKET_SEED,
            deviationFactor=0.15,
            minSizeFactor=0.1
        )
        part.setMeshControls(
            regions=cells,
            elemShape=TET,
            technique=FREE
        )
        e1 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
        part.setElementType(regions=(cells,), elemTypes=(e1,))
        part.generateMesh()

        # Assign section
        region = regionToolset.Region(cells=part.cells)
        part.SectionAssignment(
            region=region,
            sectionName='BracketSection'
        )
        print("  OK:", bname,
              "| elems:", len(part.elements),
              "| nodes:", len(part.nodes))
    except Exception as e:
        print("  FAILED:", bname, "->", str(e))

# -------------------------------------------------------
# STEP 6: Mesh wires
# -------------------------------------------------------
print("\n--- Step 6: Meshing wires ---")

wire_ok   = 0
wire_fail = 0

for wname in wire_parts:
    part = model.parts[wname]
    cells = part.cells
    if len(cells) == 0:
        wire_fail += 1
        continue
    try:
        part.deleteMesh()
    except:
        pass
    try:
        part.seedPart(
            size=WIRE_SEED,
            deviationFactor=0.1,
            minSizeFactor=0.05
        )
        part.setMeshControls(
            regions=cells,
            elemShape=TET,
            technique=FREE
        )
        e1 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
        part.setElementType(regions=(cells,), elemTypes=(e1,))
        part.generateMesh()

        # Assign section
        region = regionToolset.Region(cells=part.cells)
        part.SectionAssignment(
            region=region,
            sectionName='WireSection'
        )
        wire_ok += 1
    except Exception as e:
        print("  FAILED:", wname, "->", str(e))
        wire_fail += 1

print("  Wires meshed OK:", wire_ok, "/", len(wire_parts))
print("  Failed         :", wire_fail, "/", len(wire_parts))

# -------------------------------------------------------
# STEP 7: Create assembly instances
# -------------------------------------------------------
print("\n--- Step 7: Creating assembly instances ---")

assembly = model.rootAssembly
assembly.DatumCsysByDefault(CARTESIAN)

for pname in part_names:
    if pname not in assembly.instances.keys():
        try:
            part = model.parts[pname]
            if len(part.cells) > 0:
                assembly.Instance(
                    name=pname,
                    part=part,
                    dependent=ON
                )
                print("  Instanced:", pname)
        except Exception as e:
            print("  Instance failed:", pname, "->", str(e))
    else:
        print("  Already instanced:", pname)

# -------------------------------------------------------
# STEP 8: Clean up steps
# -------------------------------------------------------
print("\n--- Step 8: Setting up ModalStep ---")

# Remove all non-Initial steps
for sname in list(model.steps.keys()):
    if sname != 'Initial':
        try:
            del model.steps[sname]
            print("  Deleted step:", sname)
        except Exception as e:
            print("  Could not delete:", sname, "->", str(e))

# Create fresh ModalStep
model.FrequencyStep(
    name='ModalStep',
    previous='Initial',
    numEigen=NUM_EIGEN,
    eigensolver=LANCZOS,
    shift=1.0
)
print("  Created: ModalStep | numEigen:", NUM_EIGEN, "| shift=1.0 ✅")

# -------------------------------------------------------
# STEP 9: Remove all interactions and constraints
# -------------------------------------------------------
print("\n--- Step 9: Removing contact/constraints ---")

for name in list(model.interactions.keys()):
    try: del model.interactions[name]
    except: pass

for name in list(model.interactionProperties.keys()):
    try: del model.interactionProperties[name]
    except: pass

for name in list(model.constraints.keys()):
    try: del model.constraints[name]
    except: pass

print("  All contact and constraints removed ✅")

# -------------------------------------------------------
# STEP 10: Apply boundary conditions
# -------------------------------------------------------
print("\n--- Step 10: Applying boundary conditions ---")

# Remove all existing BCs first
for name in list(model.boundaryConditions.keys()):
    try: del model.boundaryConditions[name]
    except: pass

# Encastre on bracket faces
for bname in bracket_parts:
    if bname in assembly.instances.keys():
        inst = assembly.instances[bname]
        region = regionToolset.Region(faces=inst.faces[:])
        bc_name = 'BC_Bracket_' + bname.replace(' ', '_')
        model.EncastreBC(
            name=bc_name,
            createStepName='Initial',
            region=region
        )
        print("  EncastreBC on bracket:", bname, "✅")

# Encastre on wire endpoints (vertices)
pin_count = 0
for wname in wire_parts:
    if wname not in assembly.instances.keys():
        continue
    inst = assembly.instances[wname]
    if len(inst.vertices) == 0:
        continue
    try:
        region = regionToolset.Region(vertices=inst.vertices)
        model.EncastreBC(
            name='BC_Pin_' + wname.replace(' ', '_'),
            createStepName='Initial',
            region=region
        )
        pin_count += 1
    except Exception as e:
        pass

print("  EncastreBC on wire endpoints:", pin_count, "/", len(wire_parts), "✅")

# -------------------------------------------------------
# STEP 11: Pre-submit model state check
# -------------------------------------------------------
print("\n--- Step 11: Pre-submit check ---")

total_e = sum(len(model.parts[p].elements) for p in part_names
              if len(model.parts[p].cells) > 0)
total_n = sum(len(model.parts[p].nodes) for p in part_names
              if len(model.parts[p].cells) > 0)
total_bc = len(model.boundaryConditions.keys())

print("  Steps       :", list(model.steps.keys()))
print("  Interactions:", list(model.interactions.keys()))
print("  Constraints :", list(model.constraints.keys()))
print("  Total elems :", total_e)
print("  Total nodes :", total_n)
print("  Total BCs   :", total_bc)

if total_bc < 2:
    print("  WARNING: Very few BCs — check bracket/wire identification above")
if total_e == 0:
    print("  ERROR: No elements — mesh generation failed")
    raise SystemExit

# -------------------------------------------------------
# STEP 12: Create and submit job
# -------------------------------------------------------
print("\n--- Step 12: Submitting job ---")

# Delete old job if exists
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
# STEP 13: Extract and print frequency results
# -------------------------------------------------------
print("--- Step 13: Extracting frequency results ---")
print("="*55)

try:
    import visualization
    import odbAccess

    odb_path = JOB_NAME + '.odb'
    odb = session.openOdb(name=odb_path)

    freq_step = odb.steps['ModalStep']
    frames    = freq_step.frames

    print("\n  MODE FREQUENCIES — WR3400 Wire Rope Isolator")
    print("  " + "-"*40)
    print("  {:>6}  {:>15}  {:>15}".format("Mode", "Freq (Hz)", "Freq (rad/s)"))
    print("  " + "-"*40)

    freq_results = []
    for frame in frames:
        if frame.frameId == 0:
            continue  # skip initial frame
        desc = frame.description
        # Abaqus frame description contains frequency info
        # Format: "Mode 1: Value = X, Freq = Y, ..."
        try:
            freq_hz = None
            # Try reading from frame description
            if 'Freq' in desc or 'freq' in desc:
                parts_desc = desc.replace(',', ' ').split()
                for idx, token in enumerate(parts_desc):
                    if 'freq' in token.lower() and idx+1 < len(parts_desc):
                        try:
                            freq_hz = float(parts_desc[idx+2])
                            break
                        except:
                            pass
            # Alternative: read eigenvalue and convert
            if freq_hz is None:
                import math
                # eigenvalue = omega^2, omega in rad/s
                # Try to parse from description
                if 'EigenValue' in desc or 'Value' in desc:
                    parts_desc = desc.replace('=','= ').split()
                    for idx, token in enumerate(parts_desc):
                        if token == '=' and idx > 0:
                            try:
                                val = float(parts_desc[idx+1])
                                if val > 0:
                                    freq_hz = math.sqrt(val) / (2 * math.pi)
                                    break
                            except:
                                pass

            if freq_hz is not None and freq_hz <= 5000.0:
                freq_results.append((frame.frameId, freq_hz))
                print("  {:>6}  {:>15.4f}  {:>15.4f}".format(
                    frame.frameId,
                    freq_hz,
                    freq_hz * 2 * 3.14159
                ))
        except Exception as e:
            print("  Frame", frame.frameId, "parse error:", str(e))

    print("  " + "-"*40)
    print("\n  Total modes extracted up to 5000 Hz:", len(freq_results))

    if len(freq_results) == 0:
        print("\n  NOTE: Could not auto-parse frequencies.")
        print("  Please open the .odb in Abaqus Viewer to view results,")
        print("  OR check the .dat file for the frequency table.")
        print("  DAT file location:", os.getcwd(), "/", JOB_NAME + ".dat")

    odb.close()

except Exception as e:
    print("  ODB read error:", str(e))
    print("\n  *** Frequencies are in the .dat file ***")
    print("  Open:", JOB_NAME + ".dat")
    print("  Search for: EIGENVALUE  FREQUENCY")

# -------------------------------------------------------
# STEP 14: Also read .dat file directly as backup
# -------------------------------------------------------
print("\n--- Step 14: Reading .dat file (backup) ---")

dat_file = JOB_NAME + '.dat'
if os.path.exists(dat_file):
    try:
        with open(dat_file, 'r') as f:
            lines = f.readlines()

        in_freq_block = False
        print("\n  FREQUENCY TABLE FROM .DAT FILE:")
        print("  " + "-"*55)

        for i, line in enumerate(lines):
            if 'EIGENVALUE' in line and 'FREQUENCY' in line:
                in_freq_block = True
                print("  " + line.rstrip())
                continue
            if in_freq_block:
                stripped = line.strip()
                if stripped == '':
                    if in_freq_block:
                        in_freq_block = False
                    continue
                if any(c.isdigit() for c in stripped):
                    print("  " + line.rstrip())
                else:
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