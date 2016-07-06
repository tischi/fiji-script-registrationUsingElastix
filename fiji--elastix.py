#
# use elastix from Fiji
#
# author: tischitischer@gmail.com
#
# input: 
# 
# computation:
#
# output:

import os
from ij import IJ
from subprocess import Popen, PIPE

#
# FUNCTIONS
#

def cmd(args):
  p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
  output, err = p.communicate()
  return(output)

def convert_to_mhd(input_file, mhd_file_name, output_folder):
  #print("opening "+input_file) 
  imp = IJ.openImage(input_file)
  output_file = os.path.join(output_folder, mhd_file_name)
  IJ.run(imp, "MHD/MHA ...", "save="+output_file);
  #print("saving "+output_file)
  return output_file

# - the conversion to unsigned int is ugly!
# - weird behavior of IJ.openImage: it shows the image but does not put anything into the imp
#   - report to Wayne
def convert_result(original_filename, output_folder, save_as_max):
  IJ.openImage(os.path.join(output_folder,"result.0.mhd"))
  imp = IJ.getImage()
  IJ.run(imp, "32-bit", "");
  IJ.setMinAndMax(0, 65535);
  IJ.run(imp, "16-bit", "");
  output_file = os.path.join(output_folder,original_filename+"--transformed.tif")
  IJ.saveAs(imp, "Tiff", output_file)
  # optional to save maximum projections
  if(save_as_max):
    if(imp.getStackSize()>1):
      IJ.run(imp, "Z Project...", "projection=[Max Intensity]")
      IJ.saveAs(IJ.getImage(), "Tiff", output_file+"--z-max.tif")
  return output_file

#
# GET PARAMETERS
#

# - input folder
input_folder = "C:\\Users\\tischer\\Desktop\\3D-files"

# file list
# file_list = ['t09.tif', 't10.tif']

file_list = []
for file_name in os.listdir(input_folder):
  if file_name.endswith(".tif"):
    file_list.append(file_name)

# output folder
output_folder = input_folder+"--fiji"
if not os.path.isdir(output_folder):
  os.mkdir(output_folder)

# registration method
parameter_file = "C:\\Users\\tischer\\Desktop\\parameters_Affine.txt"

# reference image
i_ref = int(len(file_list)/2)

# path to elastix
elastix = 'C:/Program Files/elastix_v4.8/elastix' 

# options
save_result_also_as_max_projection = True

#
# COMPUTE
#

# convert fixed (reference) file to .mhd 
fixed_file = convert_to_mhd(os.path.join(input_folder, file_list[i_ref]), "fixed.mhd", output_folder)

for f in file_list:
  print("matching: "+str(f)+" to "+file_list[i_ref])
  moving_file = convert_to_mhd(os.path.join(input_folder, f), "moving.mhd", output_folder)
  
  # run registration
  output = cmd([elastix, '-f', fixed_file,'-m', moving_file, '-out', output_folder, '-p', parameter_file])

  # convert transformed moving file to .tif and give it the name of the input file
  convert_result(f, output_folder, save_result_also_as_max_projection)
  
  # clean up
  IJ.run("Close All", "");

print("Done!")
# optional:
# - save x,y,z maximum projections of the raw and registered data on the fly and show them in the end as movies

