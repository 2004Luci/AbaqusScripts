from abaqus import *
from abaqusConstants import *
import regionToolset
import mesh

# ------------------------------
# 1. MODEL & PART LISTING
# ------------------------------
modelName = 'Model-1'
mdb.Model(name=modelName)
mdl = mdb.models[modelName]

print('Parts in the model:')
for p in mdl.parts.keys():
    print('   ' + p)

# ------------------------------
# 2. MATERIAL DEFINITIONS
# ------------------------------

# Stainless steel (wire)
mat_wire = mdl.Material(name='SS_Wire')
mat_wire.Density(table=((8.0e-006, ),))        # kg/mm^3
mat_wire.Elastic(table=((193000.0, 0.30),))    # N/mm2, Poisson

# Mild steel (bracket)
mat_bracket = mdl.Material(name='Mild_Steel')
mat_bracket.Density(table=((7.85e-006, ),))
mat_bracket.Elastic(table=((210000.0, 0.30),))

# ------------------------------
# 3. CREATE SOLID SECTIONS
# ------------------------------

sec_wire = mdl.HomogeneousSolidSection(name='Wire_Section',
                                       material='SS_Wire',
                                       thickness=None)
sec_bracket = mdl.HomogeneousSolidSection(name='Bracket_Section',
                                           material='Mild_Steel',
                                           thickness=None)

# ------------------------------
# 4. SECTION ASSIGNMENT
# ------------------------------
for partName, partObj in mdl.parts.items():
    if len(partObj.cells) > 0:
        # assign wire section to parts with Wire in name
        if 'wire' in partName.lower():
            region = regionToolset.Region(cells=partObj.cells)
            partObj.SectionAssignment(region=region,
                                      sectionName='Wire_Section')
            print('Wire section assigned to', partName)
        else:
            # everything else gets bracket section
            region = regionToolset.Region(cells=partObj.cells)
            partObj.SectionAssignment(region=region,
                                      sectionName='Bracket_Section')
            print('Bracket section assigned to', partName)
    else:
        print('No solid cells found in', partName)

# ------------------------------
# 5. MESHING
# ------------------------------

# Mesh seeding sizes
wire_mesh_size = 0.8
bracket_mesh_size = 4.0

for partName, partObj in mdl.parts.items():
    # Set mesh controls
    partObj.seedPart(size=bracket_mesh_size, deviationFactor=0.1,
                     minSizeFactor=0.1)

    # Finer mesh if wire
    if 'wire' in partName.lower():
        partObj.seedPart(size=wire_mesh_size, deviationFactor=0.1,
                         minSizeFactor=0.1)

    # Element type
    elemType1 = mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD)
    partObj.setElementType(regions=(partObj.cells,),
                            elemTypes=(elemType1,))

    partObj.generateMesh()
    print('Meshed part:', partName)

# ------------------------------
# 6. ASSEMBLY
# ------------------------------
assemblyInst = mdl.rootAssembly
for partName, partObj in mdl.parts.items():
    assemblyInst.Instance(name=partName + '-inst',
                          part=partObj, dependent=ON)

# ------------------------------
# 7. MODAL STEP
# ------------------------------

mdl.FrequencyStep(name='Modal_Step', previous='Initial',
                  numEigen=15)

# ------------------------------
# 8. BOUNDARY CONDITIONS
# ------------------------------

# Fix bracket base (example faces - user should check by visualization)
# User may need to adjust selection ids manually
all_ins = assemblyInst.instances

for instName, instObj in all_ins.items():
    if 'bracket' in instName.lower():
        # pick all bottom faces at z=0 plane if that is base
        faces = instObj.faces.findAt(((0.0, 0.0, 0.0),))
        region = regionToolset.Region(faces=faces)
        mdl.DisplacementBC(name='BC_Base_Fix', createStepName='Initial',
                            region=region, u1=SET, u2=SET, u3=SET,
                            ur1=SET, ur2=SET, ur3=SET)
        print('Base fixed BC applied to', instName)

# ------------------------------
# 9. CREATE & SUBMIT JOB
# ------------------------------

jobName = 'WR3400_Modal'
job = mdb.Job(name=jobName, model=modelName,
              numCpus=4, numDomains=4)

job.submit()
job.waitForCompletion()

print('Job submitted and completed:', jobName)