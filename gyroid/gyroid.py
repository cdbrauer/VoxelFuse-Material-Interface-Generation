"""
Copyright 2018
Dan Aukes, Cole Brauer

Generate gyroid model
"""

import sys
import PyQt5.QtGui as qg
from tqdm import tqdm

from voxelfuse.voxel_model import VoxelModel
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot
from voxelfuse.periodic import *

if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    # Settings
    a = 50                  # Scale (voxels/unit)
    size = (50, 50, 50)     # Volume

    #model = gyroid(size, a),
    #model = schwarzP(size, a)
    #model = schwarzD(size, a)
    model1, model2 = FRD(size, a)
    model = model1 | model2.setCoords((60,0,0))

    # Create Mesh
    mesh1 = Mesh.fromVoxelModel(model)

    # Create Plot
    plot1 = Plot(mesh1)
    plot1.show()

    app1.processEvents()
    app1.exec_()