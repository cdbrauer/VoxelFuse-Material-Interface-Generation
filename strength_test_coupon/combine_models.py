"""
Copyright 2019
Dan Aukes, Cole Brauer
"""

# Import Libraries
import PyQt5.QtGui as qg
import sys
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.primitives import *

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    res = 5 # voxels per mm
    couponStandard = 'D638' # Start of stl file name

    display = False # Display output
    cleanup = True # Remove duplicate materials and save file
    export = True # STL file for slicing

    # Open Files
    outputFile = 'output-combined'
    files = ['output-control', 'output-blur', 'output-dither', 'output-gyroid', 'output-schwarzp', 'output-plus', 'output-cross', 'output-zz4']

    model = VoxelModel.emptyLike(cube(1))
    for i in range(len(files)):
        new_model = VoxelModel.openVF('stl_files_v3_combined/' + files[i])
        new_model = new_model.setCoords((0, i*110, 0))
        model = model | new_model

    # Cleanup operations
    if cleanup:
        model.materials = np.round(model.materials, 1)
        model = model.removeDuplicateMaterials()
        model.saveVF(outputFile)

    # Create stl files
    if export:
        for m in range(1, len(model.materials)):
            mesh = Mesh.fromVoxelModel(model.isolateMaterial(m), resolution=res)
            mesh.export(('stl_files_v3_combined/' + couponStandard + '_mat_' + str(m) + '_' + str(model.materials[m, 2]) + '.stl'))

    if display:
        mesh = Mesh.fromVoxelModel(model)

        # Create Plot
        plot1 = Plot(mesh)
        plot1.show()
        app1.processEvents()
        app1.exec_()