from abaqus import *
from abaqusConstants import *
import mesh

# --------------------------------
# MODEL & MESHING PARAMETERS
# --------------------------------
modelName = 'Model-1'
mdbModel = mdb.models[modelName]

# Define mesh sizes (modify if needed)
wireMeshSize = 0.8   # mm for wire strands
bracketMeshSize = 4.0  # mm for bracket (coarse)

# --------------------------------
# MESH ALL PARTS
# --------------------------------
for partName, partObj in mdbModel.parts.items():
    # Only mesh parts with solid geometry
    if len(partObj.cells) > 0:

        print('Meshing part:', partName)

        # ----------------------
        # 1) Seed the part
        # ----------------------
        # Default seed (will be overwritten for specific mesh sizes)
        partObj.seedPart(size=bracketMeshSize,
                         deviationFactor=0.1,
                         minSizeFactor=0.1)

        # ----------------------
        # 2) Custom seeding
        # ----------------------
        # If this part is wire (name includes 'wire'):
        if 'wire' in partName.lower():
            partObj.seedPart(size=wireMeshSize,
                             deviationFactor=0.1,
                             minSizeFactor=0.1)
            print('  Wire mesh seeds applied:', wireMeshSize, 'mm')
        else:
            print('  Bracket mesh seeds applied:', bracketMeshSize, 'mm')

        # ----------------------
        # 3) Assign element type
        # ----------------------
        # Choose first element type
        elemType = mesh.ElemType(elemCode=C3D8R,
                                  elemLibrary=STANDARD)

        regionCells = (partObj.cells,)
        partObj.setElementType(regions=regionCells,
                                elemTypes=(elemType,))

        # ----------------------
        # 4) Generate mesh
        # ----------------------
        partObj.generateMesh()
        print('  Mesh generated for:', partName)

    else:
        print('Skipping part (no solids):', partName)

# --------------------------------
# OPTIONAL: Check mesh statistics
# --------------------------------
print('\nMesh Statistics:')
for partName, partObj in mdbModel.parts.items():
    if len(partObj.cells) > 0:
        stats = partObj.getMeshStats(regions=(partObj.cells,))
        print(' ', partName, 'Nodes:', stats.nodes, 'Elements:', stats.elements)

print('\nMesh generation script completed.')