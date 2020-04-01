"""
Copyright 2020
Dan Aukes, Cole Brauer
"""

# Import Libraries
import PyQt5.QtGui as qg
import sys
import numpy as np
from tqdm import tqdm

from voxelfuse.voxel_model import VoxelModel
from voxelfuse.primitives import *
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    cleanup = False # Remove duplicate materials

    # Open File
    couponsIDs = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']
    #folder = 'stl_files_v3_combined/output-'
    folder = 'stl_files_v4.2_combined/output_'

    rigidMaterial = 2
    flexibleMaterial = 1
    rigidPercentages = np.zeros(len(couponsIDs))
    flexiblePercentages = np.zeros(len(couponsIDs))

    for pattern in range(len(couponsIDs)):
        model = VoxelModel.openVF(folder + couponsIDs[pattern])
        model.resolution = 5 # Manually set resolution if not set in file
        res = model.resolution

        # Cleanup operations
        if cleanup:
            model.materials = np.round(model.materials, 3)
            model = model.removeDuplicateMaterials()

        _, totalVolume = model.getVolume()
        _, rigidVolume = model.getVolume(material=rigidMaterial)
        _, flexibleVolume = model.getVolume(material=flexibleMaterial)

        rigidPercentages[pattern] = rigidVolume/totalVolume
        flexiblePercentages[pattern] = flexibleVolume/totalVolume

    print('\nRigid: ' + str(rigidPercentages))
    print('Flexible: ' + str(flexiblePercentages))
    print('Other Material: ' + str(np.ones(len(couponsIDs))-(flexiblePercentages+rigidPercentages)))