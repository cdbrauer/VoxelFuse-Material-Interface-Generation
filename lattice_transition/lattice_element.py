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

    # Import Models
    latticeModel = VoxelModel.fromVoxFile('lattice_element_1.vox')
    lattice_size = len(latticeModel.model[0, 0, :, 0])

    # Process Models
    modelResult = latticeModel.dilate(5)

    # Create Mesh
    mesh1 = Mesh.fromVoxelModel(modelResult)

    # Create Plot
    plot1 = Plot(mesh1)
    plot1.show()

    app1.processEvents()
    app1.exec_()