"""
Copyright 2018
Dan Aukes, Cole Brauer

Generate coupon for tensile testing
"""

import os
import sys
import time

import PyQt5.QtGui as qg
from tqdm import tqdm

from voxelfuse.voxel_model import VoxelModel
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.primitives import *
from voxelfuse.voxel_model import Axes

from dithering.dither import dither
from dithering.thin import thin

if __name__=='__main__':
    # Settings
    stl = True
    res = 5 # voxels per mm
    couponStandard = 'D638' # Start of stl file name

    processingRes = 4 # voxels per processed voxel
    blurRadius = 6 # mm -- transition region width * 1/2

    blurEnable = True
    ditherEnable = False
    thinEnable = False
    latticeEnable = False

    latticeElementFile = 'lattice_element_1_15x15'
    minRadius = 0  # min radius that results in a printable structure
    maxRadius = 5  # max radius that results in a viable lattice element

    materialDecimals = 2 # material resolution of final result

    display = False
    save = False
    export = True

    app1 = qg.QApplication(sys.argv)

    # Import coupon components
    print('Importing Files')
    if stl:
        end1 = VoxelModel.fromMeshFile('coupon_templates/' + couponStandard + '-End.stl', (0, 0, 0), resolution=res).fitWorkspace()
        center = VoxelModel.fromMeshFile('coupon_templates/' + couponStandard + '-Center.stl', (0, 0, 0), resolution=res).fitWorkspace()
        end2 = end1.rotate90(2, axis=Axes.Z)
        center.coords = (end1.voxels.shape[0], round((end1.voxels.shape[1] - center.voxels.shape[1]) / 2), 0)
        end2.coords = (end1.voxels.shape[0] + center.voxels.shape[0], 0, 0)

        # Set materials
        end1 = end1.setMaterial(1)
        end2 = end2.setMaterial(1)
        center = center.setMaterial(2)

        # Combine components
        coupon = end1 | center | end2

    else: # use vox file
        end1 = VoxelModel.fromVoxFile('coupon_templates/' + 'coupon_end1.vox', (0, 0, 0)) # Should use materials 1 and 2 (red and green)
        center = VoxelModel.fromVoxFile('coupon_templates/' + 'coupon_center.vox', (113, 8, 0))
        end2 = VoxelModel.fromVoxFile('coupon_templates/' + 'coupon_end2.vox', (197, 0, 0))
        coupon = end1 | center | end2

    # Generate transition region areas
    transition_1 = cuboid((blurRadius*res*2, coupon.voxels.shape[1], coupon.voxels.shape[2]), (center.coords[0]-(blurRadius*res), 0, 0), 3)
    transition_2 = cuboid((blurRadius*res*2, coupon.voxels.shape[1], coupon.voxels.shape[2]), (end2.coords[0]-(blurRadius*res), 0, 0), 3)
    transition_regions = transition_1 | transition_2

    start = time.time()

    if blurEnable: # Blur materials
        print('Blurring')
        coupon_scaled = coupon.scale((1 / processingRes), interpolate=True).dilate()
        coupon_scaled = coupon_scaled.blur(blurRadius*(res/processingRes))
        coupon_scaled = coupon_scaled.scaleValues()
        coupon_result = coupon_scaled.scale(processingRes).intersection(coupon)

    elif ditherEnable: # Dither materials
        print('Dithering')
        coupon_scaled = coupon.scale((1 / processingRes), interpolate=True).dilate()
        coupon_scaled = dither(coupon_scaled, blurRadius*(res/processingRes)*3)
        coupon_scaled = coupon_scaled.scaleValues()
        coupon_result = coupon_scaled.scale(processingRes).intersection(coupon)

    elif latticeEnable:
        print('Lattice')

        # Import Models
        lattice_model = VoxelModel.fromVoxFile("lattice_elements/" + latticeElementFile + '.vox')
        latticeSize = lattice_model.voxels.shape[0]
        print('Lattice Element Imported')

        # Generate Dilated Lattice Elements
        lattice_elements = [VoxelModel.emptyLike(lattice_model)]
        for r in range(minRadius, maxRadius + 1):
            lattice_elements.append(lattice_model.dilateBounded(r))
        lattice_elements.append(cuboid(lattice_model.voxels.shape))
        print('Lattice Elements Generated')

        # Process Models
        latticeLocations = coupon.scale((1 / latticeSize), interpolate=True).dilate()
        latticeLocations = latticeLocations.blur(blurRadius*(res/latticeSize)*2.5)
        latticeLocations = latticeLocations.scaleValues()
        latticeLocations = latticeLocations - latticeLocations.setMaterial(2)
        latticeLocations = latticeLocations.scaleNull()
        latticeLocations.coords = (0,0,0)

        boxX = latticeLocations.voxels.shape[0]
        boxY = latticeLocations.voxels.shape[1]
        boxZ = latticeLocations.voxels.shape[2]

        print('Model Processed')

        # Convert processed model to lattice
        lattice_result = VoxelModel.emptyLike(latticeLocations)

        for x in tqdm(range(boxX), desc='Adding lattice elements'):
            for y in range(boxY):
                for z in range(boxZ):
                    i = latticeLocations.voxels[x, y, z]
                    density =  latticeLocations.materials[i, 0] * (1 - latticeLocations.materials[i, 1])
                    r = min(int(density * len(lattice_elements)), len(lattice_elements) - 1)

                    xNew = x * latticeSize
                    yNew = y * latticeSize
                    zNew = z * latticeSize

                    lattice_elements[r].coords = (xNew, yNew, zNew)

                    lattice_result = lattice_result.union(lattice_elements[r])

        lattice_result = lattice_result.setMaterial(1)
        lattice_result.coords = (-latticeSize, -latticeSize, -latticeSize)
        lattice_result = lattice_result.intersection(coupon)
        print('Lattice Structure Created')

        # Generate Resin Component
        resin_model = cuboid(coupon.voxels.shape, material=2)
        resin_model = resin_model.intersection(coupon)
        resin_model = resin_model.difference(lattice_result)
        print('Resin Model Created')

        coupon_result = lattice_result.union(resin_model)

    if ditherEnable and thinEnable:
        coupon_ends = coupon_result.isolateMaterial(1)
        coupon_center = coupon_result.isolateMaterial(2)

        coupon_ends = coupon_ends.closing(round((processingRes / 2) - 1), Axes.XY)
        coupon_ends = thin(coupon_ends, int(processingRes / 2) + 1)
        coupon_ends = coupon_ends.dilate(1)
        coupon_ends = coupon_ends.dilate(processingRes, plane=Axes.Z)

        coupon_center = coupon_center.dilate(processingRes)
        coupon_result = coupon_ends.union(coupon_center).intersection(coupon)

    coupon_result.materials = np.round(coupon_result.materials, materialDecimals)
    coupon_result = coupon_result.removeDuplicateMaterials()
    coupon_result = coupon_result.intersection(transition_regions).union(coupon)

    end = time.time()
    processingTime = (end - start)
    print("Processing time = %s" % processingTime)

    if display:
        # Create mesh data
        print('Meshing')
        mesh1 = Mesh.fromVoxelModel(coupon_result, resolution=res)

        # Create plot
        print('Plotting')
        plot1 = Plot(mesh1, drawEdges=True, positionOffset = (35, 2, 0), viewAngle=(50, 40, 200), resolution=(720, 720), name=couponStandard)
        plot1.show()
        app1.processEvents()

    if save:
        print('Saving')
        coupon_result.saveVF('output')

    if export:
        print('Exporting')

        try:
            os.mkdir('stl_output')
        except OSError:
            print('Output folder already exists')
        else:
            print('Output folder successfully created')

        for m in range(1, len(coupon_result.materials)):
            current_mesh = Mesh.fromVoxelModel(coupon_result.isolateMaterial(m), resolution=res)
            current_mesh.export(('stl_output/' + couponStandard + '_mat_' + str(m) + '_' + str(coupon_result.materials[m, 2]) + '.stl'))

    print('Finished')

    app1.exec_()