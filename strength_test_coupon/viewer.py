"""
Copyright 2019
Dan Aukes, Cole Brauer
"""

# Import Libraries
import PyQt5.QtGui as qg
import sys
import numpy as np
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.primitives import cuboid
from voxelfuse.simulation import Simulation
from voxelfuse.voxel_model import Dir
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    # Settings
    # scaleFactor = 1 # Scale the model to increase/decrease resolution
    trim = True # Remove end bumps
    cleanup = False # Remove duplicate materials and save file
    export = True # STL file for slicing
    display = False # Display output

    # Open File
    location = 'stl_files_v3_combined/output-'
    variations = ['A', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']

    for var in variations:
        file = location + var + '.vf'
        model = VoxelModel.openVF(file)

        # Remove end bumps
        if trim:
            modelCutTool1 = cuboid((model.voxels.shape[0], model.voxels.shape[1], 12), (0, 0, model.voxels.shape[2] - 12), 3)
            modelCutTool2 = cuboid((1, model.voxels.shape[1], model.voxels.shape[2]), (0, 0, 0), 3)
            modelCutTool3 = cuboid((1, model.voxels.shape[1], model.voxels.shape[2]), (model.voxels.shape[0] - 1, 0, 0), 3)
            model = model.difference(modelCutTool1 | modelCutTool2 | modelCutTool3)
            model = model.fitWorkspace()
            model.coords = (0, 0, 0)

        # Apply scale factor
        # model = model.scale(scaleFactor)

        # Apply rubber material
        # modelRubber = model.isolateMaterial(1)
        # modelRubber = modelRubber.setMaterial(5)
        # model = modelRubber | model

        # Cleanup operations
        if cleanup:
            model.materials = np.round(model.materials, 3)
            model = model.removeDuplicateMaterials()
            model.saveVF(file)

        # Create stl files
        if export:
            for m in range(1, len(model.materials)):
                mesh = Mesh.fromVoxelModel(model.isolateMaterial(m).fitWorkspace(), 5)
                mesh.export(file + '-' + str(m) + '.stl')

        # Display viewer window
        if display:
            mesh = Mesh.fromVoxelModel(model)

            # Create Plot
            plot1 = Plot(mesh, grids=True)
            plot1.show()
            app1.processEvents()
            app1.exec_()