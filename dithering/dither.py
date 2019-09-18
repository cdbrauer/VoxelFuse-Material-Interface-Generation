import PyQt5.QtGui as qg
import sys

import numpy as np
from scipy import ndimage

from voxelfuse.materials import material_properties
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.voxel_model import VoxelModel

from voxelfuse_primitives.solid import Solid

def dither(model, radius=1):
    if radius == 0:
        return VoxelModel.copy(model)

    x_len = model.voxels.shape[0]
    y_len = model.voxels.shape[1]
    z_len = model.voxels.shape[2]

    full_model = np.zeros((x_len, y_len, z_len, len(material_properties)+1), dtype=np.float)

    for x in range(x_len):
        for y in range(y_len):
            for z in range(z_len):
                i = model.voxels[x,y,z]
                full_model[x,y,z,:] = model.materials[i]

    for m in range(len(material_properties)):
        full_model[:, :, :, m+1] = ndimage.gaussian_filter(full_model[:, :, :, m+1], sigma=radius)

    mask = full_model[:, :, :, 0]
    mask = np.repeat(mask[..., None], len(material_properties)+1, axis=3)
    full_model = np.multiply(full_model, mask)

    for x in range(x_len):
        for y in range(y_len):
            for z in range(z_len):
                voxel = full_model[x, y, z]
                if voxel[0] > 0:
                    max_i = voxel[1:].argmax()+1
                    for i in range(1, len(voxel)):
                        old = full_model[x, y, z, i]

                        if i == max_i:
                            full_model[x, y, z, i] = 1
                        else:
                            full_model[x, y, z, i] = 0

                        error = old - full_model[x, y, z, i]
                        if y+1 < y_len:
                            full_model[x, y+1, z, i] += error * (3/10) * full_model[x, y+1, z, 0]
                        if y+1 < y_len and x+1 < x_len:
                            full_model[x+1, y+1, z, i] += error * (1/5) * full_model[x+1, y+1, z, 0]
                        if y+1 < y_len and x+1 < x_len and z+1 < z_len:
                            full_model[x+1, y+1, z+1, i] += error * (1/5) * full_model[x+1, y+1, z+1, 0]
                        if x+1 < x_len:
                            full_model[x+1, y, z, i] += error * (3/10) * full_model[x+1, y, z, 0]

    new_voxels = np.zeros_like(model.voxels, dtype=int)
    new_materials = np.zeros((1, len(material_properties) + 1), dtype=np.float)

    for x in range(x_len):
        for y in range(y_len):
            for z in range(z_len):
                m = full_model[x, y, z, :]
                i = np.where(np.equal(new_materials, m).all(1))[0]

                if len(i) > 0:
                    new_voxels[x, y, z] = i[0]
                else:
                    new_materials = np.vstack((new_materials, m))
                    new_voxels[x, y, z] = len(new_materials) - 1

    return VoxelModel(new_voxels, new_materials, model.x, model.y, model.z)

if __name__ == '__main__':
    app1 = qg.QApplication(sys.argv)

    box_x = 100
    box_y = 20
    box_z = 20

    box1 = Solid.cuboid((box_x, box_y, box_z), (0, 0, 0), 1)
    box2 = Solid.cuboid((box_x, box_y, box_z), (box_x, 0, 0), 3)
    baseModel = box1.union(box2)
    print('Model Created')

    # Process Models
    blurResult = baseModel.blur(int(round(box_x/4)))
    ditherResult = dither(baseModel, int(round(box_x/4)))

    blurMesh = Mesh.fromVoxelModel(blurResult)
    ditherMesh = Mesh.fromVoxelModel(ditherResult)

    plot1 = Plot(blurMesh)
    plot2 = Plot(ditherMesh)

    plot1.show()
    plot2.show()

    app1.processEvents()
    app1.exec_()