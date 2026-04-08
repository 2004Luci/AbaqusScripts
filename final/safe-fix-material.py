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
#  2. CREATE MATERIALS (SAFE FIX)
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

