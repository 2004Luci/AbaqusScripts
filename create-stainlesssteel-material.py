from abaqus import *
from abaqusConstants import *

model = mdb.models['Model-1']

if 'StainlessSteel' not in model.materials.keys():

    mat = model.Material(name='StainlessSteel')

    # density (kg/mm^3)
    mat.Density(table=((7.93e-6,),))

    # elastic properties (MPa = N/mm^2)
    mat.Elastic(table=((200000.0, 0.30),))

    print("Material StainlessSteel created")

else:
    print("Material StainlessSteel already exists")