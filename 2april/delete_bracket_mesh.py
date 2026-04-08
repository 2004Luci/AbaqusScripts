# -*- coding: utf-8 -*-

from abaqus import *

model = mdb.models['Model-1']

# bracket part names
brackets = ['wr340010_STEEL-1', 'wr340010_STEEL-2']

for name in brackets:
    
    try:
        partObj = model.parts[name]
        partObj.deleteMesh()
        print("Mesh deleted for:", name)
        
    except:
        print("Failed or no mesh found for:", name)

print("\n✅ Bracket mesh deletion complete.")