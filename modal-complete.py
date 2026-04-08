# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly


# ---------------------------------------------------
# 1. CREATE ASSEMBLY INSTANCES
# ---------------------------------------------------

for partName, part in model.parts.items():

    if partName not in assembly.instances.keys():

        assembly.Instance(
            name=partName,
            part=part,
            dependent=ON
        )

print('Assembly created')


# ---------------------------------------------------
# 2. CREATE WIRE PROFILE
# ---------------------------------------------------

wireDiameter = 0.265
wireRadius = wireDiameter/2.0

model.CircularProfile(
    name='WireProfile',
    r=wireRadius
)

print('Beam profile created')


# ---------------------------------------------------
# 3. CREATE BEAM SECTION
# ---------------------------------------------------

model.BeamSection(
    name='WireSection',
    integration=DURING_ANALYSIS,
    poissonRatio=0.3,
    profile='WireProfile',
    material='StainlessSteel',
    temperatureVar=LINEAR
)

print('Beam section created')


# ---------------------------------------------------
# 4. ASSIGN SECTION TO WIRES
# ---------------------------------------------------

for partName, part in model.parts.items():

    if 'STEEL-' in partName:

        num = int(partName.split('-')[-1])

        if num >= 3:

            region = regionToolset.Region(edges=part.edges)

            part.SectionAssignment(
                region=region,
                sectionName='WireSection'
            )

print('Section assigned to wires')


# ---------------------------------------------------
# 5. CREATE MODAL STEP
# ---------------------------------------------------

model.FrequencyStep(
    name='ModalStep',
    previous='Initial',
    numEigen=20,
    eigensolver=LANCZOS
)

model.steps['ModalStep'].setValues(
    minEigen=4000.0,
    maxEigen=5000.0
)

print('Modal step created')


# ---------------------------------------------------
# 6. APPLY BOUNDARY CONDITIONS
# ---------------------------------------------------

brackets = ['wr340010_STEEL-1','wr340010_STEEL-2']

for bracket in brackets:

    inst = assembly.instances[bracket]

    region = regionToolset.Region(faces=inst.faces)

    model.EncastreBC(
        name='BC_'+bracket,
        createStepName='Initial',
        region=region
    )

print('Boundary conditions applied')


# ---------------------------------------------------
# 7. CREATE JOB
# ---------------------------------------------------

mdb.Job(
    name='WR3400_MODAL',
    model='Model-1',
    description='WR3400 modal analysis'
)

print('Job created')
print('Submit using: mdb.jobs["WR3400_MODAL"].submit()')