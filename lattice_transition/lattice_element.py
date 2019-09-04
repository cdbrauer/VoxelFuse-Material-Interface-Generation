"""
Copyright 2019
Dan Aukes, Cole Brauer
"""

# Import Libraries
import PyQt5.QtGui as qg
import sys
import time
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    min_radius = 7   # min radius that results in a printable structure
    max_radius = 25  # radius that results in a solid cube

    # Import Models
    latticeModel = VoxelModel.fromVoxFile('lattice_element_1.vox')
    lattice_size = len(latticeModel.model[0, 0, :, 0])

    start = time.time()

    # Process Model - standard dilate command
    modelResult = VoxelModel.copy(latticeModel)
    modelResult = modelResult.dilateBounded(min_radius)

    end = time.time()
    m1Time = (end - start)
    print(m1Time)

    # Create Mesh
    mesh1 = Mesh.fromVoxelModel(modelResult)

    # Create Plot
    plot1 = Plot(mesh1)
    plot1.show()

    app1.processEvents()
    app1.exec_()