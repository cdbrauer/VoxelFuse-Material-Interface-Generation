import PyQt5.QtGui as qg
import sys

from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.voxel_model import VoxelModel

from dithering.thin import thin

if __name__ == '__main__':
    app1 = qg.QApplication(sys.argv)

    box_x = 25
    box_y = 10
    box_z = 10

    # Create base model
    result1 = VoxelModel.fromVoxFile('centerline-test.vox')
    print('Model Created')

    # Process Model
    result1 = thin(result1, 50)

    # Create mesh
    mesh1 = Mesh.fromVoxelModel(result1)

    # Create plot
    plot1 = Plot(mesh1)
    plot1.show()

    app1.processEvents()
    app1.exec_()