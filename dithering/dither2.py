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
    x_len = model.voxels.shape[0] + 2
    y_len = model.voxels.shape[1] + 2
    z_len = model.voxels.shape[2] + 2

    new_voxels = np.zeros((x_len, y_len, z_len), dtype=np.int32)
    new_voxels[1:-1, 1:-1, 1:-1] = model.voxels

    #struct1 = ndimage.generate_binary_structure(3, 1)
    #struct2 = ndimage.generate_binary_structure(3, 2)
    struct3 = ndimage.generate_binary_structure(3, 3)

    boundaryDirections = np.array([[0,0,0], [2,0,0], [0,2,0], [0,0,2], [2,2,0], [2,0,2], [0,2,2], [2,2,2]])
    #boundaryDirections = np.array([[0,1,1], [1,0,1], [1,1,0], [2,1,1], [1,2,1], [1,1,2]])
    numDirections = len(boundaryDirections)

    for i in tqdm(range(max_iter), desc='Thinning'):
        last_voxels = np.copy(new_voxels)
        deletions = 0

        for x in range(1,x_len-1): #, desc='Thinning pass '+str(i)):
            for y in range(1,y_len-1):
                for z in range(1,z_len-1):
                    if last_voxels[x,y,z] != 0:
                        n = np.copy(last_voxels[x-1:x+2, y-1:y+2, z-1:z+2])
                        n[1,1,1] = 0
                        n[n != 0] = 1

                        # Find C
                        C = ndimage.label(n, structure=struct3)[1]

                        # Find N
                        N = n[0,1,1] + n[1,0,1] + n[1,1,0] + n[2,1,1] + n[1,2,1] + n[1,1,2]

                        # Find D
                        d = boundaryDirections[i%numDirections]
                        D = n[d[0], 1, 1] + n[1, d[1], 1] + n[1, 1, d[2]] + n[d[0], d[1], 1] + n[1, d[1], d[2]] + n[d[0], 1, d[2]] + n[d[0], d[1], d[2]]
                        #D = D + n[1, 2-d[1], d[2]] + n[d[0], 2-d[1], 1] + n[d[0], 2-d[1], d[2]]
                        #D = n[d[0], d[1], d[2]]

                        # Apply conditions
                        if (C==1) and (N>=2) and (N<=4) and (D==0):
                            new_voxels[x, y, z] = 0
                            deletions = deletions + 1

        if deletions == 0 and (i%numDirections == numDirections-1):
            break

    return VoxelModel(new_voxels, model.materials, model.coords)

if __name__ == '__main__':
    app1 = qg.QApplication(sys.argv)

    box_x = 25
    box_y = 10
    box_z = 10

    # Create base model
    box1 = Solid.cuboid((box_x, box_y, box_z), (0, 0, 0), 1)
    box2 = Solid.cuboid((box_x, box_y, box_z), (box_x, 0, 0), 3)
    baseModel = box1.union(box2)
    print('Model Created')

    # Process Model
    ditherResult = dither(baseModel, int(round(box_x/2)))

    # Scale result
    ditherResult = ditherResult.scale(5)

    # Isolate materials
    result1 = ditherResult.isolateMaterial(1)
    result2 = ditherResult.isolateMaterial(2)

    result1 = result1.closing(2, Axes.XY)
    result1 = thin(result1, 5000)

    # Save result
    result1.saveVF('thin_model')

    # Create mesh
    ditherMesh = Mesh.fromVoxelModel(result1)

    # Create plot
    plot1 = Plot(ditherMesh)
    plot1.show()

    app1.processEvents()
    app1.exec_()