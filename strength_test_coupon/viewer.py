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

    display = True # Display output
    export = False # STL file for slicing
    cleanup = False # Remove duplicate materials and save file

    # Open File
    file = 'stl_files_v3_combined/output-zz5'
    model = VoxelModel.openVF(file)

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

    if display:
        mesh = Mesh.fromVoxelModel(model)

        # Create Plot
        plot1 = Plot(mesh)
        plot1.show()
        app1.processEvents()
        app1.exec_()