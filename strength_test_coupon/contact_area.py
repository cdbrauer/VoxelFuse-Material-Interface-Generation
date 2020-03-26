"""
Copyright 2020
Dan Aukes, Cole Brauer

1. Isolate a region of a model
2. Select one material
3. Find the number of faces where this material meets another material
4. Convert number of faces to surface area
"""

# Import Libraries
import PyQt5.QtGui as qg
import sys
import numpy as np
from tqdm import tqdm

from voxelfuse.voxel_model import VoxelModel
from voxelfuse.primitives import *
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    transitionWidth = 12
    transitionCenter = 71.1
    materialToMeasure = 1

    largestOnly = True # Only look at the largest component of each material
    cleanup = False # Remove duplicate materials
    display = False # Display output

    # Open File
    file = 'stl_files_v4.2_combined/output_K'
    model = VoxelModel.openVF(file)
    model.resolution = 5 # Manually set resolution if not set in file
    res = model.resolution

    # Define a region in which to calculate the contact area
    testRegionSize = (round(transitionWidth*res*1.75), model.voxels.shape[1], model.voxels.shape[2])
    testRegionLocation = (model.coords[0] + round(transitionCenter*res) - round(testRegionSize[0]*.5), model.coords[1], model.coords[2])
    test_region = cuboid(testRegionSize, testRegionLocation, material=3, resolution=res)

    # Cleanup operations
    if cleanup:
        model.materials = np.round(model.materials, 3)
        model = model.removeDuplicateMaterials()

    # Crop the model to the region of interest
    model_cropped = VoxelModel.emptyLike(model)
    if largestOnly:
        # Isolate the region of the model that intersects with the test region
        model_cropped_all_components = model & test_region

        # Loop through each material in model
        for m in range(1, len(model_cropped.materials)):
            model_current_material = model_cropped_all_components.isolateMaterial(m)
            model_current_material = model_current_material.getComponents()

            # Find the volume of each component made of this material
            componentVolumes = np.zeros(model_current_material.numComponents+1)
            for c in range(1, model_current_material.numComponents+1):
                componentVolumes[c], _ = model_current_material.getVolume(component=c)

            # Identify the largest component and add to cropped model
            largestComponent = componentVolumes.argmax()
            model_cropped = model_current_material.isolateComponent(largestComponent) | model_cropped
    else:
        # Isolate the region of the model that intersects with the test region
        model_cropped = model & test_region

    # Isolate the material of interest
    model_single_material = model_cropped.isolateMaterial(materialToMeasure)

    # Find exterior voxels
    surfaceVoxelsArray = model_single_material.difference(model_single_material.erode(radius=1, connectivity=1)).voxels

    x_len = surfaceVoxelsArray.shape[0]
    y_len = surfaceVoxelsArray.shape[1]
    z_len = surfaceVoxelsArray.shape[2]

    # Create list of exterior voxel coordinates
    surfaceVoxelCoords = []
    for x in tqdm(range(x_len), desc='Finding exterior voxels'):
        for y in range(y_len):
            for z in range(z_len):
                if surfaceVoxelsArray[x, y, z] != 0:
                    surfaceVoxelCoords.append([x, y, z])

    # Find number of contact surfaces for each surface voxel
    totalSurfaceCount = 0
    for voxel_coords in tqdm(surfaceVoxelCoords, desc='Checking for contact surfaces'):
        x = voxel_coords[0]
        y = voxel_coords[1]
        z = voxel_coords[2]

        if x+1 < x_len:
            if (model_cropped.voxels[x+1, y, z] != 0) and (model_cropped.voxels[x+1, y, z] != materialToMeasure):
                totalSurfaceCount = totalSurfaceCount + 1
        if x-1 >= 0:
            if (model_cropped.voxels[x-1, y, z] != 0) and (model_cropped.voxels[x-1, y, z] != materialToMeasure):
                totalSurfaceCount = totalSurfaceCount + 1

        if y+1 < y_len:
            if (model_cropped.voxels[x, y+1, z] != 0) and (model_cropped.voxels[x, y+1, z] != materialToMeasure):
                totalSurfaceCount = totalSurfaceCount + 1
        if y-1 >= 0:
            if (model_cropped.voxels[x, y-1, z] != 0) and (model_cropped.voxels[x, y-1, z] != materialToMeasure):
                totalSurfaceCount = totalSurfaceCount + 1

        if z+1 < z_len:
            if (model_cropped.voxels[x, y, z+1] != 0) and (model_cropped.voxels[x, y, z+1] != materialToMeasure):
                totalSurfaceCount = totalSurfaceCount + 1
        if z-1 >= 0:
            if (model_cropped.voxels[x, y, z-1] != 0) and (model_cropped.voxels[x, y, z-1] != materialToMeasure):
                totalSurfaceCount = totalSurfaceCount + 1

    print('\nNumber of contact surfaces: ' + str(totalSurfaceCount))
    print('Surface area: ' + str(totalSurfaceCount*(1/res)*(1/res)) + ' mm^2')

    if display:
        mesh = Mesh.fromVoxelModel(model_single_material.setMaterial(4) | model_cropped.setMaterial(3) | model)

        # Create Plot
        plot1 = Plot(mesh, grids=True)
        plot1.show()
        app1.processEvents()
        app1.exec_()