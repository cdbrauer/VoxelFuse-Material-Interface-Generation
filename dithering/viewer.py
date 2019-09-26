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

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    export = False # STL file for slicing

    # Open File
    file = 'thin_model'
    model = VoxelModel.openVF(file)
    mesh = Mesh.fromVoxelModel(model)

    # Create Plot
    plot1 = Plot(mesh)
    plot1.show()
    app1.processEvents()

    # Create stl files
    if export:
        mesh.export(file + '.stl')

    app1.exec_()