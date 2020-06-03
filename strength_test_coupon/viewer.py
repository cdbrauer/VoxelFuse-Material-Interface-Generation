"""
Copyright 2019
Dan Aukes, Cole Brauer
"""

# Import Libraries
import PyQt5.QtGui as qg
import sys
import numpy as np
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.simulation import Simulation
from voxelfuse.voxel_model import Dir
from voxelfuse.mesh import Mesh
from voxelfuse.plot import Plot

# Start Application
if __name__=='__main__':
    app1 = qg.QApplication(sys.argv)

    scaleFactor = 0.25 # Scale the model to increase/decrease resolution
    cleanup = False # Remove duplicate materials and save file
    export = False # STL file for slicing
    exportSim = True # VXA file for simulation
    display = False # Display output

    # Open File
    file = 'stl_files_v4.2_combined/output_C'
    model = VoxelModel.openVF(file)

    # Apply scale factor
    model = model.scale(scaleFactor)

    # Apply rubber material
    modelRubber = model.isolateMaterial(1)
    modelRubber = modelRubber.setMaterial(8)
    model = modelRubber | model

    # Cleanup operations
    if cleanup:
        model.materials = np.round(model.materials, 3)
        model = model.removeDuplicateMaterials()
        model.saveVF(file)

    # Create stl files
    if export:
        for m in range(1, len(model.materials)):
            mesh = Mesh.fromVoxelModel(model.isolateMaterial(m).fitWorkspace())
            mesh.export(file + '-' + str(m) + '.stl')

    # Create simulation file
    if exportSim:
        simulation = Simulation(model) # Initialize a simulation
        simulation.setCollision() # Enable self collisions with default settings
        simulation.addBoundaryConditionBox() # Add a box boundary with default settings (fixed constraint, YZ plane at X=0)
        simulation.addBoundaryConditionBox(position=(0.99, 0, 0), displacement=(30, 0, 0)) # Add a boundary condition at x = max, leave other settings at default (fixed constraint, YZ plane)
        simulation.launchSim(file + '_sim', delete_files=True)  # Launch simulation, do not save simulation file

    if display:
        mesh = Mesh.fromVoxelModel(model)

        # Create Plot
        plot1 = Plot(mesh)
        plot1.show()
        app1.processEvents()
        app1.exec_()