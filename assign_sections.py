from abaqus import *
from abaqusConstants import *
import regionToolset

# Replace MODEL_NAME with actual model name
modelName = 'Model-1'
sectionName = 'SolidSection'  # The section you already created

# Get model
mdl = mdb.models[modelName]

# Get dictionary of all parts
allParts = mdl.parts

# Print a list of all part names (optional)
print('All parts in model:')
for pName in allParts.keys():
    print('  '+pName)

# Loop through parts and assign the same section
for pName, partObj in allParts.items():
    # only assign if part has solid cells
    if len(partObj.cells) > 0:
        # region = all solid cells
        region = regionToolset.Region(cells=partObj.cells)

        # Assign section
        partObj.SectionAssignment(
            region=region,
            sectionName=sectionName,
            offset=0.0,
            offsetType=MIDDLE_SURFACE,
            offsetField='',
            thicknessAssignment=FROM_SECTION
        )
        print('Section assigned to part:', pName)
    else:
        print('No solid cells to assign in part:', pName)