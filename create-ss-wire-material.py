from abaqus import *
from abaqusConstants import *

model = mdb.models['Model-1']

# create stainless steel material
if 'SS_WIRE' not in model.materials.keys():

    mat = model.Material(name='SS_WIRE')

    # density in kg/mm^3
    mat.Density(table=((7.93e-6,),))

    # elastic properties (MPa = N/mm^2)
    mat.Elastic(table=((200000.0, 0.3),))

    print("Material SS_WIRE created with kg/mm^3 units")

else:
    print("Material SS_WIRE already exists")