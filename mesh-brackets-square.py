from abaqus import *
from abaqusConstants import *
import mesh

model = mdb.models['Model-1']
part = model.parts['wr340010_STEEL-2']

cells = part.cells

# Global seed
part.seedPart(size=2.0, deviationFactor=0.1, minSizeFactor=0.1)

# Use tetrahedral mesh (most robust)
part.setMeshControls(regions=cells, elemShape=TET, technique=FREE)

# Element types
elemType1 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD)
elemType2 = mesh.ElemType(elemCode=C3D4, elemLibrary=STANDARD)

part.setElementType(regions=(cells,), elemTypes=(elemType1, elemType2))

# Generate mesh
part.generateMesh()