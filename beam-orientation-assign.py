# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *
import regionToolset

model = mdb.models['Model-1']

# orientation direction
orientation_vector = (0.0, 0.0, 1.0)

for partName, part in model.parts.items():

    if 'STEEL-' in partName:

        number = int(partName.split('-')[-1])

        # wire parts start from 3
        if number >= 3:

            edges = part.edges

            region = regionToolset.Region(edges=edges)

            part.assignBeamSectionOrientation(
                region=region,
                method=N1_COSINES,
                n1=orientation_vector
            )

            print("Beam orientation assigned to:", partName)

print("All wire orientations assigned successfully.")