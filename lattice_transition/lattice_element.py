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

    min_radius = 0  # min radius that results in a printable structure    (1,  7)
    max_radius = 6  # max radius that results in a viable lattice element (4, 22)

    # Import Models
    latticeModel = VoxelModel.fromVoxFile('lattice_element_3_15x15.vox')
    lattice_size = latticeModel.voxels.shape[0]

    start = time.time()

    # Process Model
    modelResult = VoxelModel.copy(latticeModel)
    modelResult1 = modelResult.dilateBounded(min_radius)
    modelResult2 = modelResult.dilateBounded(max_radius)

    end = time.time()
    m1Time = (end - start)
    print(m1Time)

    # Create Mesh
    mesh1 = Mesh.fromVoxelModel(modelResult1)
    mesh2 = Mesh.fromVoxelModel(modelResult2)

    # Create Plot
    plot1 = Plot(mesh1)
    plot1.show()

    plot2 = Plot(mesh2)
    plot2.show()

    app1.processEvents()
    app1.exec_()