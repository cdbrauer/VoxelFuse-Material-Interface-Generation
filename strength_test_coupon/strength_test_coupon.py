"""
Copyright 2018
Dan Aukes, Cole Brauer

Generate coupon for tensile testing
"""

import PyQt5.QtGui as qg
import sys
import time

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

    new_model = new_model.union(input_model)

    return new_model

if __name__=='__main__':
    # Settings
    stl = False
    highRes = False

    blurRadius = 8
    blurEnable = False

    ditherEnable = True
    thinEnable = True

    latticeEnable = False
    lattice_element_file = 'lattice_element_1m'
    min_radius = 1  # min radius that results in a printable structure
    max_radius = 6  # radius that results in a solid cube

    resultScale = 5

    mold = False
    moldWallThickness = 2
    moldGap = 1

    fixture = False
    fixtureWallThickness = 5
    fixtureGap = 1

    save = True
    export = False

    app1 = qg.QApplication(sys.argv)

    # Import coupon components
    print('Importing Files')
    if stl:
        # TODO: Improve dimensional accuracy of stl model import and use these files instead of vox file
        if highRes:
            end1 = VoxelModel.fromMeshFile('end1x10.stl', (0, 0, 0))
            center = VoxelModel.fromMeshFile('centerx10.stl', (670, 30, 0))
            end2 = VoxelModel.fromMeshFile('end2x10.stl', (980, 0, 0))
        else:
            end1 = VoxelModel.fromMeshFile('end1.stl', (0, 0, 0))
            center = VoxelModel.fromMeshFile('center.stl', (67, 3, 0))
            end2 = VoxelModel.fromMeshFile('end2.stl', (98, 0, 0))

        # Set materials
        end1 = end1.setMaterial(1)
        end2 = end2.setMaterial(1)
        center = center.setMaterial(2)

        # Combine components
        coupon = VoxelModel.copy(end1.union(center.union(end2)))
    else: # use vox file
        coupon = VoxelModel.fromVoxFile('coupon.vox') # Should use materials 1 and 2 (red and green)

    start = time.time()

    if blurEnable: # Blur materials
        print('Blurring')
        coupon = coupon.blur(blurRadius)
        coupon = coupon.scaleValues()

    elif ditherEnable: # Dither materials
        print('Dithering')
        coupon = dither(coupon, blurRadius)
        coupon = coupon.scaleValues()

    elif latticeEnable:
        print('Lattice')

        coupon = coupon.scale(0.333, interpolate=True)

        box_x = coupon.voxels.shape[0]
        box_y = coupon.voxels.shape[1]
        box_z = coupon.voxels.shape[2]

        # Import Models
        latticeModel = VoxelModel.fromVoxFile(lattice_element_file + '.vox')
        lattice_size = latticeModel.voxels.shape[0]
        print('Lattice Element Imported')

        # Process Models
        modelResult = coupon.blur(int(round(blurRadius/3)))
        modelResult = modelResult - modelResult.setMaterial(2)
        modelResult = modelResult.scaleNull()
        print('Model Processed')

        # Generate Dilated Lattice Elements
        latticeElements = [VoxelModel.emptyLike(latticeModel)]
        for r in range(min_radius, max_radius+1):
            latticeElements.append(latticeModel.dilateBounded(r))
        print('Lattice Elements Generated')

        # Convert processed model to lattice
        latticeResult = VoxelModel.emptyLike(coupon)

        for x in tqdm(range(box_x), desc='Adding lattice elements'):
            for y in range(box_y):
                for z in range(box_z):
                    i = modelResult.voxels[x, y, z]
                    density =  modelResult.materials[i, 0] * (1 - modelResult.materials[i, 1])
                    if density > 0:
                        r = int(round(density * (max_radius - min_radius))) + min_radius
                    else:
                        r = 0

                    x_new = x * lattice_size
                    y_new = y * lattice_size
                    z_new = z * lattice_size

                    latticeElements[r].coords = (x_new, y_new, z_new)

                    latticeResult = latticeResult.union(latticeElements[r])

        latticeResult = latticeResult.setMaterial(1)
        print('Lattice Structure Created')

        # Generate Resin Component
        resinModel = Solid.cuboid((box_x * lattice_size, box_y * lattice_size, box_z * lattice_size), material=3)
        resinModel = resinModel.intersection(coupon.scale(lattice_size))
        resinModel = resinModel.difference(latticeResult)
        print('Resin Model Created')

        coupon = latticeResult.union(resinModel)

    if not latticeEnable:
        coupon = coupon.scale(resultScale)

    if ditherEnable and thinEnable:
        coupon_ends = coupon.isolateMaterial(2)
        coupon_center = coupon.isolateMaterial(1)

        coupon_ends = coupon_ends.closing(2, Axes.XY)
        coupon_ends = thin(coupon_ends, int(resultScale/2)+1)
        coupon_ends = coupon_ends.dilate(1)
        coupon_ends = coupon_ends.dilate(resultScale, plane=Axes.Z)

        coupon_center = coupon_center.dilate(resultScale)
        coupon = coupon_ends.union(coupon_center).intersection(coupon)

    if mold: # Generate mold feature around material 2
        print('Generating Mold')

        # Find all voxels containing <50% material 2
        material_vector = np.zeros(len(material_properties) + 1)
        material_vector[0] = 1
        material_vector[3] = 0.5
        printed_components = coupon - coupon.setMaterialVector(material_vector)
        printed_components.materials = np.around(printed_components.materials, 0)
        printed_components = printed_components.scaleValues()

        # Generate mold body
        mold_model = coupon.difference(printed_components).dilate(moldWallThickness+1, plane=Axes.XY)

        # Find clearance to prevent mold from sticking to model and apply clearance to body
        mold_model = mold_model.difference(printed_components.dilate(moldGap, plane=Axes.XY))

        if fixture: # Generate a fixture around the full part to support mold
            print('Generating Fixture')
            coupon = coupon.union(coupon.web('laser', 1, 5).setMaterial(3))

        # Add mold to coupon model
        coupon = coupon.union(mold_model.setMaterial(3))

    end = time.time()
    processingTime = (end - start)
    print("Processing time = %s" % processingTime)

    # Create mesh data
    print('Meshing')
    mesh1 = Mesh.fromVoxelModel(coupon)

    # Create plot
    print('Plotting')
    plot1 = Plot(mesh1, grids=False, drawEdges=False)
    plot1.show()
    app1.processEvents()

    if save:
        print('Saving')
        coupon.saveVF('output')

    if export:
        print('Exporting')

        # Get non-cast components
        # Find all voxels containing <50% material 2
        material_vector = np.zeros(len(material_properties) + 1)
        material_vector[0] = 1
        material_vector[3] = 0.5
        printed_components = coupon - coupon.setMaterialVector(material_vector)
        printed_components.materials = np.around(printed_components.materials, 0)
        printed_components = printed_components.scaleValues()
        printed_components = printed_components.setMaterial(1)

        mesh2 = Mesh.fromVoxelModel(printed_components)
        plot2 = Plot(mesh2, grids=True)
        plot2.show()
        app1.processEvents()
        mesh2.export('modified-coupon.stl')

    app1.exec_()