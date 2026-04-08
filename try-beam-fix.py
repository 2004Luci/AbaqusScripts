# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *

model = mdb.models['Model-1']

for partName, part in model.parts.items():

    if 'STEEL-' in partName:

        num = int(partName.split('-')[-1])

        if num >= 3:  # wires

            edges = part.edges

            # combine all edges virtually
            part.createVirtualTopology(
                regions=edges
            )

            print("Virtual topology applied to:", partName)

print("All wires simplified for meshing.")