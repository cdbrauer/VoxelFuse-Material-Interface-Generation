import PyQt5.QtGui as qg
import sys

import numpy as np
from scipy import ndimage
from tqdm import tqdm

from voxelfuse.materials import material_properties
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.voxel_model import Axes
from voxelfuse.voxel_model import Struct
from voxelfuse_primitives.solid import Solid

from numba import njit

@njit()
def toFullMaterials(voxels, materials, n_materials):
    x_len = voxels.shape[0]
    y_len = voxels.shape[1]
    z_len = voxels.shape[2]

    full_model = np.zeros((x_len, y_len, z_len, n_materials), dtype=np.float32)

    for x in range(x_len):
        for y in range(y_len):
            for z in range(z_len):
                i = voxels[x,y,z]
                full_model[x,y,z,:] = materials[i]

    return full_model

def toIndexedMaterials(voxels, model):
    x_len = model.voxels.shape[0]
    y_len = model.voxels.shape[1]
    z_len = model.voxels.shape[2]

    new_voxels = np.zeros((x_len, y_len, z_len), dtype=np.int32)
    new_materials = np.zeros((1, len(material_properties) + 1), dtype=np.float32)

    for x in range(x_len):
        for y in range(y_len):
            for z in range(z_len):
                m = voxels[x, y, z, :]
                i = np.where(np.equal(new_materials, m).all(1))[0]

                if len(i) > 0:
                    new_voxels[x, y, z] = i[0]
                else:
                    new_materials = np.vstack((new_materials, m))
                    new_voxels[x, y, z] = len(new_materials) - 1

    return VoxelModel(new_voxels, new_materials, model.coords)

@njit()
def addError(model, error, constant, i, x, y, z, x_len, y_len, z_len):
    if y < y_len and x < x_len and z < z_len:
        model[x, y, z, i] += error * constant * model[x, y, z, 0]

@njit()
def ditherOptimized(full_model):
    x_len = full_model.shape[0]
    y_len = full_model.shape[1]
    z_len = full_model.shape[2]

    for x in range(x_len):
        for y in range(y_len):
            for z in range(z_len):
                voxel = full_model[x, y, z]
                if voxel[0] > 0:
                    max_i = voxel[1:].argmax()+1
                    for i in range(1, len(voxel)):
                        if full_model[x, y, z, i] != 0:
                            old = full_model[x, y, z, i]

                            if i == max_i:
                                full_model[x, y, z, i] = 1
                            else:
                                full_model[x, y, z, i] = 0

                            error = old - full_model[x, y, z, i]

                            # Original dither
                            # addError(full_model, error, 3/10, i, x, y+1, z, x_len, y_len, z_len)
                            # addError(full_model, error, 1/5, i, x+1, y+1, z, x_len, y_len, z_len)
                            # addError(full_model, error, 1/5, i, x+1, y+1, z+1, x_len, y_len, z_len)
                            # addError(full_model, error, 3/10, i, x+1, y, z, x_len, y_len, z_len)

                            # New dither (based on Fundamentals of 3D Halftoning by Lou and Stucki)
                            # addError(full_model, error, 4/21, i, x+1, y, z, x_len, y_len, z_len)
                            # addError(full_model, error, 1/21, i, x+2, y, z, x_len, y_len, z_len)
                            #
                            # addError(full_model, error, 4/21, i, x, y+1, z, x_len, y_len, z_len)
                            # addError(full_model, error, 1/21, i, x, y+2, z, x_len, y_len, z_len)
                            #
                            # addError(full_model, error, 1/21, i, x+1, y+1, z, x_len, y_len, z_len)
                            # addError(full_model, error, 1/21, i, x-1, y+1, z, x_len, y_len, z_len)
                            #
                            # addError(full_model, error, 1/21, i, x, y-1, z+1, x_len, y_len, z_len)
                            # addError(full_model, error, 1/21, i, x-1, y, z+1, x_len, y_len, z_len)
                            # addError(full_model, error, 1/21, i, x, y+1, z+1, x_len, y_len, z_len)
                            # addError(full_model, error, 1/21, i, x+1, y, z+1, x_len, y_len, z_len)
                            #
                            # addError(full_model, error, 4/21, i, x, y, z+1, x_len, y_len, z_len)
                            # addError(full_model, error, 1/21, i, x, y, z+2, x_len, y_len, z_len)

                            # X-only
                            # addError(full_model, error, 1/3, i, x+1, y, z, x_len, y_len, z_len)
                            # Y-only
                            addError(full_model, error, 1/3, i, x, y+1, z, x_len, y_len, z_len)
                            # Z-only
                            # addError(full_model, error, 1/3, i, x, y, z+1, x_len, y_len, z_len)

    return full_model

def dither(model, radius=1):
    if radius == 0:
        return VoxelModel.copy(model)

    full_model = toFullMaterials(model.voxels, model.materials, len(material_properties)+1)
    for m in range(len(material_properties)):
        full_model[:, :, :, m+1] = ndimage.gaussian_filter(full_model[:, :, :, m+1], sigma=radius)

    mask = full_model[:, :, :, 0]
    mask = np.repeat(mask[..., None], len(material_properties)+1, axis=3)
    full_model = np.multiply(full_model, mask)

    full_model = ditherOptimized(full_model)

    return toIndexedMaterials(full_model, model)

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

    return new_model

if __name__ == '__main__':
    app1 = qg.QApplication(sys.argv)

    box_x = 25
    box_y = 10
    box_z = 10

    # Create base model
    box1 = Solid.cuboid((box_x, box_y, box_z), (0, 0, 0), 1)
    box2 = Solid.cuboid((box_x, box_y, box_z), (box_x, 0, 0), 3)
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
    result1 = thin(result1, 50) #100

    # Save result
    result1.saveVF('thin-test')

    # Create mesh
    ditherMesh = Mesh.fromVoxelModel(result1)

    # Create plot
    plot1 = Plot(ditherMesh)
    plot1.show()

    app1.processEvents()
    app1.exec_()