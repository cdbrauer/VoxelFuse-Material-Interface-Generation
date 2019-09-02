"""
Copyright 2019
Dan Aukes, Cole Brauer
"""

# Import Libraries
import PyQt5.QtGui as qg
import sys
import numpy as np
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.materials import materials

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    # Import Models
    #baseModel = VoxelModel.fromVoxFile('material_interface_1.vox')
    latticeModel = VoxelModel.fromVoxFile('lattice_element_1m.vox')
    lattice_size = len(latticeModel.model[0, 0, :, 0])
    print('Lattice Element Imported')

    # Generate baseModel instead of importing
    box = np.ones((lattice_size*2, lattice_size*2, lattice_size*10, len(materials)+1))
    box1 = VoxelModel(box, 0, 0, 0).setMaterial(1)
    box2 = VoxelModel(box, lattice_size*10, 0, 0).setMaterial(3)
    baseModel = box1.union(box2)
    print('Model Created')

    # Process Models
    modelResult = baseModel.blur(100)
    modelResult = modelResult - modelResult.setMaterial(3)
    modelResult = modelResult.scaleNull()
    print('Model Processed')

    x_len = len(modelResult.model[0, 0, :, 0])
    y_len = len(modelResult.model[:, 0, 0, 0])
    z_len = len(modelResult.model[0, :, 0, 0])

    x_repeat = range(0, x_len, lattice_size)
    y_repeat = range(0, y_len, lattice_size)
    z_repeat = range(0, z_len, lattice_size)

    latticeResult = VoxelModel.emptyLike(modelResult)

    for x in x_repeat:
        print(str(x) + '/' + str(x_repeat[-1]))

        for y in y_repeat:
            for z in z_repeat:
                latticeModel.x = x
                latticeModel.y = y
                latticeModel.z = z

                x_center = int(x + (lattice_size/2))
                y_center = int(y + (lattice_size/2))
                z_center = int(z + (lattice_size/2))

                density = modelResult.model[y_center, z_center, x_center, 0] * (1 - modelResult.model[y_center, z_center, x_center, 1])
                dilate_radius = int(density * 7)

                if dilate_radius > 0:
                    latticeModelDilated = latticeModel.dilate(dilate_radius)
                else:
                    latticeModelDilated = VoxelModel.emptyLike(latticeModel)

                latticeResult = latticeResult.union(latticeModelDilated)

    print('Lattice Created')

    modelResult = modelResult.intersection(latticeResult)
    modelResult = modelResult.setMaterial(1)
    modelResult2 = modelResult.union(baseModel.setMaterial(3))
    modelResult3 = baseModel.setMaterial(3).difference(modelResult)
    print('Lattice Processed')

    # Create Mesh
    mesh1 = Mesh.fromVoxelModel(modelResult)
    mesh2 = Mesh.fromVoxelModel(modelResult2)
    mesh3 = Mesh.fromVoxelModel(modelResult3)
    print('Mesh Created')

    # Create Plot
    plot1 = Plot(mesh1)
    plot1.show()
    plot2 = Plot(mesh2)
    plot2.show()
    plot3 = Plot(mesh3)
    plot3.show()

    app1.processEvents()
    app1.exec_()