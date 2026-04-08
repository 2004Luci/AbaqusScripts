# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

brackets = ['wr340010_STEEL-1', 'wr340010_STEEL-2']

print("\nApplying boundary conditions...\n")

for name in brackets:
    
    inst = assembly.instances[name]
    
    # select ALL faces (safe approach)
    region = regionToolset.Region(faces=inst.faces)

    model.EncastreBC(
        name='BC_' + name,
        createStepName='Initial',
        region=region
    )

    print("Fixed:", name)

print("\n✅ Boundary conditions applied\n")