"""
Copyright 2020
Dan Aukes, Cole Brauer

Generate coupon for tensile testing
"""

import os
import sys
import time
import math
import yaml

import PyQt5.QtGui as qg
from tqdm import tqdm

from voxelfuse.voxel_model import VoxelModel
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.primitives import *
from voxelfuse.periodic import *
from voxelfuse.voxel_model import Axes

from dithering.dither import dither

configIDs = ['LA', 'LC', 'LD', 'LE', 'LF', 'LG', 'LH', 'LI', 'LJ', 'LK']
# configIDs = ['LJ', 'LK']
# configIDs = ['B1', 'B2'] # ['A', 'B', 'C', 'E']

# Set desired outputs
display = False
save = True
export = False

outputFolder = 'stl_files_fdm_v1'

if __name__=='__main__':
    for configID in configIDs:
        # Load config
        with open("config_files/config_" + configID + ".yaml", 'r') as f:
            try:
                config = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                print(exc)

        # Load settings
        filename = config.get('filename')
        res = config.get('res') # voxels per mm
        couponStandard = config.get('couponStandard') # Start of stl file name
        centerLengthScale = config.get('centerLengthScale') # transition length scale multiplier
        blurRadius = config.get('blurRadius') # mm -- transition region width * 1/2
        materialStep = config.get('materialStep')  # material step size of final result

        blurEnable = config.get('blurEnable', False)
        ditherEnable = config.get('ditherEnable', False)
        latticeEnable = config.get('latticeEnable', False)
        gyroidEnable = config.get('gyroidEnable', False)

        if ditherEnable:
            ditherType = config.get('ditherType')
            processingRes = config.get('processingRes') # voxels per processed voxel

        if latticeEnable:
            latticeElementFile = config.get('latticeElementFile')
            minRadius = config.get('minRadius')  # 0/1 min radius that results in a printable structure
            maxRadius = config.get('maxRadius')  # 3/5 max radius that results in a viable lattice element

        if gyroidEnable:
            gyroidType = config.get('gyroidType')
            gyroidScale = config.get('gyroidScale')
            gyroidMaxDilate = config.get('gyroidMaxDilate')
            gyroidMaxErode = config.get('gyroidMaxErode')

        app1 = qg.QApplication(sys.argv)

        # Import coupon components
        print('Importing Files')
        end1 = VoxelModel.fromMeshFile('coupon_templates/' + couponStandard + '-End.stl', (0, 0, 0), resolution=res).fitWorkspace()
        center = VoxelModel.fromMeshFile('coupon_templates/' + couponStandard + '-Center-2.stl', (0, 0, 0), resolution=res).fitWorkspace()
        end2 = end1.rotate90(2, axis=Axes.Z)
        center.coords = (end1.voxels.shape[0], round((end1.voxels.shape[1] - center.voxels.shape[1]) / 2), 0)
        end2.coords = (end1.voxels.shape[0] + center.voxels.shape[0], 0, 0)

        # Trim center
        center_cross_section = VoxelModel(center.voxels[0:2, :, :], 3).fitWorkspace()
        centerLength = center.voxels.shape[0]
        centerWidth = center_cross_section.voxels.shape[1]
        centerHeight = center_cross_section.voxels.shape[2]

        centerCoordsOffset = (
        center.coords[0], center.coords[1] + round(((center.voxels.shape[1] - centerWidth) / 2)), center.coords[2])
        center = cuboid((centerLength, centerWidth, centerHeight), centerCoordsOffset)

        # Set materials
        end1 = end1.setMaterial(1)
        end2 = end2.setMaterial(1)
        center = center.setMaterial(2)

        # Combine components
        coupon = end1 | center | end2
        coupon = coupon.setMaterial(1)

        # Remove end bumps
        modelCutTool1 = cuboid((coupon.voxels.shape[0], coupon.voxels.shape[1], 12), (0, 0, coupon.voxels.shape[2] - 12), 3)
        modelCutTool2 = cuboid((1, coupon.voxels.shape[1], coupon.voxels.shape[2]), (0, 0, 0), 3)
        modelCutTool3 = cuboid((1, coupon.voxels.shape[1], coupon.voxels.shape[2]), (coupon.voxels.shape[0] - 1, 0, 0), 3)
        coupon = coupon.difference(modelCutTool1 | modelCutTool2 | modelCutTool3)
        coupon = coupon.fitWorkspace()
        coupon.coords = (0,0,0)

        # Scaled center
        newCenterLength = round(centerLength * centerLengthScale)
        centerCoordsOffset = (center.coords[0] + round((centerLength - newCenterLength) / 2), center.coords[1], center.coords[2])
        center = cuboid((newCenterLength, centerWidth, centerHeight), centerCoordsOffset)
        center = center.setMaterial(2)
        coupon = center | coupon

        coupon_input = VoxelModel.copy(coupon)

        start = time.time()

        # Generate transition regions
        transition_1 = cuboid((blurRadius * res * 2, coupon.voxels.shape[1], coupon.voxels.shape[2]), (center.coords[0] - (blurRadius * res), 0, 0), 3)
        transition_2 = cuboid((blurRadius * res * 2, coupon.voxels.shape[1], coupon.voxels.shape[2]), (center.coords[0] - (blurRadius * res) + newCenterLength, 0, 0), 3)
        transition_regions = transition_1 | transition_2
        transition_regions = transition_regions.getComponents()

        # Generate lattice elements
        latticeSize = None
        lattice_elements = None
        if latticeEnable:
            # Import Models
            lattice_model = VoxelModel.fromVoxFile("lattice_elements/" + latticeElementFile + '.vox')
            latticeSize = lattice_model.voxels.shape[0]
            print('Lattice Element Imported')

            # Generate Dilated Lattice Elements
            lattice_elements = [VoxelModel.emptyLike(lattice_model)]
            for r in range(minRadius, maxRadius + 1):
                lattice_elements.append(lattice_model.dilate(r))
            lattice_elements.append(cuboid(lattice_model.voxels.shape))
            print('Lattice Elements Generated')

        elif gyroidEnable:
            # Import Models
            s = center.voxels.shape[2] * gyroidScale

            if gyroidType == 2:
                lattice_model_1, lattice_model_2 = schwarzP((s,s,s), s)
            elif gyroidType == 3:
                lattice_model_1, lattice_model_2 = schwarzD((s,s,s), s)
            elif gyroidType == 4:
                lattice_model_1, lattice_model_2 = FRD((s,s,s), s)
            else: # gyroidType == 1
                lattice_model_1, lattice_model_2 = gyroid((s,s,s), s)

            latticeSize = s
            print('Lattice Element Imported')

            # Generate Dilated Lattice Elements
            lattice_elements = [VoxelModel.emptyLike(lattice_model_1)]
            for r in range(0, gyroidMaxErode):
                lattice_elements.append(lattice_model_1.difference(lattice_model_2.dilate(gyroidMaxErode - r)))
            for r in range(0, gyroidMaxDilate + 1):
                lattice_elements.append(lattice_model_1.dilate(r))
            lattice_elements.append(cuboid(lattice_model_1.voxels.shape))
            print('Lattice Elements Generated')

        # Generate transitions
        for c in range(transition_regions.numComponents):
            print('Component #' + str(c+1))
            transition = coupon_input & (transition_regions.isolateComponent(c+1))
            transitionCenter = transition.getCenter()
            transition = transition.fitWorkspace()
            print(transitionCenter)

            if blurEnable: # Blur materials
                print('Blurring')
                transition_scaled = transition.blur(blurRadius*res)                 # Apply blur
                transition_scaled = transition_scaled.scaleValues()                 # Cleanup values
                transition_scaled = transition_scaled.setCenter(transitionCenter)   # Center processed model on target region
                transition = transition_scaled & transition                         # Trim excess voxels

            elif ditherEnable: # Dither materials
                print('Dithering')
                x_len = int(transition.voxels.shape[0])
                y_len = int(transition.voxels.shape[1])
                z_len = int(transition.voxels.shape[2])

                transition_scaled = transition.blur(blurRadius*res*1.5)
                transition_scaled = transition_scaled.scale((1 / processingRes))    # Reduce to processing scale and dilate to compensate for rounding errors

                if ditherType == 2:
                    transition_scaled = transition_scaled.dither(blurRadius*(res/processingRes), blur=False, use_full=False, y_error=0.8, x_error=0.8)   # Apply Dither
                elif ditherType == 3:
                    transition_scaled = transition_scaled.dither(blurRadius*(res/processingRes), blur=False, use_full=False, y_error=0.8)   # Apply Dither
                else: # ditherType == 1
                    transition_scaled = transition_scaled.dither(blurRadius * (res / processingRes), blur=False)  # Apply Dither

                transition_scaled = transition_scaled.scaleValues()                                         # Cleanup values
                transition_scaled = transition_scaled.scaleToSize((x_len, y_len, z_len))                      # Increase to original scale
                transition_scaled = transition_scaled.setCenter(transitionCenter)                           # Center processed model on target region
                transition = transition_scaled & transition                                                 # Trim excess voxels

            elif latticeEnable or gyroidEnable:
                print('Lattice')

                boxX = math.ceil(transition.voxels.shape[0] / latticeSize)
                boxY = math.ceil(transition.voxels.shape[1] / latticeSize)
                boxZ = math.ceil(transition.voxels.shape[2] / latticeSize)
                print([boxX, boxY, boxZ])

                lattice_locations = transition.scaleToSize((boxX, boxY, boxZ))
                lattice_locations = lattice_locations.blur(blurRadius*(res/latticeSize))
                lattice_locations = lattice_locations.scaleValues()
                lattice_locations = lattice_locations - lattice_locations.setMaterial(2)
                lattice_locations = lattice_locations.scaleNull()

                # Convert processed model to lattice
                lattice_result = VoxelModel.emptyLike(lattice_locations)

                for x in tqdm(range(boxX), desc='Adding lattice elements'):
                    for y in range(boxY):
                        for z in range(boxZ):
                            i = lattice_locations.voxels[x, y, z]
                            density = lattice_locations.materials[i, 0] * (1 - lattice_locations.materials[i, 1])

                            if density < 1e-10:
                                r = 0
                            elif density > (1 - 1e-10):
                                r = len(lattice_elements) - 1
                            else:
                                r = round(density * (len(lattice_elements) - 3)) + 1

                            r = int(r)

                            locationOffset = round((lattice_elements[r].voxels.shape[0] - latticeSize) / 2)

                            x2 = (x * latticeSize) - locationOffset
                            y2 = (y * latticeSize) - locationOffset
                            z2 = (z * latticeSize) - locationOffset

                            lattice_elements[r].coords = (x2, y2, z2) # Do not use setCoords here

                            lattice_result = lattice_result.union(lattice_elements[r])

                lattice_result = lattice_result.setMaterial(1)
                lattice_result = lattice_result.setCenter(transitionCenter)   # Center processed model on target region
                transition_scaled = lattice_result & transition               # Trim excess voxels
                transition = transition_scaled | transition.setMaterial(2)

            transition = transition & coupon    # Trim excess voxels
            coupon = transition | coupon        # Add to result

        coupon = coupon.round(materialStep)
        coupon = coupon.removeDuplicateMaterials()
        coupon.resolution = res

        end = time.time()
        processingTime = (end - start)
        print("Processing time = %s" % processingTime)

        if display:
            # Create mesh data
            print('Meshing')
            mesh1 = Mesh.fromVoxelModel(coupon, resolution=res)

            # Create plot
            print('Plotting')
            plot1 = Plot(mesh1, grids=True, drawEdges=True, positionOffset = (35, 2, 0), viewAngle=(50, 40, 200), resolution=(720, 720), name=filename)
            plot1.show()
            app1.processEvents()
            app1.exec_()

        if save:
            try:
                os.mkdir(outputFolder)
            except OSError:
                print('Output folder already exists')
            else:
                print('Output folder successfully created')

            print('Saving')
            coupon.saveVF(outputFolder + '/output_' + filename)

        if export:
            print('Exporting')

            try:
                os.mkdir(outputFolder + '/stl_output_' + filename)
            except OSError:
                print('Output folder already exists')
            else:
                print('Output folder successfully created')

            for m in range(1, len(coupon.materials)):
                current_mesh = Mesh.fromVoxelModel(coupon.isolateMaterial(m), resolution=res)
                current_mesh.export((outputFolder + '/stl_output_' + filename +'/' + couponStandard + '_mat_' + str(m) + '_' + str(coupon.materials[m, 2]) + '.stl'))

    print('Finished')