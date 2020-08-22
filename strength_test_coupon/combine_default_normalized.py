"""
Copyright 2019
Dan Aukes, Cole Brauer
"""

# Import Libraries
import PyQt5.QtGui as qg
import sys
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.primitives import *

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    res = 5 # voxels per mm
    clearance = 50
    defaultModelName = 'stl_files_v5_combined/output_B1_default'
    normalizedModelName = 'stl_files_v5_combined/output_B2_normalized'

    # Open Files
    outputFolder = 'stl_files_v5_combined/'
    dModel = VoxelModel.openVF(defaultModelName)
    nModel = VoxelModel.openVF(normalizedModelName)

    # Markers
    size = dModel.voxels.shape
    markerSize = int((size[2] * 0.7)/2) * 2
    marker1 = cylinder(int(markerSize/2), size[2], (0, 0, 0), resolution=res)
    marker2 = marker1 | cylinder(int(markerSize/2), size[2], (0, markerSize*2, 0), resolution=res)
    marker3 = marker2 | cylinder(int(markerSize/2), size[2], (0, markerSize*4, 0), resolution=res)

    # Init result model
    resultModel = VoxelModel.emptyLike(dModel)

    # Add vertical coupons
    resultModel = resultModel | dModel.setCoords((0, 0, 0))
    resultModel = resultModel | nModel.setCoords((350, 100 + clearance, 0))
    resultModel = resultModel | dModel.setCoords((750, 200 + 2 * clearance, 0))
    resultModel = resultModel | nModel.setCoords((0, 1300 - 2 * clearance, 0))
    resultModel = resultModel | dModel.setCoords((350, 1400 - clearance, 0))
    resultModel = resultModel | nModel.setCoords((750, 1500, 0))

    resultModel = resultModel.difference(marker1.setCoords((0 + markerSize, 0 + markerSize, 0)))
    resultModel = resultModel.difference(marker2.setCoords((350 + markerSize, 100 + clearance + markerSize, 0)))
    resultModel = resultModel.difference(marker3.setCoords((750 + markerSize, 200 + 2 * clearance + markerSize, 0)))
    resultModel = resultModel.difference(marker1.setCoords((0 + markerSize, 1300 - 2 * clearance + markerSize, 0)))
    resultModel = resultModel.difference(marker2.setCoords((350 + markerSize, 1400 - clearance + markerSize, 0)))
    resultModel = resultModel.difference(marker3.setCoords((750 + markerSize, 1500 + markerSize, 0)))

    # Rotate models
    dModel = dModel.rotate90()
    nModel = nModel.rotate90()

    # Add horizontal coupons
    resultModel = resultModel | dModel.setCoords((0, 100 + clearance, 0))
    resultModel = resultModel | nModel.setCoords((100 + clearance, 100 + clearance, 0))
    resultModel = resultModel | dModel.setCoords((550, 300, 0))
    resultModel = resultModel | nModel.setCoords((950, 450, 0))
    resultModel = resultModel | dModel.setCoords((1300, 650 - clearance, 0))
    resultModel = resultModel | nModel.setCoords((1400 + clearance, 650 - clearance, 0))

    resultModel = resultModel.difference(marker1.setCoords((0 + markerSize, 100 + clearance + markerSize, 0)))
    resultModel = resultModel.difference(marker1.setCoords((100 + clearance + markerSize, 100 + clearance + markerSize, 0)))
    resultModel = resultModel.difference(marker2.setCoords((550 + markerSize, 300 + markerSize, 0)))
    resultModel = resultModel.difference(marker2.setCoords((950 + markerSize, 450 + markerSize, 0)))
    resultModel = resultModel.difference(marker3.setCoords((1300 + markerSize, 650 - clearance + markerSize, 0)))
    resultModel = resultModel.difference(marker3.setCoords((1400 + clearance + markerSize, 650 - clearance + markerSize, 0)))

    # Clean up
    resultModel = resultModel.removeDuplicateMaterials()

    # Create stl files
    for m in range(1, len(resultModel.materials)):
        mesh = Mesh.fromVoxelModel(resultModel.isolateMaterial(len(resultModel.materials) - m), resolution=res)
        mesh.export((outputFolder + str(len(resultModel.materials) - m) + '_FLX95585-DM_00A.stl'))