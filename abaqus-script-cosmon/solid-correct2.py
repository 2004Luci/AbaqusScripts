# =============================================================================
# WIRE ROPE 7x1 MODAL ANALYSIS - SOLID METHOD (FULL GEOMETRY)
# (No STEP import - assumes parts already imported manually as wr340010_7x1-N)
# =============================================================================

from abaqus import *
from abaqusConstants import *
from caeModules import *
import mesh
import os
import math

# ========================== USER INPUTS ======================================
WORK_DIR  = r'C:\Users\admin\Desktop\solid-results'

MAX_FREQ_HZ = 5000.0
MAX_MODES = 100

# Mesh sizes - wire MUST be < wire diameter for good quality
WIRE_SOLID_SEED = 0.4      # mm (wire dia ~0.8mm, so seed ~0.4mm)
PLATE_SOLID_SEED = 3.0     # mm

# Embedded region disabled - wires are mostly in free space, can't embed
# Instead we fix wire end faces (like a gripped wire rope)
USE_EMBEDDED_REGION = False

E_MODULUS = 200000.0       # MPa
POISSON = 0.3
DENSITY = 7.85e-9          # tonne/mm^3
# =============================================================================


def main():
    if not os.path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)
    os.chdir(WORK_DIR)

    model = mdb.models['Model-1']
    print('Found model with {} parts'.format(len(model.parts)))

    # ---------- STEP 1: Classify ----------
    solid_plate_parts, wire_parts = [], []
    for name in model.parts.keys():
        if len(model.parts[name].faces) > 10:
            solid_plate_parts.append(name)
        else:
            wire_parts.append(name)
    print('STEP 1: {} plates, {} wires (all as solids)'.format(
        len(solid_plate_parts), len(wire_parts)))

    # ---------- STEP 2: Material ----------
    print('STEP 2: Material and section...')
    mat = model.Material(name='Steel')
    mat.Elastic(table=((E_MODULUS, POISSON),))
    mat.Density(table=((DENSITY,),))
    model.HomogeneousSolidSection(name='SteelSolid', material='Steel', thickness=None)

    # ---------- STEP 3: Section assignment ----------
    print('STEP 3: Assigning section...')
    for name in model.parts.keys():
        p = model.parts[name]
        r = p.Set(cells=p.cells[:], name='AllCells')
        p.SectionAssignment(region=r, sectionName='SteelSolid',
                            offset=0.0, offsetType=MIDDLE_SURFACE,
                            offsetField='', thicknessAssignment=FROM_SECTION)

    # ---------- STEP 4: Assembly ----------
    print('STEP 4: Assembly...')
    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    for name in model.parts.keys():
        a.Instance(name=name+'-1', part=model.parts[name], dependent=ON)

    # ---------- STEP 5: Frequency step ----------
    print('STEP 5: Frequency step...')
    max_eig = (2.0 * math.pi * MAX_FREQ_HZ) ** 2
    model.FrequencyStep(name='ModalAnalysis', previous='Initial',
                        eigensolver=LANCZOS, numEigen=MAX_MODES,
                        maxEigen=max_eig,
                        description='Modal 7x1 solid up to {} Hz'.format(MAX_FREQ_HZ))

    # ---------- STEP 6: Mesh ----------
    print('STEP 6: Meshing (this can take a few minutes for thin wires)...')
    c3d10 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD)
    c3d6 = mesh.ElemType(elemCode=C3D6, elemLibrary=STANDARD)
    c3d4 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)

    # Mesh wires - use fine seed and quadratic tets for thin geometry
    total_wire_nodes = 0
    total_wire_elems = 0
    for wname in wire_parts:
        p = model.parts[wname]
        p.setMeshControls(regions=p.cells[:], elemShape=TET, technique=FREE)
        p.seedPart(size=WIRE_SOLID_SEED, deviationFactor=0.1, minSizeFactor=0.1)
        p.setElementType(regions=(p.cells[:],), elemTypes=(c3d10, c3d6, c3d4))
        p.generateMesh()
        total_wire_nodes += len(p.nodes)
        total_wire_elems += len(p.elements)
    print('  Wire nodes: {}, elements: {}'.format(total_wire_nodes, total_wire_elems))

    # Mesh plates
    total_plate_nodes = 0
    for pname in solid_plate_parts:
        p = model.parts[pname]
        p.setMeshControls(regions=p.cells[:], elemShape=TET, technique=FREE)
        p.seedPart(size=PLATE_SOLID_SEED)
        p.setElementType(regions=(p.cells[:],), elemTypes=(c3d10, c3d6, c3d4))
        p.generateMesh()
        total_plate_nodes += len(p.nodes)
    print('  Plate nodes: {}'.format(total_plate_nodes))
    print('  Total nodes: {}'.format(total_wire_nodes + total_plate_nodes))

    # ---------- STEP 7: BCs ----------
    print('STEP 7: Boundary conditions...')

    # Fix plate ends at X extremes
    for plate_name in solid_plate_parts:
        inst = a.instances[plate_name+'-1']
        p = model.parts[plate_name]
        bb = p.queryGeometry(printResults=False)
        bbox = bb['boundingBox']
        x_min, x_max = bbox[0][0], bbox[1][0]
        y_mid = bb['centroid'][1]
        short = plate_name.split('-')[-1]
        lf = inst.faces.findAt(((x_min, y_mid, 0.0),))
        rf = inst.faces.findAt(((x_max, y_mid, 0.0),))
        model.EncastreBC(name='Fix-P{}-L'.format(short), createStepName='Initial',
                         region=a.Set(faces=lf, name='P{}-Left'.format(short)))
        model.EncastreBC(name='Fix-P{}-R'.format(short), createStepName='Initial',
                         region=a.Set(faces=rf, name='P{}-Right'.format(short)))

    # Fix wire end faces (small circular faces ~ pi*r^2)
    # For r=0.4mm, area ~ 0.5 mm^2. Use threshold of 5 mm^2 to be safe.
    for wname in wire_parts:
        inst = a.instances[wname+'-1']
        end_face_indices = []
        for f in inst.faces:
            try:
                area = f.getSize()
                if area < 5.0:  # end faces are very small
                    end_face_indices.append(f.index)
            except:
                pass
        if end_face_indices:
            face_seq = inst.faces[end_face_indices[0]:end_face_indices[0]+1]
            for fi in end_face_indices[1:]:
                face_seq = face_seq + inst.faces[fi:fi+1]
            set_name = 'WireEnd-{}'.format(wname)
            a.Set(faces=face_seq, name=set_name)
            model.EncastreBC(name='Fix-WE-{}'.format(wname.split('-')[-1]),
                             createStepName='Initial',
                             region=a.sets[set_name])
            print('  Fixed {} end faces on {}'.format(len(end_face_indices), wname))

    # ---------- STEP 8: Save and submit ----------
    print('STEP 8: Saving and submitting job...')
    mdb.saveAs(pathName=os.path.join(WORK_DIR, 'WireRope7x1_Solid.cae'))
    job_name = 'WireRope7x1_Solid'
    if job_name in mdb.jobs:
        del mdb.jobs[job_name]
    job = mdb.Job(name=job_name, model='Model-1', type=ANALYSIS,
                  numCpus=4, numDomains=4, multiprocessingMode=THREADS)
    job.submit()
    job.waitForCompletion()
    final_status = str(job.status)
    print('  Status: {}'.format(final_status))

    # ---------- STEP 9: Extract results (only if job completed) ----------
    if final_status == 'COMPLETED':
        odb_path = os.path.join(WORK_DIR, 'WireRope7x1_Solid.odb')
        odb = session.openOdb(odb_path)
        step = odb.steps['ModalAnalysis']
        print('\n{:>4} {:>15}'.format('Mode', 'Freq (Hz)'))
        f = open(os.path.join(WORK_DIR, 'modal_results.txt'), 'w')
        f.write('7x1 Wire Rope Modal Analysis (SOLID)\n')
        f.write('='*40 + '\n')
        f.write('Total nodes: {}\n'.format(total_wire_nodes + total_plate_nodes))
        f.write('Wire seed: {} mm, Plate seed: {} mm\n'.format(
            WIRE_SOLID_SEED, PLATE_SOLID_SEED))
        f.write('='*40 + '\n')
        for i, frame in enumerate(step.frames):
            line = '{:>4} {:>15.4f}'.format(i+1, frame.frequency)
            print(line)
            f.write(line + '\n')
        f.close()
        print('\nDONE. Results in: {}'.format(WORK_DIR))
    else:
        print('\nJob did not complete. Check .dat and .msg files in: {}'.format(WORK_DIR))
        # Show last lines of .msg file for diagnosis
        msg_path = os.path.join(WORK_DIR, job_name + '.msg')
        if os.path.exists(msg_path):
            f = open(msg_path, 'r')
            content = f.read()
            f.close()
            print('\n--- Last part of .msg file ---')
            print(content[-1500:])


if __name__ == '__main__':
    main()