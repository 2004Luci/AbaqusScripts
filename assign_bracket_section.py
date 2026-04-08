# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *
import regionToolset

model = mdb.models['Model-1']

# ---------------------------------------------------
# create bracket solid section
# ---------------------------------------------------

if 'BracketSection' not in model.sections.keys():

    model.HomogeneousSolidSection(
        name='BracketSection',
        material='StainlessSteel',
        thickness=None
    )

    print("Bracket solid section created")

# ---------------------------------------------------
# assign section to both brackets
# ---------------------------------------------------

brackets = ['wr340010_STEEL-1','wr340010_STEEL-2']

for name in brackets:

    part = model.parts[name]

    region = regionToolset.Region(cells=part.cells)

    part.SectionAssignment(
        region=region,
        sectionName='BracketSection'
    )

    print("Section assigned to:", name)

print("Bracket section assignment completed")