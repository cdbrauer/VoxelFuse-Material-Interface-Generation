import PyQt5.QtGui as qg
import sys

import numpy as np

from voxelfuse.materials import material_properties
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.primitives import cuboid
from voxelfuse.voxel_model import VoxelModel

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
def addError(model, error, constant, i, x, y, z, x_len, y_len, z_len, error_spread_threshold):
    if y < y_len and x < x_len and z < z_len:
        high = np.where(model[x, y, z, 1:] > error_spread_threshold)[0]
        if len(high) == 0:
            model[x, y, z, i] += error * constant * model[x, y, z, 0]

@njit()
def ditherOptimized(full_model, use_full, x_error, y_error, z_error, error_spread_threshold):
    x_len = full_model.shape[0]
    y_len = full_model.shape[1]
    z_len = full_model.shape[2]

    for z in range(z_len):
        for y in range(y_len):
            for x in range(x_len):
                voxel = full_model[x, y, z]
                if voxel[0] == 1.0:
                    max_i = voxel[1:].argmax()+1
                    for i in range(1, len(voxel)):
                        if full_model[x, y, z, i] != 0:
                            old = full_model[x, y, z, i]

                            if i == max_i:
                                full_model[x, y, z, i] = 1
                            else:
                                full_model[x, y, z, i] = 0

                            error = old - full_model[x, y, z, i]

                            if use_full:
                                # Based on Fundamentals of 3D Halftoning by Lou and Stucki
                                addError(full_model, error, 4/21, i, x+1, y, z, x_len, y_len, z_len, error_spread_threshold)
                                addError(full_model, error, 1/21, i, x+2, y, z, x_len, y_len, z_len, error_spread_threshold)

                                addError(full_model, error, 4/21, i, x, y+1, z, x_len, y_len, z_len, error_spread_threshold)
                                addError(full_model, error, 1/21, i, x, y+2, z, x_len, y_len, z_len, error_spread_threshold)

                                addError(full_model, error, 1/21, i, x+1, y+1, z, x_len, y_len, z_len, error_spread_threshold)
                                addError(full_model, error, 1/21, i, x-1, y+1, z, x_len, y_len, z_len, error_spread_threshold)

                                addError(full_model, error, 1/21, i, x, y-1, z+1, x_len, y_len, z_len, error_spread_threshold)
                                addError(full_model, error, 1/21, i, x-1, y, z+1, x_len, y_len, z_len, error_spread_threshold)
                                addError(full_model, error, 1/21, i, x, y+1, z+1, x_len, y_len, z_len, error_spread_threshold)
                                addError(full_model, error, 1/21, i, x+1, y, z+1, x_len, y_len, z_len, error_spread_threshold)

                                addError(full_model, error, 4/21, i, x, y, z+1, x_len, y_len, z_len, error_spread_threshold)
                                addError(full_model, error, 1/21, i, x, y, z+2, x_len, y_len, z_len, error_spread_threshold)
                            else:
                                addError(full_model, error, x_error, i, x+1, y, z, x_len, y_len, z_len, error_spread_threshold)
                                addError(full_model, error, y_error, i, x, y+1, z, x_len, y_len, z_len, error_spread_threshold)
                                addError(full_model, error, z_error, i, x, y, z+1, x_len, y_len, z_len, error_spread_threshold)

    return full_model

def dither(model, radius=1, use_full=True, x_error=0.0, y_error=0.0, z_error=0.0, error_spread_threshold=0.8, blur=True):
    if radius == 0:
        return VoxelModel.copy(model)

    if blur:
        new_model = model.blur(radius)
        new_model = new_model.scaleValues()
    else:
        new_model = model.scaleValues()

    full_model = toFullMaterials(new_model.voxels, new_model.materials, len(material_properties)+1)
    full_model = ditherOptimized(full_model, use_full, x_error, y_error, z_error, error_spread_threshold)

    return toIndexedMaterials(full_model, model)

if __name__ == '__main__':
    app1 = qg.QApplication(sys.argv)

    box_x = 25
    box_y = 40
    box_z = 40

    box1 = cuboid((box_x, box_y, box_z), (0, 0, 0), 1)
    box2 = cuboid((box_x, box_y, box_z), (box_x, 0, 0), 3)
    box3 = cuboid((box_x, box_y, box_z), (box_x*2, 0, 0), 1)
    baseModel = box1 | box2 | box3
    print('Model Created')

    # Process Models
    blurResult = baseModel.blur(int(round(box_x/2)))
    ditherResult = dither(baseModel, int(round(box_x/2)))

    # Create mesh data
    for m in range(1, len(ditherResult.materials)):
        currentMaterial = ditherResult.isolateMaterial(m)
        currentMesh = Mesh.fromVoxelModel(currentMaterial)
        currentMesh.export('output_' + str(m) + '.stl')

    baseMesh = Mesh.fromVoxelModel(baseModel)
    blurMesh = Mesh.fromVoxelModel(blurResult)
    ditherMesh = Mesh.fromVoxelModel(ditherResult)

    plot1 = Plot(baseMesh)
    plot2 = Plot(blurMesh)
    plot3 = Plot(ditherMesh)

    plot1.show()
    plot2.show()
    plot3.show()

    app1.processEvents()
    app1.exec_()