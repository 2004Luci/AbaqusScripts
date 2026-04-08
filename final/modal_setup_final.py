# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

# ---------------------------------------------------
# 1. CREATE ASSEMBLY (instances)
# ---------------------------------------------------

for partName, part in model.parts.items():
    if partName not in assembly.instances.keys():
        assembly.Instance(name=partName, part=part, dependent=ON)

print("Assembly done")


# ---------------------------------------------------
# 2. CREATE MATERIALS (SAFE FIX)
# ---------------------------------------------------

if 'SS_WIRE' not in model.materials.keys():
    mat = model.Material(name='SS_WIRE')
    mat.Density(table=((7.93e-6,),))
    mat.Elastic(table=((200000.0, 0.3),))
    print("SS_WIRE created")

if 'StainlessSteel' not in model.materials.keys():
    mat = model.Material(name='StainlessSteel')
    mat.Density(table=((7.93e-6,),))
    mat.Elastic(table=((200000.0, 0.3),))
    print("StainlessSteel created")


# ---------------------------------------------------
# 3. BEAM SECTION (WIRES)
# ---------------------------------------------------

if 'WireProfile' not in model.profiles.keys():
    model.CircularProfile(name='WireProfile', r=0.1325)

if 'WireSection' not in model.sections.keys():
    model.BeamSection(
        name='WireSection',
        integration=DURING_ANALYSIS,
        poissonRatio=0.3,
        profile='WireProfile',
        material='SS_WIRE',
        temperatureVar=LINEAR
    )

# assign to wires
for partName, part in model.parts.items():
    if 'STEEL-' in partName:
        num = int(partName.split('-')[-1])
        if num >= 3:
            region = regionToolset.Region(edges=part.edges)
            part.SectionAssignment(region=region, sectionName='WireSection')

print("Wire sections assigned")


# ---------------------------------------------------
# 4. SOLID SECTION (BRACKETS)
# ---------------------------------------------------

if 'BracketSection' not in model.sections.keys():
    model.HomogeneousSolidSection(
        name='BracketSection',
        material='StainlessSteel'
    )

brackets = ['wr340010_STEEL-1','wr340010_STEEL-2']

for name in brackets:
    part = model.parts[name]
    region = regionToolset.Region(cells=part.cells)
    part.SectionAssignment(region=region, sectionName='BracketSection')

print("Bracket sections assigned")


# ---------------------------------------------------
# 5. BEAM ORIENTATION
# ---------------------------------------------------

for partName, part in model.parts.items():
    if 'STEEL-' in partName:
        num = int(partName.split('-')[-1])
        if num >= 3:
            region = regionToolset.Region(edges=part.edges)
            part.assignBeamSectionOrientation(
                region=region,
                method=N1_COSINES,
                n1=(0,0,1)
            )

print("Beam orientation done")


# ---------------------------------------------------
# 6. MODAL STEP (IMPORTANT)
# ---------------------------------------------------

if 'ModalStep' not in model.steps.keys():
    model.FrequencyStep(
        name='ModalStep',
        previous='Initial',
        numEigen=200,            #Values
        eigensolver=LANCZOS
    )

model.steps['ModalStep'].setValues(
    minEigen=0.0,                # Min eigen
    maxEigen=4000.0               # Max eigen
)

print("Modal step ready")


# ---------------------------------------------------
# 7. BOUNDARY CONDITIONS
# ---------------------------------------------------

for name in brackets:
    inst = assembly.instances[name]
    region = regionToolset.Region(faces=inst.faces)
    model.EncastreBC(
        name='BC_'+name,
        createStepName='Initial',
        region=region
    )

print("BC applied")


# ---------------------------------------------------
# 8. GENERAL CONTACT (IMPORTANT)
# ---------------------------------------------------

if 'FrictionProp' not in model.interactionProperties.keys():

    prop = model.ContactProperty('FrictionProp')

    prop.TangentialBehavior(table=((0.1,),))
    prop.NormalBehavior(pressureOverclosure=HARD)

if 'GeneralContact' not in model.interactions.keys():

    model.ContactStd(name='GeneralContact', createStepName='Initial')

    model.interactions['GeneralContact'].includedPairs.setValuesInStep(
        stepName='Initial', useAllstar=ON
    )

    model.interactions['GeneralContact'].contactPropertyAssignments.appendInStep(
        stepName='Initial',
        assignments=((GLOBAL, SELF, 'FrictionProp'),)
    )

print("Contact done")


# ---------------------------------------------------
# 9. JOB
# ---------------------------------------------------

mdb.Job(
    name='WR3400_MODAL',
    model='Model-1',
    type=ANALYSIS
)

print("SETUP COMPLETE ✅")
print("Now go to Job module and click SUBMIT")