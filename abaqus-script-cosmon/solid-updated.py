# =============================================================================
# WIRE ROPE 7x1 MODAL ANALYSIS - SOLID + KINEMATIC COUPLING
# =============================================================================
# - Quadratic tet mesh (C3D10) on all parts
# - Encastre ONLY on bottom bracket (auto-detected: name ending in -1)
# - Kinematic coupling at top bracket hole locations (RP at each hole center,
#   wire nodes + bracket nodes near hole as slaves, U1/U2/U3 constrained)
# - No other constraints on wires or top bracket
# =============================================================================

from abaqus import *
from abaqusConstants import *
from caeModules import *
import regionToolset
import mesh
import os
import math

# ========================== USER INPUTS ======================================
WORK_DIR = r'C:\Users\admin\Desktop\solid-results'

MAX_FREQ_HZ = 5000.0
MAX_MODES = 100

WIRE_SOLID_SEED = 0.4      # mm - quadratic tets on thin wires
PLATE_SOLID_SEED = 3.0     # mm - bracket mesh

# Hole detection / coupling parameters
HOLE_CLUSTER_X_TOL = 4.0    # mm - max X-spread inside one hole crossing
COUPLE_SEARCH_RADIUS = 4.0  # mm - bracket node search radius around hole center

E_MODULUS = 200000.0       # MPa
POISSON   = 0.3
DENSITY   = 7.85e-9        # tonne/mm^3
# =============================================================================


def main():
    if not os.path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)
    os.chdir(WORK_DIR)

    model = mdb.models['Model-1']
    print('Found model with {} parts'.format(len(model.parts)))

    # ---------- STEP 1: Classify parts ----------
    bracket_parts, wire_parts = [], []
    for name in model.parts.keys():
        if len(model.parts[name].faces) > 10:
            bracket_parts.append(name)
        else:
            wire_parts.append(name)

    if len(bracket_parts) != 2:
        raise Exception('Expected 2 bracket parts, found {}'.format(len(bracket_parts)))

    # User convention: name ending in -1 = bottom, -2 = top
    bracket_parts.sort()
    bottom_bracket = bracket_parts[0]
    top_bracket    = bracket_parts[1]
    print('STEP 1: bottom={}, top={}, wires={}'.format(
        bottom_bracket, top_bracket, len(wire_parts)))

    # ---------- STEP 2: Material ----------
    print('STEP 2: Material...')
    mat = model.Material(name='Steel')
    mat.Elastic(table=((E_MODULUS, POISSON),))
    mat.Density(table=((DENSITY,),))
    model.HomogeneousSolidSection(name='SteelSolid', material='Steel', thickness=None)

    # ---------- STEP 3: Section assignment ----------
    print('STEP 3: Assigning sections...')
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
                        description='Modal 7x1 with kinematic coupling')

    # ---------- STEP 6: Mesh (QUADRATIC TETS for all parts) ----------
    print('STEP 6: Meshing (quadratic C3D10 elements)...')
    c3d10 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD)
    c3d15 = mesh.ElemType(elemCode=C3D15, elemLibrary=STANDARD)
    c3d20 = mesh.ElemType(elemCode=C3D20, elemLibrary=STANDARD)

    # Wires: quadratic tets, fine seed for thin geometry
    total_wire_nodes = 0
    for wname in wire_parts:
        p = model.parts[wname]
        p.setMeshControls(regions=p.cells[:], elemShape=TET, technique=FREE)
        p.seedPart(size=WIRE_SOLID_SEED, deviationFactor=0.1, minSizeFactor=0.1)
        p.setElementType(regions=(p.cells[:],), elemTypes=(c3d10,))
        p.generateMesh()
        total_wire_nodes += len(p.nodes)
    print('  Wire nodes: {}'.format(total_wire_nodes))

    # Brackets: quadratic tets
    total_bracket_nodes = 0
    for bname in bracket_parts:
        p = model.parts[bname]
        p.setMeshControls(regions=p.cells[:], elemShape=TET, technique=FREE)
        p.seedPart(size=PLATE_SOLID_SEED)
        p.setElementType(regions=(p.cells[:],), elemTypes=(c3d10,))
        p.generateMesh()
        total_bracket_nodes += len(p.nodes)
    print('  Bracket nodes: {}'.format(total_bracket_nodes))
    print('  TOTAL NODES: {}'.format(total_wire_nodes + total_bracket_nodes))

    # ---------- STEP 7: Boundary Conditions ----------
    print('STEP 7: BC -- Encastre on bottom bracket ONLY...')
    bottom_inst = a.instances[bottom_bracket + '-1']
    top_inst    = a.instances[top_bracket    + '-1']

    # Encastre on entire bottom bracket (all cells -> all nodes fixed)
    bottom_set = a.Set(cells=bottom_inst.cells[:], name='BottomBracket-All')
    model.EncastreBC(name='Fix-BottomBracket',
                     createStepName='Initial',
                     region=bottom_set)
    print('  Encastre applied to: {}'.format(bottom_bracket))
    print('  No BCs on top bracket or wires (will be coupled)')

    # ---------- STEP 8: Kinematic Coupling at top bracket hole regions -----
    print('STEP 8: Building kinematic couplings at top bracket holes...')

    # Get top bracket bounding box
    top_p = model.parts[top_bracket]
    bb = top_p.queryGeometry(printResults=False)['boundingBox']
    tb_xmin, tb_ymin, tb_zmin = bb[0]
    tb_xmax, tb_ymax, tb_zmax = bb[1]
    print('  Top bracket bbox: X[{:.2f},{:.2f}] Y[{:.2f},{:.2f}] Z[{:.2f},{:.2f}]'.format(
        tb_xmin, tb_xmax, tb_ymin, tb_ymax, tb_zmin, tb_zmax))

    coupling_count = 0
    skipped = 0

    for wname in wire_parts:
        wire_inst = a.instances[wname + '-1']

        # Collect wire nodes inside top bracket bbox
        wire_nodes_in = []
        for n in wire_inst.nodes:
            x, y, z = n.coordinates
            if (tb_xmin <= x <= tb_xmax and
                tb_ymin <= y <= tb_ymax and
                tb_zmin <= z <= tb_zmax):
                wire_nodes_in.append(n)

        if not wire_nodes_in:
            continue

        # Cluster by X coordinate -> each cluster = one hole crossing
        wire_nodes_in.sort(key=lambda n: n.coordinates[0])
        clusters = []
        current = [wire_nodes_in[0]]
        for n in wire_nodes_in[1:]:
            if n.coordinates[0] - current[-1].coordinates[0] < HOLE_CLUSTER_X_TOL:
                current.append(n)
            else:
                clusters.append(current)
                current = [n]
        clusters.append(current)

        # Process each cluster (one hole crossing)
        for ci, cluster in enumerate(clusters):
            cx = sum(n.coordinates[0] for n in cluster) / len(cluster)
            cy = sum(n.coordinates[1] for n in cluster) / len(cluster)
            cz = sum(n.coordinates[2] for n in cluster) / len(cluster)

            # Find nearby top bracket nodes (hole inner surface candidates)
            bracket_near = []
            r2 = COUPLE_SEARCH_RADIUS * COUPLE_SEARCH_RADIUS
            for bn in top_inst.nodes:
                bx, by, bz = bn.coordinates
                if (bx-cx)*(bx-cx) + (by-cy)*(by-cy) + (bz-cz)*(bz-cz) < r2:
                    bracket_near.append(bn)

            if len(bracket_near) == 0:
                skipped += 1
                continue

            # Reference point at hole center
            rp_feat = a.ReferencePoint(point=(cx, cy, cz))
            rp_obj  = a.referencePoints[rp_feat.id]
            rp_region = regionToolset.Region(referencePoints=(rp_obj,))

            # Slave node set = wire nodes (cluster) + bracket nodes (near)
            wire_labels    = [n.label for n in cluster]
            bracket_labels = [n.label for n in bracket_near]

            wire_node_arr    = wire_inst.nodes.sequenceFromLabels(wire_labels)
            bracket_node_arr = top_inst.nodes.sequenceFromLabels(bracket_labels)
            combined         = wire_node_arr + bracket_node_arr

            slave_name = 'Slaves-{}-h{}'.format(wname, ci)
            a.Set(nodes=combined, name=slave_name)

            # Apply kinematic coupling
            coupling_name = 'KCouple-{}-h{}'.format(wname, ci)
            model.Coupling(
                name=coupling_name,
                controlPoint=rp_region,
                surface=a.sets[slave_name],
                influenceRadius=WHOLE_SURFACE,
                couplingType=KINEMATIC,
                localCsys=None,
                u1=ON, u2=ON, u3=ON,
                ur1=OFF, ur2=OFF, ur3=OFF
            )
            coupling_count += 1

    print('  Created {} kinematic couplings ({} clusters skipped - no bracket nodes)'.format(
        coupling_count, skipped))

    # ---------- STEP 9: Save and submit ----------
    print('STEP 9: Saving and submitting job...')
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

    # ---------- STEP 10: Extract results ----------
    if final_status == 'COMPLETED':
        odb_path = os.path.join(WORK_DIR, 'WireRope7x1_Solid.odb')
        odb = session.openOdb(odb_path)
        step = odb.steps['ModalAnalysis']
        print('\n{:>4} {:>15}'.format('Mode', 'Freq (Hz)'))
        f = open(os.path.join(WORK_DIR, 'modal_results.txt'), 'w')
        f.write('7x1 Wire Rope Modal Analysis (SOLID + Kinematic Couplings)\n')
        f.write('='*60 + '\n')
        f.write('Bottom bracket (encastre): {}\n'.format(bottom_bracket))
        f.write('Top bracket (kinematic couplings): {}\n'.format(top_bracket))
        f.write('Total kinematic couplings: {}\n'.format(coupling_count))
        f.write('Wire seed: {} mm, Plate seed: {} mm\n'.format(
            WIRE_SOLID_SEED, PLATE_SOLID_SEED))
        f.write('Element type: C3D10 (quadratic tet)\n')
        f.write('Total nodes: {}\n'.format(total_wire_nodes + total_bracket_nodes))
        f.write('='*60 + '\n')
        for i, frame in enumerate(step.frames):
            line = '{:>4} {:>15.4f}'.format(i+1, frame.frequency)
            print(line)
            f.write(line + '\n')
        f.close()
        print('\nDONE. Results in: {}'.format(WORK_DIR))
    else:
        print('\nJob did not complete. Check .dat and .msg files in: {}'.format(WORK_DIR))
        msg_path = os.path.join(WORK_DIR, job_name + '.msg')
        if os.path.exists(msg_path):
            f = open(msg_path, 'r')
            content = f.read()
            f.close()
            print('\n--- Last 2000 chars of .msg file ---')
            print(content[-2000:])


if __name__ == '__main__':
    main()