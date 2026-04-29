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
WORK_DIR  = r'C:\Users\admin\Desktop\solid-results'   # output folder

MAX_FREQ_HZ = 5000.0
MAX_MODES = 100

WIRE_SOLID_SEED = 1.0      # mm - wire solid element size (thin geometry)
PLATE_SOLID_SEED = 3.0     # mm - plate solid element size

USE_EMBEDDED_REGION = True
EMBED_TOLERANCE = 1.0      # mm - search tolerance for embedded region

E_MODULUS = 200000.0       # MPa
POISSON = 0.3
DENSITY = 7.85e-9          # tonne/mm^3
# =============================================================================


def main():
    # Create output folder (Python 2/3 compatible)
    if not os.path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)
    os.chdir(WORK_DIR)

    # Get the model (parts already imported manually)
    model = mdb.models['Model-1']
    print('Found model with {} parts'.format(len(model.parts)))

    # ---------- STEP 1: Classify parts ----------
    solid_plate_parts, wire_parts = [], []
    for name in model.parts.keys():
        if len(model.parts[name].faces) > 10:
            solid_plate_parts.append(name)
        else:
            wire_parts.append(name)
    print('STEP 1: {} plates, {} wires (all as solids)'.format(
        len(solid_plate_parts), len(wire_parts)))

    # ---------- STEP 2: Material and Section ----------
    print('STEP 2: Material and section...')
    mat = model.Material(name='Steel')
    mat.Elastic(table=((E_MODULUS, POISSON),))
    mat.Density(table=((DENSITY,),))
    model.HomogeneousSolidSection(name='SteelSolid', material='Steel', thickness=None)

    # ---------- STEP 3: Assign section to all parts ----------
    print('STEP 3: Assigning solid section to all parts...')
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

    # ---------- STEP 5: Embedded region (wires in plates) ----------
    if USE_EMBEDDED_REGION:
        print('STEP 5: Creating embedded region constraint...')
        plate_cells = []
        for pname in solid_plate_parts:
            plate_cells.append(a.instances[pname+'-1'].cells[:])
        combined_plate = plate_cells[0]
        for i in range(1, len(plate_cells)):
            combined_plate = combined_plate + plate_cells[i]
        a.Set(cells=combined_plate, name='PlateHost')

        wire_cells = []
        for wname in wire_parts:
            wire_cells.append(a.instances[wname+'-1'].cells[:])
        combined_wire = wire_cells[0]
        for i in range(1, len(wire_cells)):
            combined_wire = combined_wire + wire_cells[i]
        a.Set(cells=combined_wire, name='WiresEmbedded')

        model.EmbeddedRegion(
            name='WiresInPlates',
            embeddedRegion=a.sets['WiresEmbedded'],
            hostRegion=a.sets['PlateHost'],
            weightFactorTolerance=1e-06,
            toleranceMethod=ABSOLUTE,
            absoluteTolerance=EMBED_TOLERANCE,
            fractionalTolerance=0.05)

    # ---------- STEP 6: Frequency step ----------
    print('STEP 6: Frequency step...')
    max_eig = (2.0 * math.pi * MAX_FREQ_HZ) ** 2
    model.FrequencyStep(name='ModalAnalysis', previous='Initial',
                        eigensolver=LANCZOS, numEigen=MAX_MODES,
                        maxEigen=max_eig,
                        description='Modal 7x1 solid up to {} Hz'.format(MAX_FREQ_HZ))

    # ---------- STEP 7: Mesh ----------
    print('STEP 7: Meshing...')
    c3d10 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD)
    c3d6 = mesh.ElemType(elemCode=C3D6, elemLibrary=STANDARD)
    c3d4 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)

    # Mesh wires
    total_wire_nodes = 0
    for wname in wire_parts:
        p = model.parts[wname]
        p.setMeshControls(regions=p.cells[:], elemShape=TET, technique=FREE)
        p.seedPart(size=WIRE_SOLID_SEED)
        p.setElementType(regions=(p.cells[:],), elemTypes=(c3d10, c3d6, c3d4))
        p.generateMesh()
        total_wire_nodes += len(p.nodes)
    print('  Wire nodes total: {}'.format(total_wire_nodes))

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

    # ---------- STEP 8: BCs ----------
    print('STEP 8: Boundary conditions...')
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

    # Fix wire end faces (small circular faces at each end of solid wires)
    for wname in wire_parts:
        inst = a.instances[wname+'-1']
        end_face_indices = []
        for f in inst.faces:
            area = f.getSize()
            if area < 10.0:  # small end face
                end_face_indices.append(f.index)
        if end_face_indices:
            face_seq = inst.faces[end_face_indices[0]:end_face_indices[0]+1]
            for fi in end_face_indices[1:]:
                face_seq = face_seq + inst.faces[fi:fi+1]
            set_name = 'WireEnd-{}'.format(wname)
            a.Set(faces=face_seq, name=set_name)
            model.EncastreBC(name='Fix-WE-{}'.format(wname.split('-')[-1]),
                             createStepName='Initial',
                             region=a.sets[set_name])

    # ---------- STEP 9: Save and submit ----------
    print('STEP 9: Saving and submitting job...')
    mdb.saveAs(pathName=os.path.join(WORK_DIR, 'WireRope7x1_Solid.cae'))
    job = mdb.Job(name='WireRope7x1_Solid', model='Model-1', type=ANALYSIS,
                  numCpus=4, numDomains=4, multiprocessingMode=THREADS)
    job.submit()
    job.waitForCompletion()
    print('  Status: {}'.format(str(job.status)))

    # ---------- STEP 10: Extract results ----------
    odb = session.openOdb(os.path.join(WORK_DIR, 'WireRope7x1_Solid.odb'))
    step = odb.steps['ModalAnalysis']
    print('\n{:>4} {:>15}'.format('Mode', 'Freq (Hz)'))
    f = open(os.path.join(WORK_DIR, 'modal_results.txt'), 'w')
    f.write('7x1 Wire Rope Modal Analysis (SOLID)\n')
    f.write('='*40 + '\n')
    for i, frame in enumerate(step.frames):
        line = '{:>4} {:>15.4f}'.format(i+1, frame.frequency)
        print(line)
        f.write(line + '\n')
    f.close()
    print('\nDONE. Results in: {}'.format(WORK_DIR))


if __name__ == '__main__':
    main()