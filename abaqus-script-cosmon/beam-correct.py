# =============================================================================
# WIRE ROPE 7x1 MODAL ANALYSIS - BEAM METHOD
# (No STEP import - assumes parts already imported manually as wr340010_7x1-N)
# =============================================================================

from abaqus import *
from abaqusConstants import *
from caeModules import *
import mesh
import os
import math
import json

# ========================== USER INPUTS ======================================
WORK_DIR  = r'C:\Users\admin\Desktop\beam-results'   # output folder

MAX_FREQ_HZ = 5000.0
MAX_MODES = 100

WIRE_BEAM_SEED = 10.0      # mm
PLATE_SOLID_SEED = 3.0     # mm

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
    solid_parts, wire_parts = [], []
    for name in model.parts.keys():
        if len(model.parts[name].faces) > 10:
            solid_parts.append(name)
        else:
            wire_parts.append(name)
    print('STEP 1: {} solid plates, {} wires'.format(len(solid_parts), len(wire_parts)))

    # ---------- STEP 2: Auto-detect wire radius & extract centerlines ----------
    print('STEP 2: Extracting wire centerlines...')
    N_PTS = 60
    p0 = model.parts[wire_parts[0]]
    edge_sizes = []
    for i in range(len(p0.edges)):
        edge_sizes.append((i, p0.edges[i].getSize()))
    edge_sizes.sort(key=lambda x: x[1])
    short_len = edge_sizes[0][1]
    wire_radius = (2.0 * short_len) / (2.0 * math.pi)
    print('  Auto-detected wire radius: {:.4f} mm (diameter: {:.4f} mm)'.format(
        wire_radius, 2.0 * wire_radius))

    wire_data = {}
    for wname in wire_parts:
        p = model.parts[wname]
        max_len, idx = 0, 0
        for i in range(len(p.edges)):
            if p.edges[i].getSize() > max_len:
                max_len, idx = p.edges[i].getSize(), i
        coords = []
        for i in range(N_PTS + 1):
            dp = p.DatumPointByEdgeParam(edge=p.edges[idx], parameter=i/float(N_PTS))
            pt = p.datums[dp.id]
            coords.append([pt.pointOn[0], pt.pointOn[1], pt.pointOn[2]])
        wire_data[wname] = coords

    with open(os.path.join(WORK_DIR, 'wire_centerlines.json'), 'w') as f:
        json.dump(wire_data, f)

    # ---------- STEP 3: Create beam parts, delete solid wires ----------
    print('STEP 3: Creating {} beam wire parts...'.format(len(wire_data)))
    for old_name, coords in wire_data.items():
        num = old_name.split('-')[-1]
        new_name = 'Wire-{}'.format(num)
        p = model.Part(name=new_name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
        p.WireSpline(points=[tuple(c) for c in coords],
                     mergeType=MERGE, meshable=ON)
    for old in list(wire_data.keys()):
        del model.parts[old]

    # ---------- STEP 4: Material + Sections ----------
    print('STEP 4: Material and sections...')
    mat = model.Material(name='Steel')
    mat.Elastic(table=((E_MODULUS, POISSON),))
    mat.Density(table=((DENSITY,),))
    model.CircularProfile(name='WireProfile', r=wire_radius)
    model.BeamSection(name='WireBeamSection', integration=DURING_ANALYSIS,
                      profile='WireProfile', material='Steel',
                      consistentMassMatrix=False)
    model.HomogeneousSolidSection(name='PlateSection', material='Steel', thickness=None)

    for name in model.parts.keys():
        p = model.parts[name]
        if name.startswith('Wire-'):
            r = p.Set(edges=p.edges[:], name='AllEdges')
            p.SectionAssignment(region=r, sectionName='WireBeamSection',
                                offset=0.0, offsetType=MIDDLE_SURFACE,
                                offsetField='', thicknessAssignment=FROM_SECTION)
            p.assignBeamSectionOrientation(region=r, method=N1_COSINES,
                                           n1=(0.0, 1.0, 0.0))
        else:
            r = p.Set(cells=p.cells[:], name='AllCells')
            p.SectionAssignment(region=r, sectionName='PlateSection',
                                offset=0.0, offsetType=MIDDLE_SURFACE,
                                offsetField='', thicknessAssignment=FROM_SECTION)

    # ---------- STEP 5: Assembly ----------
    print('STEP 5: Assembly...')
    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    for name in model.parts.keys():
        a.Instance(name=name+'-1', part=model.parts[name], dependent=ON)

    # ---------- STEP 6: Frequency step ----------
    print('STEP 6: Frequency step...')
    max_eig = (2.0 * math.pi * MAX_FREQ_HZ) ** 2
    model.FrequencyStep(name='ModalAnalysis', previous='Initial',
                        eigensolver=LANCZOS, numEigen=MAX_MODES,
                        maxEigen=max_eig,
                        description='Modal 7x1 up to {} Hz'.format(MAX_FREQ_HZ))

    # ---------- STEP 7: Mesh ----------
    print('STEP 7: Meshing...')
    beam_elem = mesh.ElemType(elemCode=B31, elemLibrary=STANDARD)
    for name in model.parts.keys():
        if name.startswith('Wire-'):
            p = model.parts[name]
            p.seedPart(size=WIRE_BEAM_SEED)
            p.setElementType(regions=(p.edges[:],), elemTypes=(beam_elem,))
            p.generateMesh()
    c3d10 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD)
    c3d6 = mesh.ElemType(elemCode=C3D6, elemLibrary=STANDARD)
    c3d4 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)
    for name in solid_parts:
        p = model.parts[name]
        p.setMeshControls(regions=p.cells[:], elemShape=TET, technique=FREE)
        p.seedPart(size=PLATE_SOLID_SEED)
        p.setElementType(regions=(p.cells[:],), elemTypes=(c3d10, c3d6, c3d4))
        p.generateMesh()

    # ---------- STEP 8: BCs ----------
    print('STEP 8: Boundary conditions...')
    for plate_name in solid_parts:
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

    wverts = []
    for iname in a.instances.keys():
        if iname.startswith('Wire-'):
            wverts.append(a.instances[iname].vertices[:])
    combined = wverts[0]
    for i in range(1, len(wverts)):
        combined = combined + wverts[i]
    a.Set(vertices=combined, name='AllWireEndpoints')
    model.EncastreBC(name='Fix-WireEnds', createStepName='Initial',
                     region=a.sets['AllWireEndpoints'])

    # ---------- STEP 9: Save and submit ----------
    print('STEP 9: Submitting job...')
    mdb.saveAs(pathName=os.path.join(WORK_DIR, 'WireRope7x1_Beam.cae'))
    job = mdb.Job(name='WireRope7x1_Beam', model='Model-1', type=ANALYSIS)
    job.submit()
    job.waitForCompletion()
    print('  Status: {}'.format(str(job.status)))

    # ---------- STEP 10: Extract results ----------
    odb = session.openOdb(os.path.join(WORK_DIR, 'WireRope7x1_Beam.odb'))
    step = odb.steps['ModalAnalysis']
    print('\n{:>4} {:>15}'.format('Mode', 'Freq (Hz)'))
    f = open(os.path.join(WORK_DIR, 'modal_results.txt'), 'w')
    f.write('7x1 Wire Rope Modal Analysis (BEAM)\n')
    f.write('='*40 + '\n')
    for i, frame in enumerate(step.frames):
        line = '{:>4} {:>15.4f}'.format(i+1, frame.frequency)
        print(line)
        f.write(line + '\n')
    f.close()
    print('\nDONE. Results in: {}'.format(WORK_DIR))


if __name__ == '__main__':
    main()