# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *
import mesh

# =============================
# MODEL
# =============================
modelName = 'Model-1'
mdbModel = mdb.models[modelName]

# =============================
# MESH PARAMETERS (OPTIMIZED)
# =============================

#  KEY CHANGE (VERY IMPORTANT)
wireBeamSeed = 2.12    # mm  

# Bracket mesh (coarser)
bracketMeshSize = 6.0  # mm 

# =============================
# FUNCTION TO GET PART NUMBER
# =============================
def getPartNumber(name):
    try:
        return int(name.split('-')[-1])
    except:
        return None

# =============================
# DELETE OLD MESH FIRST
# =============================
print("\nDeleting old mesh...\n")

for partName, partObj in mdbModel.parts.items():
    try:
        partObj.deleteMesh()
        print("Deleted mesh:", partName)
    except:
        pass

# =============================
# MESHING START
# =============================
print("\nStarting NEW meshing...\n")

for partName, partObj in mdbModel.parts.items():
    
    print("Meshing part:", partName)
    
    num = getPartNumber(partName)
    
    if num is None:
        print("  Skipped (unknown naming)")
        continue

    # =============================
    # BRACKET (SOLID MESH)
    # =============================
    if num == 1 or num == 2:

        partObj.seedPart(
            size=bracketMeshSize,
            deviationFactor=0.1,
            minSizeFactor=0.1
        )

        # Solid elements (efficient)
        elemSolid = mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD)

        partObj.setElementType(
            regions=(partObj.cells,),
            elemTypes=(elemSolid,)
        )

        partObj.generateMesh()

        print("  ✅ Bracket mesh done (size =", bracketMeshSize, "mm)")

    # =============================
    # WIRES (BEAM MESH)
    # =============================
    else:

        partObj.seedPart(
            size=wireBeamSeed,
            deviationFactor=0.1,
            minSizeFactor=0.1
        )

        # Beam elements
        elemBeam = mesh.ElemType(elemCode=B31, elemLibrary=STANDARD)

        partObj.setElementType(
            regions=(partObj.edges,),
            elemTypes=(elemBeam,)
        )

        partObj.generateMesh()

        print("  ✅ Wire mesh done (seed =", wireBeamSeed, "mm)")

# =============================
# DONE
# =============================
print("\n✅ MESHING COMPLETE\n")

print("👉 Now check element count:")
print("Mesh → Tools → Query → Elements → All")