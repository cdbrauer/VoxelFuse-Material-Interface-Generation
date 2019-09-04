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

    min_radius = 1  # min radius that results in a printable structure (1,  7)
    max_radius = 6  # radius that results in a solid cube              (6, 25)

    box_x = 15
    box_y = 4
    box_z = 4

    # Import Models
    latticeModel = VoxelModel.fromVoxFile(lattice_element_file + '.vox')
    lattice_size = len(latticeModel.model[0, 0, :, 0])
    print('Lattice Element Imported')

    # Generate Base Model
    box = np.ones((box_y, box_z, box_x, len(materials)+1))
    box1 = VoxelModel(box, 0, 0, 0).setMaterial(1)
    box2 = VoxelModel(box, box_x, 0, 0).setMaterial(3)
    baseModel = box1.union(box2)
    print('Model Created')

    # Process Models
    modelResult = baseModel.blur(int(round(box_x/6)))
    modelResult = modelResult - modelResult.setMaterial(3)
    modelResult = modelResult.scaleNull()
    print('Model Processed')

    # Generate Dilated Lattice Elements
    latticeElements = [VoxelModel.emptyLike(latticeModel)]
    for r in range(min_radius, max_radius+1):
        latticeElements.append(latticeModel.dilateBounded(r))
    print('Lattice Elements Generated')

    # Convert processed model to lattice
    latticeResult = VoxelModel(np.zeros((1, 1, 1, len(materials)+1)))

    iter_count = box_x * box_y * box_z
    iter_current = 0

    print('Lattice Structure Generation:')
    for x in range(box_x * 2):
        print(str(x) + '/' + str(box_x * 2))
        for y in range(box_y):
            for z in range(box_z):
                density =  modelResult.model[y, z, x, 0] * (1 - modelResult.model[y, z, x, 1])
                if density > 0:
                    r = int(round(density * (max_radius - min_radius))) + min_radius
                else:
                    r = 0

                latticeElements[r].x = x * lattice_size
                latticeElements[r].y = y * lattice_size
                latticeElements[r].z = z * lattice_size

                latticeResult = latticeResult.union(latticeElements[r])

    latticeResult = latticeResult.setMaterial(1)
    print('Lattice Structure Created')

    # Generate Resin Component
    large_box = np.ones((box_y * lattice_size, box_z * lattice_size, box_x * lattice_size * 2, len(materials) + 1))
    resinModel = VoxelModel(large_box, 0, 0, 0).setMaterial(3)
    resinModel = resinModel.difference(latticeResult)
    print('Resin Model Created')

    latticeResultMold = VoxelModel.copy(latticeResult)
    if mold: # Generate mold feature
        fixtureModel = latticeResult.union(resinModel).web('laser', moldGap, moldWallThickness)
        fixtureModel = fixtureModel.setMaterial(2)
        latticeResultMold = latticeResultMold.union(fixtureModel)
    print('Fixture Generated')

    # Create Mesh
    mesh1 = Mesh.fromVoxelModel(latticeResult)
    mesh2 = Mesh.fromVoxelModel(latticeResultMold)
    print('Mesh Created')

    # Create Plot
    plot1 = Plot(mesh1)
    plot1.show()
    plot2 = Plot(mesh2)
    plot2.show()
    app1.processEvents()

    if export:
        mesh2.export('test_coupon_' + lattice_element_file + '.stl')

    app1.exec_()