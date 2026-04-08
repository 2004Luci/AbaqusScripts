# -*- coding: utf-8 -*-

from abaqus import *
from abaqusConstants import *

model = mdb.models['Model-1']

# ---------------------------------------------------
# 1. CREATE CONTACT PROPERTY (Friction)
# ---------------------------------------------------

if 'FrictionProp' not in model.interactionProperties.keys():

    prop = model.ContactProperty('FrictionProp')

    prop.TangentialBehavior(
        formulation=PENALTY,
        table=((0.1,),)   # friction coefficient
    )

    prop.NormalBehavior(
        pressureOverclosure=HARD
    )

    print("Contact property created")


# ---------------------------------------------------
# 2. ENABLE GENERAL CONTACT
# ---------------------------------------------------

model.ContactStd(
    name='GeneralContact',
    createStepName='Initial'
)

model.interactions['GeneralContact'].includedPairs.setValuesInStep(
    stepName='Initial',
    useAllstar=ON
)

model.interactions['GeneralContact'].contactPropertyAssignments.appendInStep(
    stepName='Initial',
    assignments=((GLOBAL, SELF, 'FrictionProp'),)
)

print("General contact enabled successfully")