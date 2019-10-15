import PyQt5.QtGui as qg
import sys

import numpy as np
from scipy import ndimage
from tqdm import tqdm

from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.primitives import cuboid
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.voxel_model import Axes
from voxelfuse.voxel_model import Struct

from dithering.dither import dither

def thin(model, max_iter):
    x_len = model.voxels.shape[0] + 4
    y_len = model.voxels.shape[1] + 4
    z_len = model.voxels.shape[2] + 4

    struct = ndimage.generate_binary_structure(3, 3)

    sphere = np.zeros((5, 5, 5), dtype=np.int32)
    for x in range(5):
        for y in range(5):
            for z in range(5):
                xd = (x - 2)
                yd = (y - 2)
                zd = (z - 2)
                r = np.sqrt(xd ** 2 + yd ** 2 + zd ** 2)

                if r < 2.5:
                    sphere[x, y, z] = 1

    input_model = VoxelModel(np.zeros((x_len, y_len, z_len), dtype=np.int32), model.materials, model.coords)
    input_model.voxels[2:-2, 2:-2, 2:-2] = model.voxels
    new_model = VoxelModel.emptyLike(input_model)

    for i in tqdm(range(max_iter), desc='Thinning'):
        # Find exterior voxels
        interior_voxels = input_model.erode(radius=1, plane=Axes.XYZ, structType=Struct.STANDARD, connectivity=1)
        exterior_voxels = input_model.difference(interior_voxels)

        x_len = len(exterior_voxels.voxels[:, 0, 0])
        y_len = len(exterior_voxels.voxels[0, :, 0])
        z_len = len(exterior_voxels.voxels[0, 0, :])

        # Create list of exterior voxel coordinates
        exterior_coords = []
        for x in range(x_len):
            for y in range(y_len):
                for z in range(z_len):
                    if exterior_voxels.voxels[x, y, z] != 0:
                        exterior_coords.append([x, y, z])

        # Store voxels that must be part of the center line
        for coords in exterior_coords:
            x = coords[0]
            y = coords[1]
            z = coords[2]

            if input_model.voxels[x,y,z] != 0:
                # Get matrix of neighbors
                n = np.copy(input_model.voxels[x - 2:x + 3, y - 2:y + 3, z - 2:z + 3])
                n[n != 0] = 1

                # Find V - number of voxels near current along xyz axes
                Vx = np.sum(n[:, 2, 2])
                Vy = np.sum(n[2, :, 2])
                Vz = np.sum(n[2, 2, :])

                # Subtract sphere
                n = n - sphere
                n[n < 1] = 0

                # Check if subtraction split model
                C = ndimage.label(n, structure=struct)[1]

                # Apply conditions
                if (C > 1) or (Vx <= 2) or (Vy <= 2) or (Vz <= 2):
                    new_model.voxels[x, y, z] = input_model.voxels[x, y, z]

        if np.sum(interior_voxels.voxels) < 1:
            break
        else:
            input_model = VoxelModel.copy(interior_voxels)

    new_model = new_model.union(input_model)

    return new_model

if __name__ == '__main__':
    app1 = qg.QApplication(sys.argv)

    box_x = 25
    box_y = 10
    box_z = 10

    # Create base model
    box1 = cuboid((box_x, box_y, box_z), (0, 0, 0), 1)
    box2 = cuboid((box_x, box_y, box_z), (box_x, 0, 0), 3)
    result1 = box1.union(box2)
    print('Model Created')

    # Process Model
    ditherResult = dither(result1, int(round(box_x/2)))

    # Scale result
    ditherResult = ditherResult.scale(5) # 15

    # Isolate materials
    result1 = ditherResult.isolateMaterial(1)
    result2 = ditherResult.isolateMaterial(2)

    result1 = result1.closing(2, Axes.XY) # 7
    result1 = thin(result1, 3) #100

    # Save result
    result1.saveVF('thin-test')

    # Create mesh
    ditherMesh = Mesh.fromVoxelModel(result1)

    # Create plot
    plot1 = Plot(ditherMesh)
    plot1.show()

    app1.processEvents()
    app1.exec_()