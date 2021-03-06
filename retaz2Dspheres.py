import espressomd
import object_in_fluid as oif

from espressomd import lb
from espressomd import lbboundaries
from espressomd import shapes
from espressomd import interactions

import numpy as np
import os, glob, sys, shutil
import random
import math
import time, datetime

# linear cluster
# IJ, feb2021
# cells connected via Morse non-bonded interaction
# bonds can be visualised


#ahoj tt je zmena

#pridavam do new br, testujem dalsiu zmenu

def distance(a,b):
    return np.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2)

def calc_mean_velocity(x):
    # takes cross-section at position x
    # and calculates mean fluid velocity over this cross-section
    ymin = 0
    ymax = int(boxY)
    zmin = 0
    zmax = int(boxZ)
    sum = 0
    counter = 0

    for i in range(ymin, ymax):
        for j in range(zmin, zmax):
            vel = lbf[x,i,j].velocity
            if lbf[x,i,j].boundary == 0:
                sum += vel
                counter += 1
    return sum/counter

def output_lines(positions, cell1_id, cell2_id, time):
    dist = boxX

    pairs = []
    for i in cells[cell1_id].mesh.points:
        for j in cells[cell2_id].mesh.points:
            ipos = positions[cell1_id][i.part_id]
            jpos = positions[cell2_id][j.part_id]
            d = distance(ipos, jpos)
            dist = min(dist, d)
            if d <= cutoff:
                line = [ipos[0], ipos[1], ipos[2], jpos[0], jpos[1], jpos[2]]
                pairs.append(line)
    cell_distances[cell1_id][cell2_id] = dist
    oif.output_vtk_lines(lines=pairs, out_file=vtk_directory + "/lines" + str(cell1_id) + str(cell2_id) + "_" + str(time) + ".vtk")

if len(sys.argv) != 9:
    print ("4 arguments are expected:")
    print ("r_cell: radius of cells")
    print("angle: angle of cells")
    print("n_cells: number of cells")
    print ("sim_id: id of the simulation")
    print (" ")

# list of expected arguments
r_cell = "ND"
angle = "ND"
n_cell = "ND"
sim_id = "ND"
vtk = "y"

# read arguments
i = 0
for i, arg in enumerate(sys.argv):
    if i%2 == 1:
        print (str(arg) + " \t" + sys.argv[i + 1])
    if arg == "r_cell":
        r_cell = float(sys.argv[i + 1])
    if arg == "angle":
        angle = float(sys.argv[i + 1])
    if arg == "n_cell":
        n_cell = int(sys.argv[i + 1])
    if arg == "sim_id":
        sim_id = sys.argv[i + 1]

# check that we have everything
if r_cell == "ND" or angle == "ND" or n_cell == "ND" or sim_id == "ND":
    print("something wrong when reading arguments, quitting.")

# create folder structure
directory = "output/sim"+str(sim_id)
#os.makedirs(directory + "/distances")
if vtk == "y" or vtk == "yes":
    vtk_directory = directory + "/vtk"
    if os.path.exists(vtk_directory):
        shutil.rmtree(vtk_directory)
    os.makedirs(vtk_directory)

# channel constants
boxX = 100.0
boxY = 80.0
boxZ = 40.0

# system constants
system = espressomd.System(box_l=[boxX, boxY, boxZ])
system.cell_system.skin = 0.2
system.time_step = 0.1

# save script and arguments
shutil.copyfile(str(sys.argv[0]), directory + "/" + str(sys.argv[0]))
out_file = open(directory + "/parameters"+str(sim_id)+".txt", "a")
for arg in sys.argv:
    out_file.write(str(arg) + " ")
out_file.write("\n")
out_file.write("boxX "+str(boxX)+"\n")
out_file.write("boxY "+str(boxY)+"\n")
out_file.write("boxZ "+str(boxZ)+"\n")
out_file.close()

# create boundaries
boundaries = []
# bottom of the channel
tmp_shape = shapes.Rhomboid(corner=[0.0, 0.0, 0.0], a=[boxX, 0.0, 0.0], b=[0.0, boxY, 0.0], c=[0.0, 0.0, 1.0],
              direction=1)
boundaries.append(tmp_shape)
oif.output_vtk_rhomboid(rhom_shape=tmp_shape, out_file=vtk_directory+"/wallBottom.vtk")

# top of the channel
tmp_shape = shapes.Rhomboid(corner=[0.0, 0.0, boxZ-1], a=[boxX, 0.0, 0.0], b=[0.0, boxY, 0.0], c=[0.0, 0.0, 1.0],
              direction=1)
boundaries.append(tmp_shape)
oif.output_vtk_rhomboid(rhom_shape=tmp_shape, out_file=vtk_directory+"/wallTop.vtk")

# front wall of the channel
tmp_shape = shapes.Rhomboid(corner=[0.0, 0.0, 0.0], a=[boxX, 0.0, 0.0], b=[0.0, 1.0, 0.0], c=[0.0, 0.0, boxZ],
              direction=1)
boundaries.append(tmp_shape)
oif.output_vtk_rhomboid(rhom_shape=tmp_shape, out_file=vtk_directory+"/wallFront.vtk")

# back wall of the channel
tmp_shape = shapes.Rhomboid(corner=[0.0, boxY-1.0, 0.0], a=[boxX, 0.0, 0.0], b=[0.0, 1.0, 0.0], c=[0.0, 0.0, boxZ],
              direction=1)
boundaries.append(tmp_shape)
oif.output_vtk_rhomboid(rhom_shape=tmp_shape, out_file=vtk_directory+"/wallBack.vtk")

boundary_particle_type = 10
boundary_particle_type_constant=100

for boundary in boundaries:
  system.lbboundaries.add(lbboundaries.LBBoundary(shape=boundary))
  system.constraints.add(shape=boundary, particle_type=boundary_particle_type_constant+boundary_particle_type, penetrable=False)


# cell constants
cell_radius = r_cell
uhol = 0
cell_positions = []
polohax = cell_radius + 0.5
polohay = boxY/2.0
polohaz = boxZ/2.0

cell_positions.append([polohax,
                       polohay,
                       polohaz])
for i in range(n_cell-1):
    beta = random.randrange(-angle, angle);
    uhol = uhol + beta
    polohax = polohax + math.cos(math.radians(uhol))*(2*cell_radius + 0.5)
    polohay =  polohay + math.sin(math.radians(uhol))*(2*cell_radius + 0.5)
    cell_positions.append([polohax,
                       polohay,
                       polohaz])


typeCell_soft = oif.OifCellType(nodes_file="input/sphere642nodes.dat",
                           triangles_file="input/sphere642triangles.dat",
                           check_orientation=False,
                           system=system,
                           ks=0.02,
                           kb=0.1,
                           kal=0.05,
                           kag=0.7,
                           kv=0.9,
                           normal=True,
                           resize=[cell_radius, cell_radius, cell_radius])

# create cells
cells = []
for i in range(n_cell):
    cells.append(oif.OifCell(cell_type=typeCell_soft,
                            particle_type=i,
                            origin=cell_positions[i],
                            particle_mass=0.5))

# cell-wall interactions
for i in range(len(cells)):
    system.non_bonded_inter[i,boundary_particle_type].soft_sphere.set_params(a=0.002,
                                                                         n=1.5,
                                                                         cutoff=0.8,
                                                                         offset=0.0)

# cell-cell interactions
# attractive Morse, repulsive soft_sphere (membrane collision can be used here instead of soft-sphere):
for i in range(len(cells)):
    for j in range(i+1, len(cells)):
        system.non_bonded_inter[i,j].morse.set_params(eps=0.4,
                                                    alpha=0.2,
                                                    cutoff=0.6,
                                                    rmin=1.0)
        system.non_bonded_inter[i,j].soft_sphere.set_params(a=0.002,
                                                      n=1.5,
                                                      cutoff=0.4,
                                                      offset=0.0)

# fluid
fluid_viscosity = 1.5
fluid_density = 1.0
lbf = espressomd.lb.LBFluid(agrid=1,
                            dens=fluid_density,
                            visc=fluid_viscosity,
                            tau=system.time_step,
                            ext_force_density=[0.0003, 0.0, 0.0])
gammaFriction = typeCell_soft.suggest_LBgamma(visc = fluid_viscosity, dens = fluid_density)
system.actors.add(lbf)
system.thermostat.set_lb(LB_fluid=lbf,
                         gamma=gammaFriction)

#for boundary in boundaries:
#    system.lbboundaries.add(lbboundaries.LBBoundary(shape=boundary))
#    system.constraints.add(shape=boundary,
#                           particle_type=boundary_particle_type,
#                           penetrable=False)

#cell_distances = [[0]*len(cells)]*len(cells)

positions = []
for id, cell in enumerate(cells):
    #positions.append({})
    cell.output_vtk_pos_folded(file_name=vtk_directory + "/cell" + str(id) + "_0.vtk")
    #for i in cell.mesh.points:
    #    positions[id][i.part_id] = i.get_pos()

#for i in range(len(cells)):
#    for j in range(i+1, len(cells)):
#        output_lines(positions,i,j,0)

print ("fluid and cells initialised")

# main integration loop
#maxCycle = 300
maxCycle = 5
#steps_in_one_cycle = 5000
steps_in_one_cycle = 300
print ("time: 0 ms")
for cycle in range(1, maxCycle):
    loopStartTime = time.time()
    system.integrator.run(steps=steps_in_one_cycle)
    current_time = cycle * system.time_step * steps_in_one_cycle / 1000  # time in ms

    # outputting vtk files for visualisation

    for id, cell in enumerate(cells):
        cell.output_vtk_pos_folded(file_name=vtk_directory + "/cell" + str(id) + "_" + str(cycle) +".vtk")
        #for i in cell.mesh.points:
        #    positions[id][i.part_id] = i.get_pos()

    #out_distances = ""
    #for i in range(len(cells)):
    #    for j in range(i + 1, len(cells)):
    #        output_lines(positions, i, j, cycle)
    #        out_distances += str(cell_distances[i][j]) + " "

    #out_file = open(directory + "/distances" + str(sim_id) + ".txt", "a")
    #out_file.write(out_distances)
    #out_file.close()

    f_vel = calc_mean_velocity(int(boxX / 2.0))
    print("fluid x-velocity (mean @ mid capillary): " + str(f_vel[0]))

    velocities = []
    positions = []
    out_data = str(f_vel[0]) + " "
    for id, cell in enumerate(cells):
        velocities.append(cell.get_velocity())
        positions.append(cell.get_origin())
        print("cell" + str(id) + " velocity: " + str(velocities[id]))
        out_data += str(velocities[id][0]) + " " + str(velocities[id][1]) + " " + str(velocities[id][2]) + " "
        out_data += str(positions[id][0]) + " " + str(positions[id][1]) + " " + str(positions[id][2]) + " "

    out_file = open(directory + "/data_" + str(sim_id) + ".txt", "a")
    out_file.write(str(current_time) + " " + out_data + "\n")
    out_file.close()

    print("currTime: " + str(current_time))
    loopEndTime = time.time()
    print("\n...........\n...whole loop took " + str(loopEndTime - loopStartTime) + " s\n...........\n")

print ("Simulation completed.")
exit()