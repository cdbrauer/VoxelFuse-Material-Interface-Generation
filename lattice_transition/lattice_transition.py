"""
Copyright 2019
Dan Aukes, Cole Brauer
"""

# Import Libraries
import PyQt5.QtGui as qg
import sys
import time
from tqdm import tqdm
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.primitives import *

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    lattice_element_file = 'lattice_element_1m'
    min_radius = 1  # min radius that results in a printable structure    (1,  7)
    max_radius = 4  # max radius that results in a viable lattice element (6, 25)

    mold = True
    moldWallThickness = 5
    moldGap = 2

    save = False  # VF file for reopening
    export = False # STL file for slicing
    display = True # Show result in viewer

    box_x = 10
    box_y = 2
    box_z = 2

    start = time.time()

    # Import Models
    latticeModel = VoxelModel.fromVoxFile(lattice_element_file + '.vox')
    lattice_size = latticeModel.voxels.shape[0]
    print('Lattice Element Imported')

    # Generate Base Model
    box1 = cuboid((box_x, box_y, box_z), (0, 0, 0), 1)
    box2 = cuboid((box_x, box_y, box_z), (box_x, 0, 0), 3)
    baseModel = box1.union(box2)
    print('Model Created')

    # Process Models
    modelResult = baseModel.blur(int(round(box_x/6)))
    modelResult = modelResult.scaleValues()
    modelResult = modelResult - modelResult.setMaterial(3)
    modelResult = modelResult.scaleNull()
    print('Model Processed')

    # Generate Dilated Lattice Elements
    latticeElements = [VoxelModel.emptyLike(latticeModel)]
    for r in range(min_radius, max_radius+1):
        latticeElements.append(latticeModel.dilateBounded(r))
    latticeElements.append(cuboid(latticeModel.voxels.shape))
    print('Lattice Elements Generated')

    # Convert processed model to lattice
    latticeResult = VoxelModel.emptyLike(baseModel)

    for x in tqdm(range(box_x * 2), desc='Adding lattice elements'):
        for y in range(box_y):
            for z in range(box_z):
                i = modelResult.voxels[x, y, z]
                density =  modelResult.materials[i, 0] * (1 - modelResult.materials[i, 1])
                r = min(int(density * len(latticeElements)), len(latticeElements) - 1)

                x_new = x * lattice_size
                y_new = y * lattice_size
                z_new = z * lattice_size

                latticeElements[r].coords = (x_new, y_new, z_new)

                latticeResult = latticeResult.union(latticeElements[r])

    latticeResult = latticeResult.setMaterial(1)
    print('Lattice Structure Created')

    # Generate Resin Component
    resinModel = cuboid(latticeResult.voxels.shape, material=3)
    resinModel = resinModel.difference(latticeResult)
    print('Resin Model Created')

    # Generate mold feature
    latticeResultMold = VoxelModel.copy(latticeResult)
    if mold: 
        fixtureModel = latticeResult.union(resinModel).web('laser', moldGap, moldWallThickness)
        fixtureModel = fixtureModel.setMaterial(2)
        latticeResultMold = latticeResultMold.union(fixtureModel)
        print('Fixture Generated')

    end = time.time()
    processingTime = (end - start)
    print("Processing time = %s" % processingTime)

    # Save processed files
    if save:
        latticeResult.saveVF(lattice_element_file + '_' + str(box_x * 2) + 'x' + str(box_y) + 'x' + str(box_z) + '_no_mold')
        latticeResultMold.saveVF(lattice_element_file + '_' + str(box_x * 2) + 'x' + str(box_y) + 'x' + str(box_z))

    # Create Mesh
    if display or export:
        mesh1 = Mesh.fromVoxelModel(latticeResult)
        mesh2 = Mesh.fromVoxelModel(latticeResultMold)
        print('Mesh Created')

        # Create Plot
        if display:
            plot1 = Plot(mesh1)
            plot1.show()
            plot2 = Plot(mesh2)
            plot2.show()
            app1.processEvents()

        # Create stl files
        if export:
            mesh1.export(lattice_element_file + '_' + str(box_x * 2) + 'x' + str(box_y) + 'x' + str(box_z) + '_no_mold.stl')
            mesh2.export(lattice_element_file + '_' + str(box_x * 2) + 'x' + str(box_y) + 'x' + str(box_z) + '.stl')

    app1.exec_()
