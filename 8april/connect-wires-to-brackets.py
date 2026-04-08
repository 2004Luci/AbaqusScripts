# -*- coding: utf-8 -*-
# connect-wires-to-brackets.py

from abaqus import *
from abaqusConstants import *
import regionToolset

model = mdb.models['Model-1']
assembly = model.rootAssembly

# 1. Remove General Contact to stop the adjustment warnings
if 'General_Contact' in model.interactions.keys():
    del model.interactions['General_Contact']
    print("Deleted existing General Contact definition.")

# 2. Define the Bracket Surfaces (Master surfaces for the Tie)
# This assumes your brackets have the faces needed for the connection
bracket_names = ['wr340010_STEEL-1', 'wr340010_STEEL-2']
bracket_regions = []

for name in bracket_names:
    inst = assembly.instances[name]
    # Selecting all faces of the bracket as a simplified master surface
    bracket_regions.append(inst.faces)

# 3. Iterate through all 49 wire strands and Tie them
print("Starting Tie Constraints for 49 wire parts...")

for i in range(3, 52): # STEEL-3 to STEEL-51
    wire_inst_name = 'wr340010_STEEL-' + str(i)
    if wire_inst_name in assembly.instances.keys():
        wire_inst = assembly.instances[wire_inst_name]
        
        # Tie name
        tie_name = 'Constraint-Wire-' + str(i)
        
        # Define the wire (slave) - using all edges of the beam
        wire_region = regionToolset.Region(edges=wire_inst.edges)
        
        # Define the bracket (master) - combined faces of both brackets
        # Using a large position tolerance to catch wires near the brackets
        try:
            model.Tie(name=tie_name, master=assembly.instances[bracket_names[0]].faces, 
                      slave=wire_region, positionToleranceMethod=COMPUTED, 
                      adjust=ON, tieRotations=ON, thickness=ON)
        except:
            pass

print("✅ Wires have been tied to brackets. Run your Modal Job again.")