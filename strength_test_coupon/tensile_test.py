"""
Copyright 2019
Dan Aukes, Cole Brauer
"""

# Import Libraries
import numpy as np
from voxelfuse.voxel_model import VoxelModel
from voxelfuse.simulation import Simulation, StopCondition
from voxelfuse.primitives import cuboid

# Start Application
if __name__=='__main__':
    # Settings
    scaleFactor = 0.25 # Scale the model to increase/decrease resolution
    displacementMax = 60
    displacementStep = 5

    # Open File
    file = 'stl_files_v4.2_combined/output_C'
    model = VoxelModel.openVF(file)

    # Apply scale factor
    model = model.scale(scaleFactor)

    # Apply rubber material
    modelRubber = model.isolateMaterial(1)
    modelRubber = modelRubber.setMaterial(5)
    model = modelRubber | model

    # Remove end bumps
    modelCutTool = cuboid((model.voxels.shape[0], model.voxels.shape[1], round(12*scaleFactor)), (0, 0, model.voxels.shape[2] - round(12*scaleFactor)))
    model = model.difference(modelCutTool)
    model = model.fitWorkspace()

    # Initialize a simulation
    simulation = Simulation(model)

    # Simulation settings
    simulation.setEquilibriumMode()
    simulation.setStopCondition(StopCondition.MOTION_FLOOR, 0.0001)
    simulation.setDamping(environment=0)
    simulation.addSensor((round(model.voxels.shape[0] / 2), round(model.voxels.shape[1] / 2), round(model.voxels.shape[2] / 2)))

    # Create results file
    f = open(file + '_tensile_test.csv', 'w+')
    print('Saving file: ' + f.name)
    f.write('Displacement,Min Safety Factor,Center Stress,Center Strain,Center Safety Factor\n')
    f.close()

    for d in range(displacementStep, displacementMax, displacementStep):
        # Set boundary conditions
        simulation.clearBoundaryConditions()
        simulation.addBoundaryConditionBox(position=(0, 0, 0), size=(0.01, 1.0, 1.0)) # Add a fixed boundary condition at X = min
        simulation.addBoundaryConditionBox(position=(0, 0, 0), size=(1.0, 1.0, 1.0), fixed_dof=0b000100) # Add a fixed boundary condition in Z
        simulation.addBoundaryConditionBox(position=(0.99, 0, 0), size=(0.01, 1.0, 1.0), displacement=(d, 0, 0)) # Add a boundary condition at X = max, apply displacement for tensile testing

        # Launch simulation, do not save simulation file
        simulation.runSim(file + '_sim', 9)

        # Save results
        f = open(file + '_tensile_test.csv', 'a+')
        f.write(str(d) + ',')
        f.write(str(np.min(simulation.valueMap[np.nonzero(simulation.valueMap)])) + ',')
        f.write(str(simulation.results[0]['BondStress']) + ',')
        f.write(str(simulation.results[0]['Strain']) + ',')
        f.write(str(simulation.results[0]['SafetyFactor']) + '\n')
        f.close()

    print('Done')