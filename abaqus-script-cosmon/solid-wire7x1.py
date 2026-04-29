# =============================================================================
# WIRE ROPE 7x1 MODAL ANALYSIS - SOLID METHOD (FULL GEOMETRY)
# =============================================================================
# All 7 wires + 2 plates meshed as solid tetrahedral elements
# Preserves original geometry completely - no beam conversion
# Requires licensed Abaqus (~50,000-100,000 nodes expected)
# Usage: File > Run Script in Abaqus CAE
#        OR: abaqus cae noGUI=this_script.py
# =============================================================================

from abaqus import *
from abaqusConstants import *
from caeModules import *
import mesh
import os
import math

# ========================== USER INPUTS ======================================
STEP_FILE = r'D:\ANSYS\DOP\wr340010_7x1.STEP'   # <-- UPDATE PATH
WORK_DIR  = r'C:\Users\admin\Desktop\solid-results'    # <-- UPDATE PATH

MAX_FREQ_HZ = 5000.0
MAX_MODES = 100

# Mesh sizes - balance accuracy vs solve time
WIRE_SOLID_SEED = 1.0      # mm - wire solid element size (careful: thin wires)
PLATE_SOLID_SEED = 3.0     # mm - plate solid element size

# Contact/interaction between wires and plates (embedded region approach)
USE_EMBEDDED_REGION = True
EMBED_TOLERANCE = 1.0      # mm - search tolerance for embedded beam in plates

E_MODULUS = 200000.0       # MPa
POISSON = 0.3
DENSITY = 7.85e-9          # tonne/mm^3
# =============================================================================


def main():
    # os.makedirs(WORK_DIR, exist_ok=True)
    if not os.path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)
    os.chdir(WORK_DIR)

    # ---------- STEP 1: Import STEP ----------
    # print('STEP 1: Importing STEP file...')
    # step_data = mdb.openStep(STEP_FILE, scaleFromFile=OFF)
    # model = mdb.models['Model-1']

    # imported = 0
    # for i in range(1, 30):
    #     try:
    #         model.PartFromGeometryFile(
    #             name='wr340010_7x1-{}'.format(i),
    #             geometryFile=step_data, combine=False, bodyNum=i,
    #             dimensionality=THREE_D, type=DEFORMABLE_BODY)
    #         imported += 1
    #     except:
    #         break
    # print('  Imported {} parts'.format(imported))

    # ---------- STEP 2: Classify parts ----------
    solid_plate_parts, wire_parts = [], []
    for name in model.parts.keys():
        if len(model.parts[name].faces) > 10:
            solid_plate_parts.append(name)
        else:
            wire_parts.append(name)
    print('STEP 2: {} plates, {} wires (all as solids)'.format(
        len(solid_plate_parts), len(wire_parts)))

    # ---------- STEP 3: Material and Section ----------
    print('STEP 3: Material and section...')
    mat = model.Material(name='Steel')
    mat.Elastic(table=((E_MODULUS, POISSON),))
    mat.Density(table=((DENSITY,),))
    model.HomogeneousSolidSection(name='SteelSolid', material='Steel', thickness=None)

    # ---------- STEP 4: Assign section to all parts ----------
    print('STEP 4: Assigning solid section to all parts...')
    for name in model.parts.keys():
        p = model.parts[name]
        r = p.Set(cells=p.cells[:], name='AllCells')
        p.SectionAssignment(region=r, sectionName='SteelSolid',
                            offset=0.0, offsetType=MIDDLE_SURFACE,
                            offsetField='', thicknessAssignment=FROM_SECTION)

    # ---------- STEP 5: Assembly ----------
    print('STEP 5: Assembly...')
    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    for name in model.parts.keys():
        a.Instance(name=name+'-1', part=model.parts[name], dependent=ON)

    # ---------- STEP 6: Embedded region (wires in plates) ----------
    if USE_EMBEDDED_REGION:
        print('STEP 6: Creating embedded region constraint...')
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

    # ---------- STEP 7: Frequency step ----------
    print('STEP 7: Frequency step...')
    max_eig = (2.0 * math.pi * MAX_FREQ_HZ) ** 2
    model.FrequencyStep(name='ModalAnalysis', previous='Initial',
                        eigensolver=LANCZOS, numEigen=MAX_MODES,
                        maxEigen=max_eig,
                        description='Modal 7x1 solid up to {} Hz'.format(MAX_FREQ_HZ))

    # ---------- STEP 8: Mesh ----------
    print('STEP 8: Meshing...')
    c3d10 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD)
    c3d6 = mesh.ElemType(elemCode=C3D6, elemLibrary=STANDARD)
    c3d4 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)

    # Mesh wires with small seed (thin geometry)
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

    # ---------- STEP 9: BCs ----------
    print('STEP 9: Boundary conditions...')
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

    # Fix wire end faces (the two small circular end faces of each solid wire)
    # Find end faces by small area (approx pi * r^2)
    for wname in wire_parts:
        inst = a.instances[wname+'-1']
        end_faces = []
        for f in inst.faces:
            area = f.getSize()
            if area < 10.0:  # small end face
                end_faces.append(f)
        if end_faces:
            face_seq = inst.faces[end_faces[0].index:end_faces[0].index+1]
            for ef in end_faces[1:]:
                face_seq = face_seq + inst.faces[ef.index:ef.index+1]
            a.Set(faces=face_seq, name='WireEnd-{}'.format(wname))
            model.EncastreBC(name='Fix-WE-{}'.format(wname.split('-')[-1]),
                             createStepName='Initial',
                             region=a.sets['WireEnd-{}'.format(wname)])

    # ---------- STEP 10: Save and submit ----------
    print('STEP 10: Saving and submitting job...')
    mdb.saveAs(pathName=os.path.join(WORK_DIR, 'WireRope7x1_Solid.cae'))
    job = mdb.Job(name='WireRope7x1_Solid', model='Model-1', type=ANALYSIS,
                  numCpus=4, numDomains=4, multiprocessingMode=THREADS)
    job.submit()
    job.waitForCompletion()
    print('  Status: {}'.format(str(job.status)))

    # ---------- STEP 11: Extract results ----------
    odb = session.openOdb(os.path.join(WORK_DIR, 'WireRope7x1_Solid.odb'))
    step = odb.steps['ModalAnalysis']
    print('\n{:>4} {:>15}'.format('Mode', 'Freq (Hz)'))
    with open(os.path.join(WORK_DIR, 'modal_results.txt'), 'w') as f:
        f.write('7x1 Wire Rope Modal Analysis (SOLID)\n')
        f.write('='*40 + '\n')
        for i, frame in enumerate(step.frames):
            line = '{:>4} {:>15.4f}'.format(i+1, frame.frequency)
            print(line)
            f.write(line + '\n')
    print('\nDONE. Results in: {}'.format(WORK_DIR))


if __name__ == '__main__':
    main()