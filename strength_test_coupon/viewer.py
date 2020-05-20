"""
Copyright 2019
Dan Aukes, Cole Brauer
"""

# Import Libraries
import PyQt5.QtGui as qg
import sys
import numpy as np
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.voxel_model import Dir
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    scaleFactor = 0.2 # Scale the model to increase/decrease resolution
    cleanup = False # Remove duplicate materials and save file
    export = False # STL file for slicing
    exportSim = True # VXC file for simulation
    display = True # Display output

    # Open File
    file = 'stl_files_v4.2_combined/output_A'
    model = VoxelModel.openVF(file)

    # Apply scale factor
    model = model.scale(scaleFactor)

    # Cleanup operations
    if cleanup:
        model.materials = np.round(model.materials, 3)
        model = model.removeDuplicateMaterials()
        model.saveVF(file)

    # Create stl files
    if export:
        for m in range(1, len(model.materials)):
            mesh = Mesh.fromVoxelModel(model.isolateMaterial(m).fitWorkspace())
            mesh.export(file + '-' + str(m) + '.stl')

    # Create VXC file
    if exportSim:
        model.saveVXC(file + '_sim', compression=False)

    if display:
        mesh = Mesh.fromVoxelModel(model)

        # Create Plot
        plot1 = Plot(mesh)
        plot1.show()
        app1.processEvents()
        app1.exec_()