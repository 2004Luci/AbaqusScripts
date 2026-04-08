# -*- coding: utf-8 -*-
from abaqus import *
from abaqusConstants import *
import mesh

# =============================
# MODEL & MESHING PARAMETERS
# =============================
modelName = 'Model-1'
mdbModel = mdb.models[modelName]

# Beam seed spacing for wires (≤2×dia)
wireBeamSeed = 0.53  # mm (2 × 0.265 mm)

# Solid mesh size for bracket
bracketMeshSize = 4.0  # mm

# =============================
# FUNCTION TO GET PART NUMBER
# =============================
def getPartNumber(name):
    """
    Extract integer at end of part name like 'wr340010_STEEL-5'.
    """
    try:
        return int(name.split('-')[-1])
    except:
        return None

# =============================
# MESH EACH PART
# =============================
for partName, partObj in mdbModel.parts.items():
    print('Meshing part:', partName)
    
    # Extract number from name
    num = getPartNumber(partName)
    
    if num is None:
        # Skip parts that don't follow naming convention
        print('  Skipping unknown pattern part:', partName)
        continue

    # If part number 1 or 2 → bracket
    if num == 1 or num == 2:
        # ----------------------
        # SOLID MESH FOR BRACKET
        # ----------------------
        partObj.seedPart(size=bracketMeshSize, deviationFactor=0.1, minSizeFactor=0.1)
        
        # Assign a solid element type
        elemSolid = mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD)
        partObj.setElementType(regions=(partObj.cells,), elemTypes=(elemSolid,))
        
        partObj.generateMesh()
        print('  Solid mesh generated for bracket:', bracketMeshSize, 'mm')

    else:
        # ----------------------
        # BEAM MESH FOR WIRE
        # ----------------------
        partObj.seedPart(size=wireBeamSeed, deviationFactor=0.1, minSizeFactor=0.1)

        # Beam element type
        elemTypeBeam = mesh.ElemType(elemCode=B31, elemLibrary=STANDARD)
        regionEdges = (partObj.edges,)
        
        partObj.setElementType(regions=regionEdges, elemTypes=(elemTypeBeam,))
        partObj.generateMesh()
        
        print('  Beam mesh generated for wire part with seed ≤', wireBeamSeed, 'mm')

print('\nMeshing script completed successfully.')