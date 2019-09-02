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

    max_radius = 25

    # Import Models
    latticeModel = VoxelModel.fromVoxFile('lattice_element_1.vox')
    lattice_size = len(latticeModel.model[0, 0, :, 0])

    # Process Model - standard dilate command
    start = time.time()
    modelResult = VoxelModel.copy(latticeModel)
    for r in range(max_radius):
        print(str(r) + '/' + str(max_radius))
        modelResult = modelResult.dilate()
    end = time.time()
    m1Time = (end - start)
    print(m1Time)

    # Process Model - large dilate command
    start = time.time()
    modelResult2 = latticeModel.dilateLarge(max_radius)
    end = time.time()
    m2Time = (end - start)
    print(m2Time)

    # Create Mesh
    mesh1 = Mesh.fromVoxelModel(modelResult2)

    # Create Plot
    plot1 = Plot(mesh1)
    plot1.show()

    app1.processEvents()
    app1.exec_()