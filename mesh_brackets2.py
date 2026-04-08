from abaqus import *
from abaqusConstants import *
import mesh

# Access model
model = mdb.models['Model-1']

# Access part
part = model.parts['wr340010_STEEL-1']

# Get all cells
cells = part.cells

# Seed part
part.seedPart(size=2.0, deviationFactor=0.1, minSizeFactor=0.1)

# Mesh controls
part.setMeshControls(regions=cells, elemShape=TET, technique=FREE)

# Element type
elemType1 = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD)

part.setElementType(regions=(cells,), elemTypes=(elemType1,))

# Generate mesh
part.generateMesh()