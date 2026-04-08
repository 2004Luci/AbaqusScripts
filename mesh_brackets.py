# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import mesh

modelName = 'Model-1'
model = mdb.models[modelName]

# bracket names
brackets = [
    'wr340010_STEEL-1',
    'wr340010_STEEL-2'
]

# mesh size (mm)
meshSize = 3.0

for partName in brackets:

    if partName not in model.parts:
        print('Part not found:', partName)
        continue

    p = model.parts[partName]

    print('Meshing bracket:', partName)

    # seed the part
    p.seedPart(
        size=meshSize,
        deviationFactor=0.1,
        minSizeFactor=0.1
    )

    # assign solid element type
    elemType = mesh.ElemType(
        elemCode=C3D8R,
        elemLibrary=STANDARD
    )

    region = (p.cells,)
    p.setElementType(
        regions=region,
        elemTypes=(elemType,)
    )

    # generate mesh
    p.generateMesh()

    print('Mesh created for', partName)

print('Bracket meshing completed.')