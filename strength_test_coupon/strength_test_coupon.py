"""
Copyright 2018
Dan Aukes, Cole Brauer

Generate coupon for tensile testing
"""

import sys
import time

import PyQt5.QtGui as qg
from tqdm import tqdm

from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.primitives import *
from voxelfuse.voxel_model import Axes

from dithering.dither import dither
from dithering.thin import thin

if __name__=='__main__':
    # Settings
    stl = True
    res = 2 # voxels per mm
    coupon_standard = 'D638' # Start of stl file name

    processing_res = 3 # voxels per processed voxel
    blurRadius = 6

    blurEnable = False
    ditherEnable = True
    thinEnable = False
    latticeEnable = False

    lattice_element_file = 'lattice_element_3_15x15'
    min_radius = 0  # min radius that results in a printable structure
    max_radius = 5  # max radius that results in a viable lattice element

    mold = False
    moldWallThickness = 2
    moldGap = 1

    fixture = False
    fixtureWallThickness = 5
    fixtureGap = 1

    save = False
    export = False

    app1 = qg.QApplication(sys.argv)

    # Import coupon components
    print('Importing Files')
    if stl:
        end1 = VoxelModel.fromMeshFile("coupon_templates/" + coupon_standard + '-End.stl', (0, 0, 0), resolution=res).fitWorkspace()
        center = VoxelModel.fromMeshFile("coupon_templates/" + coupon_standard + '-Center.stl', (0, 0, 0), resolution=res).fitWorkspace()
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
        end1 = VoxelModel.fromVoxFile('coupon_templates/coupon_end1.vox', (0, 0, 0)) # Should use materials 1 and 2 (red and green)
        center = VoxelModel.fromVoxFile('coupon_templates/coupon_center.vox', (113, 8, 0))
        end2 = VoxelModel.fromVoxFile('coupon_templates/coupon_end2.vox', (197, 0, 0))
        coupon = end1 | center | end2

    start = time.time()

    if blurEnable: # Blur materials
        print('Blurring')
        couponS = coupon.scale((1 / processing_res), interpolate=True).dilate()
        couponS = couponS.blur(blurRadius)
        couponS = couponS.scaleValues()
        coupon = couponS.scale(processing_res).intersection(coupon)

    elif ditherEnable: # Dither materials
        print('Dithering')
        couponS = coupon.scale((1 / processing_res), interpolate=True).dilate()
        couponS = dither(couponS, blurRadius)
        couponS = couponS.scaleValues()
        coupon = couponS.scale(processing_res).intersection(coupon)

    elif latticeEnable:
        print('Lattice')

        # Import Models
        latticeModel = VoxelModel.fromVoxFile("lattice_elements/" + lattice_element_file + '.vox')
        lattice_size = latticeModel.voxels.shape[0]
        print('Lattice Element Imported')

        # Generate Dilated Lattice Elements
        latticeElements = [VoxelModel.emptyLike(latticeModel)]
        for r in range(min_radius, max_radius+1):
            latticeElements.append(latticeModel.dilateBounded(r))
        latticeElements.append(cuboid(latticeModel.voxels.shape))
        print('Lattice Elements Generated')

        # Process Models
        latticeLocations = coupon.scale((1/lattice_size), interpolate=True).dilate()
        latticeLocations = latticeLocations.blur(blurRadius * (processing_res / lattice_size))
        latticeLocations = latticeLocations.scaleValues()
        latticeLocations = latticeLocations - latticeLocations.setMaterial(2)
        latticeLocations = latticeLocations.scaleNull()
        latticeLocations.coords = (0,0,0)

        box_x = latticeLocations.voxels.shape[0]
        box_y = latticeLocations.voxels.shape[1]
        box_z = latticeLocations.voxels.shape[2]

        print('Model Processed')

        # Convert processed model to lattice
        latticeResult = VoxelModel.emptyLike(latticeLocations)

        for x in tqdm(range(box_x), desc='Adding lattice elements'):
            for y in range(box_y):
                for z in range(box_z):
                    i = latticeLocations.voxels[x, y, z]
                    density =  latticeLocations.materials[i, 0] * (1 - latticeLocations.materials[i, 1])
                    r = min(int(density * len(latticeElements)), len(latticeElements) - 1)

                    x_new = x * lattice_size
                    y_new = y * lattice_size
                    z_new = z * lattice_size

                    latticeElements[r].coords = (x_new, y_new, z_new)

                    latticeResult = latticeResult.union(latticeElements[r])

        latticeResult = latticeResult.setMaterial(1)
        latticeResult.coords = (-lattice_size, -lattice_size, -lattice_size)
        latticeResult = latticeResult.intersection(coupon)
        print('Lattice Structure Created')

        # Generate Resin Component
        resinModel = cuboid(coupon.voxels.shape, material=2)
        resinModel = resinModel.intersection(coupon)
        resinModel = resinModel.difference(latticeResult)
        print('Resin Model Created')

        coupon = latticeResult.union(resinModel)

    if ditherEnable and thinEnable:
        coupon_ends = coupon.isolateMaterial(1)
        coupon_center = coupon.isolateMaterial(2)

        coupon_ends = coupon_ends.closing(round((processing_res/2)-1), Axes.XY)
        coupon_ends = thin(coupon_ends, int(processing_res/2)+1)
        coupon_ends = coupon_ends.dilate(1)
        coupon_ends = coupon_ends.dilate(processing_res, plane=Axes.Z)

        coupon_center = coupon_center.dilate(processing_res)
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
    plot1 = Plot(mesh1, drawEdges=False, positionOffset = (70, 5, 0), viewAngle=(50, 40, 200), resolution=(720, 720), name=coupon_standard)
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