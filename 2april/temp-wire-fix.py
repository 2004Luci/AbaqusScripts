# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

print("\nApplying BC to WIRES...\n")

for name, inst in assembly.instances.items():
    
    if 'STEEL-' in name:
        num = int(name.split('-')[-1])
        
        if num >= 3:  # wires
            
            region = regionToolset.Region(edges=inst.edges)
            
            model.EncastreBC(
                name='BC_wire_' + name,
                createStepName='Initial',
                region=region
            )
            
            print("Fixed wire:", name)

print("\n✅ All wires constrained\n")