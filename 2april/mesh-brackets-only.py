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
# PARAMETERS
# =============================
bracketMeshSize = 8.0  # mm 

# =============================
# BRACKET PART NAMES
# =============================
brackets = ['wr340010_STEEL-1', 'wr340010_STEEL-2']

print("\nMeshing ONLY brackets...\n")

# =============================
# LOOP OVER BRACKETS
# =============================
for name in brackets:

    try:
        partObj = mdbModel.parts[name]
        print("Processing:", name)

        # ----------------------
        # Delete existing mesh
        # ----------------------
        try:
            partObj.deleteMesh()
            print("  Old mesh deleted")
        except:
            print("  No existing mesh")

        # ----------------------
        # Seeding
        # ----------------------
        partObj.seedPart(
            size=bracketMeshSize,
            deviationFactor=0.1,
            minSizeFactor=0.1
        )

        # ----------------------
        # Element type (solid)
        # ----------------------
        elemSolid = mesh.ElemType(
            elemCode=C3D8R,
            elemLibrary=STANDARD
        )

        partObj.setElementType(
            regions=(partObj.cells,),
            elemTypes=(elemSolid,)
        )

        # ----------------------
        # Generate mesh
        # ----------------------
        partObj.generateMesh()

        print("  ✅ Mesh generated (size =", bracketMeshSize, "mm)\n")

    except:
        print("  ❌ Failed for:", name, "\n")

print("✅ Bracket-only meshing COMPLETE\n")