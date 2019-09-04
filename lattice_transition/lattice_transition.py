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

    lattice_element_file = 'lattice_element_1m'

    mold = True
    moldWallThickness = 5
    moldGap = 2

    export = True

    # Dilate radius that results in a cube
    min_radius = 1  # min radius that results in a printable structure (1,  7)
    max_radius = 7  # radius that results in a solid cube              (7, 25)

    # Import Models
    latticeModel = VoxelModel.fromVoxFile(lattice_element_file + '.vox')
    lattice_size = len(latticeModel.model[0, 0, :, 0])
    print('Lattice Element Imported')

    # Generate baseModel
    box = np.ones((lattice_size*2, lattice_size*2, lattice_size*20, len(materials)+1))
    box1 = VoxelModel(box, 0, 0, 0).setMaterial(1)
    box2 = VoxelModel(box, lattice_size*10, 0, 0).setMaterial(3)
    baseModel = box1.union(box2)
    print('Model Created')

    # Process Models
    modelResult = baseModel.blur(lattice_size*6)
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

    print('Lattice Generation:')
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
                dilate_radius = int(density * (max_radius-min_radius))

                if dilate_radius > 0:
                    latticeModelDilated = latticeModel.dilateBounded(dilate_radius + min_radius)
                else:
                    latticeModelDilated = VoxelModel.emptyLike(latticeModel)

                latticeResult = latticeResult.union(latticeModelDilated)

    print('Lattice Created')

    modelResult = modelResult.intersection(latticeResult)
    modelResult = modelResult.setMaterial(1)
    modelResultComplete = modelResult.union(baseModel.setMaterial(3))
    modelResultCast = baseModel.setMaterial(3).difference(modelResult)
    print('Lattice Processed')

    modelResultMold = VoxelModel.copy(modelResult)

    if mold: # Generate mold feature
        fixtureModel = modelResultComplete.web('laser', moldGap, moldWallThickness)
        fixtureModel = fixtureModel.setMaterial(2)
        modelResultMold = modelResultMold.union(fixtureModel)

    print('Fixture Generated')

    # Create Mesh
    mesh1 = Mesh.fromVoxelModel(modelResultMold)
    print('Mesh Created')

    # Create Plot
    plot1 = Plot(mesh1)
    plot1.show()
    app1.processEvents()

    if export:
        mesh1.export('test_coupon_' + lattice_element_file + '.stl')

    app1.exec_()