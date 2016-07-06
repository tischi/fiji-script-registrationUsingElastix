#
# use elastix from Fiji
#
# author: tischitischer@gmail.com
#
# input format: 
#  -
#

import os
from ij import IJ
import subprocess
from subprocess import Popen, PIPE

#
# FUNCTIONS
#

def cmd(args):
  p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
  output, err = p.communicate()
  return(output)

def convert_to_mhd(input_file, output_folder):
  imp = IJ.openImage(input_file);
  output_file = os.path.join(output_folder,input_file+".mhd")
  IJ.run(imp, "MHD/MHA ...", "save="+output_file);
  return output_file

def convert_result(original_filename, output_folder):
  imp = IJ.openImage(os.path.join(output_folder,"result.0.mhd"));
  output_file = os.path.join(output_folder,original_filename+"--transformed.tif")
  IJ.saveAs(imp, "Tiff", output_file);
  return output_file

#
# GET PARAMETERS
#
# - input folder
input_folder = "C:\\Users\\tischer\\Desktop"
# get file list
file_list = ['t10.tif', 't09.tif']
# - output folder
output_folder = "C:\\Users\\tischer\\Desktop"
# - channel for computing registration
# - registration strategy
#   - against which file (fixed file, running file)
#   - which method (rigid, euler, affine)
parameter_file = "Z:/0000--Tischi--Practical_ImageJ/data-all/registration/elastix_example_v4.8/exampleinput/parameters_Rigid.txt"
# path to elastix
elastix = 'C:/Program Files/elastix_v4.8/elastix' 

#
# COMPUTE
#
# loop through files

# convert fixed and moving file to .mhd (use output folder as temp folder for the mhd files)
fixed_file = convert_to_mhd(os.path.join(input_folder,file_list[0]), output_folder)
moving_file = convert_to_mhd(os.path.join(input_folder,file_list[1]), output_folder)

# run registration
output = cmd([elastix, '-f', fixed_file,'-m', moving_file, '-out', output_folder, '-p', parameter_file])
print(output)

# convert transformed moving file to .tif
convert_result(file_list[1], output_folder)


# optional:
# - save x,y,z maximum projections of the raw and registered data on the fly and show them in the end as movies

