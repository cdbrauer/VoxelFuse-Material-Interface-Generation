"""
Copyright 2018
Dan Aukes, Cole Brauer

Generate coupon for tensile testing
"""

import os
import sys
import time
import math as m

import PyQt5.QtGui as qg
from tqdm import tqdm

from voxelfuse.voxel_model import VoxelModel
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.primitives import *
from voxelfuse.voxel_model import Axes

if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    # Settings
    a = 16                  # Scale (voxels/unit)
    t = 0.001               # Thickess
    size = (50, 50, 16)     # Volume

    gyroid_element = cuboid(size)

    for x in tqdm(range(size[0]), desc='Generating Gyroid'):
        for y in range(size[1]):
            for z in range(size[2]):
                t_calc = m.sin((2 * m.pi * x)/a) * m.cos((2 * m.pi * y)/a) + m.sin((2 * m.pi * y)/a) * m.cos((2 * m.pi * z)/a) + m.sin((2 * m.pi * z)/a) * m.cos((2 * m.pi * x)/a)

                if t_calc < t:
                    gyroid_element.voxels[x, y, z] = 1
                else:
                    gyroid_element.voxels[x, y, z] = 0

    # Create Mesh
    mesh1 = Mesh.fromVoxelModel(gyroid_element)

    # Create Plot
    plot1 = Plot(mesh1)
    plot1.show()

    app1.processEvents()
    app1.exec_()