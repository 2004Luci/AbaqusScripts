# =============================================================================
# WIRE ROPE 7x1 MODAL ANALYSIS - SOLID MESH + KINEMATIC COUPLING AT WIRE ENDS
# =============================================================================
# Run this AFTER manually importing wr340010_7x1.STEP into Model-1
#
# Strategy:
#   - All parts meshed with quadratic tets (C3D10)
#   - Bottom bracket (-1): Encastre on entire cell
#   - Top bracket (-2):    NO direct BC
#   - For EACH wire end face (small-area circular face):
#         * Determine nearest bracket (top or bottom) by distance
#         * Find bracket mesh nodes within COUPLE_SEARCH_RADIUS of face centroid
#         * Create RP at face centroid
#         * Kinematic coupling: RP master, slaves = wire-face nodes + nearby bracket nodes
#   - Result: wires rigidly tied to brackets at hole crossings; bottom-bracket
#     encastre transitively fixes wire ends near bottom; top-bracket motion is
#     transmitted to wire ends near top.
# =============================================================================

from abaqus import *
from abaqusConstants import *
import regionToolset, mesh, os, math

WORK_DIR              = r'C:\Users\admin\Desktop\solid-results-29april'
JOB_NAME              = "wr_7x1_solid_kc"
NUM_MODES             = 50
FREQ_MAX_HZ           = 5000.0
WIRE_SEED             = 0.40       # mm  (must be < wire diameter ~0.795)
BRACKET_SEED          = 5.0        # mm
END_FACE_AREA_MAX     = 5.0        # mm^2  (wire end face ~ 0.5 mm^2)
COUPLE_SEARCH_RADIUS  = 6.0        # mm  -- generous so we always catch bracket nodes around the hole
NUM_CPUS              = 4
E_STEEL               = 200000.0   # N/mm^2
NU_STEEL              = 0.30
RHO_STEEL             = 7.85e-9    # tonne/mm^3   (consistent units: N, mm, tonne, s, MPa)


def classify_parts(model):
    brackets, wires = [], []
    for n in model.parts.keys():
        p = model.parts[n]
        if len(p.faces) > 10:
            brackets.append(n)
        else:
            wires.append(n)
    brackets.sort()        # '-1' before '-2'
    wires.sort()
    return brackets, wires


def print_geometry(model):
    print("--- Part geometry ---")
    for n in sorted(model.parts.keys()):
        p = model.parts[n]
        bb = p.queryGeometry(printResults=False)
        b = bb['boundingBox']; c = bb['centroid']
        print("  %s: X[%.2f,%.2f] Y[%.2f,%.2f] Z[%.2f,%.2f]  centroid=(%.2f,%.2f,%.2f)  faces=%d cells=%d"
              % (n, b[0][0], b[1][0], b[0][1], b[1][1], b[0][2], b[1][2],
                 c[0], c[1], c[2], len(p.faces), len(p.cells)))


def main():
    if not os.path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)
    os.chdir(WORK_DIR)

    model = mdb.models['Model-1']
    print_geometry(model)

    brackets, wires = classify_parts(model)
    if len(brackets) < 2:
        raise Exception("Expected 2 brackets, found %d" % len(brackets))
    bottom_bracket = brackets[0]   # -1
    top_bracket    = brackets[1]   # -2
    print("Bottom bracket: %s   Top bracket: %s" % (bottom_bracket, top_bracket))
    print("Wires (%d): %s" % (len(wires), wires))

    # -------- Material & section --------
    if 'Steel' not in model.materials.keys():
        m = model.Material(name='Steel')
        m.Density(table=((RHO_STEEL,),))
        m.Elastic(table=((E_STEEL, NU_STEEL),))
    if 'SteelSec' not in model.sections.keys():
        model.HomogeneousSolidSection(name='SteelSec', material='Steel', thickness=None)

    for n in model.parts.keys():
        p = model.parts[n]
        cells = p.cells[:]
        if len(cells) > 0:
            region = regionToolset.Region(cells=cells)
            p.SectionAssignment(region=region, sectionName='SteelSec',
                                offset=0.0, offsetType=MIDDLE_SURFACE,
                                offsetField='', thicknessAssignment=FROM_SECTION)

    # -------- Assembly --------
    a = model.rootAssembly
    a.DatumCsysByDefault(CARTESIAN)
    for n in model.parts.keys():
        inst_name = n + '-1'
        if inst_name not in a.instances.keys():
            a.Instance(name=inst_name, part=model.parts[n], dependent=ON)

    bot_inst = a.instances[bottom_bracket + '-1']
    top_inst = a.instances[top_bracket + '-1']

    # -------- Mesh: quadratic tets (C3D10) for all parts --------
    elem_c3d10 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD)
    for n in model.parts.keys():
        p = model.parts[n]
        seed = WIRE_SEED if n in wires else BRACKET_SEED
        p.seedPart(size=seed, deviationFactor=0.1, minSizeFactor=0.1)
        cells = p.cells[:]
        p.setMeshControls(regions=cells, elemShape=TET, technique=FREE)
        p.setElementType(regions=(cells,), elemTypes=(elem_c3d10,))
        p.generateMesh()
        print("  Meshed %-25s  nodes=%d  elements=%d  (seed=%.2f)"
              % (n, len(p.nodes), len(p.elements), seed))
    a.regenerate()

    # -------- Step --------
    if 'Freq' in model.steps.keys():
        del model.steps['Freq']
    model.FrequencyStep(name='Freq', previous='Initial',
                        numEigen=NUM_MODES, maxEigen=FREQ_MAX_HZ)

    # -------- BC: Encastre bottom bracket only --------
    bot_cells_set = a.Set(cells=bot_inst.cells[:], name='BottomBracket-Cells')
    # remove any previous BCs
    for bcn in list(model.boundaryConditions.keys()):
        del model.boundaryConditions[bcn]
    model.EncastreBC(name='Fix-BottomBracket',
                     createStepName='Initial',
                     region=bot_cells_set)

    # -------- Kinematic couplings at wire end faces --------
    # remove any previous couplings
    for cn in list(model.constraints.keys()):
        del model.constraints[cn]

    bot_centroid = model.parts[bottom_bracket].queryGeometry(printResults=False)['centroid']
    top_centroid = model.parts[top_bracket   ].queryGeometry(printResults=False)['centroid']
    print("Bracket centroids: BOT=%s  TOP=%s" % (bot_centroid, top_centroid))

    n_top = 0
    n_bot = 0
    n_skip = 0
    r2 = COUPLE_SEARCH_RADIUS ** 2

    for wname in wires:
        winst = a.instances[wname + '-1']

        # find small-area (end) faces
        end_face_indices = []
        for fi in range(len(winst.faces)):
            try:
                if winst.faces[fi].getSize() < END_FACE_AREA_MAX:
                    end_face_indices.append(fi)
            except:
                pass
        print("  %s: %d end faces" % (wname, len(end_face_indices)))

        for ef_idx, fi in enumerate(end_face_indices):
            face = winst.faces[fi]
            cx, cy, cz = face.pointOn[0]

            d_top = (cx-top_centroid[0])**2 + (cy-top_centroid[1])**2 + (cz-top_centroid[2])**2
            d_bot = (cx-bot_centroid[0])**2 + (cy-bot_centroid[1])**2 + (cz-bot_centroid[2])**2
            if d_top < d_bot:
                target_inst, label = top_inst, 'TOP'
            else:
                target_inst, label = bot_inst, 'BOT'

            # bracket nodes within search radius
            near_labels = []
            for bn in target_inst.nodes:
                bx, by, bz = bn.coordinates
                if (bx-cx)**2 + (by-cy)**2 + (bz-cz)**2 < r2:
                    near_labels.append(bn.label)

            if not near_labels:
                # adaptive: expand radius once
                r2_big = (COUPLE_SEARCH_RADIUS * 2.0) ** 2
                for bn in target_inst.nodes:
                    bx, by, bz = bn.coordinates
                    if (bx-cx)**2 + (by-cy)**2 + (bz-cz)**2 < r2_big:
                        near_labels.append(bn.label)
                if not near_labels:
                    print("    SKIP %s end %d at (%.2f,%.2f,%.2f) -> no %s nodes in 2*radius"
                          % (wname, ef_idx, cx, cy, cz, label))
                    n_skip += 1
                    continue
                else:
                    print("    %s end %d: used expanded radius for %s (%d nodes)"
                          % (wname, ef_idx, label, len(near_labels)))

            # wire end face Set -> get its mesh node labels
            wire_face_set_name = 'WEnd-%s-%d' % (wname, ef_idx)
            wire_face_set = a.Set(faces=winst.faces[fi:fi+1], name=wire_face_set_name)
            wire_face_node_labels = [n.label for n in wire_face_set.nodes]
            if not wire_face_node_labels:
                print("    SKIP %s end %d -> no nodes on face" % (wname, ef_idx))
                n_skip += 1
                continue

            # combined slave node set
            combined = (winst.nodes.sequenceFromLabels(wire_face_node_labels) +
                        target_inst.nodes.sequenceFromLabels(near_labels))
            slaves_name = 'Slaves-%s-%d-%s' % (wname, ef_idx, label)
            a.Set(nodes=combined, name=slaves_name)

            # reference point
            rp_feat = a.ReferencePoint(point=(cx, cy, cz))
            rp_obj  = a.referencePoints[rp_feat.id]
            rp_region = regionToolset.Region(referencePoints=(rp_obj,))

            cname = 'KC-%s-%d-%s' % (wname, ef_idx, label)
            model.Coupling(name=cname,
                           controlPoint=rp_region,
                           surface=a.sets[slaves_name],
                           influenceRadius=WHOLE_SURFACE,
                           couplingType=KINEMATIC,
                           localCsys=None,
                           u1=ON, u2=ON, u3=ON,
                           ur1=ON, ur2=ON, ur3=ON)

            if label == 'TOP': n_top += 1
            else:              n_bot += 1
            print("    %s end %d -> %s  (wire face nodes=%d, bracket nodes=%d)"
                  % (wname, ef_idx, label, len(wire_face_node_labels), len(near_labels)))

    print("\nCoupling summary: TOP=%d  BOT=%d  skipped=%d" % (n_top, n_bot, n_skip))
    if n_top + n_bot == 0:
        raise Exception("No couplings created -- check geometry / search radius")

    a.regenerate()

    # -------- Save CAE --------
    cae_path = os.path.join(WORK_DIR, 'wr_7x1_solid_kc.cae')
    mdb.saveAs(pathName=cae_path)
    print("Saved CAE: %s" % cae_path)

    # -------- Job --------
    if JOB_NAME in mdb.jobs.keys():
        del mdb.jobs[JOB_NAME]
    j = mdb.Job(name=JOB_NAME, model='Model-1',
                description='7x1 wire rope solid modal w/ kinematic coupling',
                type=ANALYSIS, numCpus=NUM_CPUS, numDomains=NUM_CPUS,
                multiprocessingMode=DEFAULT)
    j._Job__userSubDir = WORK_DIR
    os.chdir(WORK_DIR)
    j.writeInput(consistencyChecking=OFF)
    print("INP written: %s.inp" % JOB_NAME)
    j.submit(consistencyChecking=OFF)
    j.waitForCompletion()
    print("Job status: %s" % j.status)

    # -------- Extract frequencies --------
    odb_path = os.path.join(WORK_DIR, JOB_NAME + '.odb')
    if j.status != COMPLETED:
        print("Job did not complete; check %s.msg / .dat" % JOB_NAME)
        return

    from odbAccess import openOdb
    odb = openOdb(path=odb_path, readOnly=True)
    step = odb.steps['Freq']
    print("\n--- Modal frequencies (Hz) ---")
    for fr in step.frames:
        desc = fr.description
        # description like: "Mode  1: Value =  1.234E+05  Freq =   55.78    (cycles/time)"
        if 'Freq' in desc:
            print("  " + desc)
    odb.close()


main()