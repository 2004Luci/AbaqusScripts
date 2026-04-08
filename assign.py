from abaqus import *
from abaqusConstants import *
import regionToolset

# ===== PARAMETERS =====
modelName = 'Model-1'
sectionName = 'AllParts_SolidSection'
materialName = 'SS_Wire'  # Change if using a different material

# Get model
mdl = mdb.models[modelName]

# -------- Print all parts --------
print('Parts in this model:')
for name in mdl.parts.keys():
    print('  -', name)

# -------- Create a Homogeneous Solid Section --------
# If the section already exists, Abaqus will raise an error.
# To avoid errors, typically you would check before creation.
try:
    mdl.HomogeneousSolidSection(name=sectionName,
                                material=materialName,
                                thickness=None)
    print('Created section:', sectionName)
except:
    print('Section already exists:', sectionName)

# -------- Assign the Section to Each Part --------

for partName, partObj in mdl.parts.items():
    # Only assign if part has solid cells
    if len(partObj.cells) > 0:
        region = regionToolset.Region(cells=partObj.cells)
        partObj.SectionAssignment(region=region,
                                  sectionName=sectionName,
                                  offset=0.0,
                                  offsetType=MIDDLE_SURFACE,
                                  offsetField='',
                                  thicknessAssignment=FROM_SECTION)
        print('Section assigned to part:', partName)
    else:
        print('Skipped (no solids):', partName)