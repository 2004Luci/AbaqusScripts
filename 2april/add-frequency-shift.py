# # -*- coding: utf-8 -*-

# from abaqus import *
# from abaqusConstants import *

# model = mdb.models['Model-1']

# model.steps['ModalStep'].setValues(
#     eigensolver=LANCZOS,
#     shift=1.0   # 🔥 KEY FIX
# )

# print("✅ Frequency shift added")



# # -*- coding: utf-8 -*-

# from abaqus import *
# from abaqusConstants import *

# model = mdb.models['Model-1']

# # Get first step automatically
# stepName = list(model.steps.keys())[0]

# model.steps[stepName].setValues(
#     eigensolver=LANCZOS,
#     shift=1.0
# )

# print("✅ Frequency shift applied to step:", stepName)



# -*- coding: utf-8 -*-

# from abaqus import *

# model = mdb.models['Model-1']

# # get step name automatically
# stepName = list(model.steps.keys())[0]

# # apply frequency shift ONLY
# model.steps[stepName].setValues(
#     shift=1.0
# )

# print("✅ Frequency shift applied to:", stepName)




# # -*- coding: utf-8 -*-

# from abaqus import *
# from abaqusConstants import *

# model = mdb.models['Model-1']

# print("\nFixing modal step...\n")

# # ----------------------------
# # 1. DELETE EXISTING STEP
# # ----------------------------
# for stepName in list(model.steps.keys()):
#     del model.steps[stepName]
#     print("Deleted step:", stepName)

# # ----------------------------
# # 2. CREATE NEW MODAL STEP
# # ----------------------------
# model.FrequencyStep(
#     name='ModalStep',
#     previous='Initial',
#     numEigen=5,
#     eigensolver=LANCZOS
# )

# print("Created new Frequency Step")

# print("\n✅ Modal step fixed\n")











# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *

model = mdb.models['Model-1']

print("\nFixing modal step...\n")

# ----------------------------
# 1. DELETE EXISTING STEPS (EXCEPT INITIAL)
# ----------------------------
for stepName in list(model.steps.keys()):
    
    if stepName != 'Initial':   # ✅ skip Initial
        del model.steps[stepName]
        print("Deleted step:", stepName)

# ----------------------------
# 2. CREATE NEW MODAL STEP
# ----------------------------
model.FrequencyStep(
    name='ModalStep',
    previous='Initial',
    numEigen=5,
    eigensolver=LANCZOS
)

print("Created new Frequency Step")

print("\n✅ Modal step fixed\n")