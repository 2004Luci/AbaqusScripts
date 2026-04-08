# -*- coding: utf-8 -*-

from abaqus import *

model = mdb.models['Model-1']

for partName, partObj in model.parts.items():
    
    try:
        partObj.deleteMesh()
        print("Mesh deleted for:", partName)
        
    except:
        print("No mesh found or failed for:", partName)

print("\nAll mesh deleted successfully.")