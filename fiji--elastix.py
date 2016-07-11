#
# use elastix from Fiji
#
# Author information:
# 
# tischitischer@gmail.com
#
# Input: 
# 
# Computation:
#
# Output:
#
#

# Strategy:
#
# 20 <- 21 => 21t    
# 21t <- 22  (using last transformation as starting)             
#
#

#
# Todo:
# - use masks
# - use last trafo as input for next: -t0 TransformParameters.0.txt
# - when it is 8-bit input save as 8-bit input (check the unsigned issue)
# - option to find trafo in downsampled and apply to full-size
# - tmp storage on VM that is automatically deleted upon log-off?


import os, time, shutil, sys
from ij import IJ
from subprocess import Popen, PIPE

#
# FUNCTIONS
#

def cmd(args):
  p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
  output, err = p.communicate()
  return(output)
     
def convert_for_elastix(input_file, mhd_file_name, output_folder):
  print("    reading tif")
  start_time = time.time()
  imp = IJ.openImage(input_file)
  print("      time spent: "+str(round(time.time()-start_time,3)))
  output_file = os.path.join(output_folder, mhd_file_name)
  print("    writing mhd")
  start_time = time.time()
  IJ.run(imp, "MHD/MHA ...", "save="+output_file);
  print("      time spent: "+str(round(time.time()-start_time,3)))
  return output_file

# - the conversion to unsigned int is ugly!
# - weird behavior of IJ.openImage: it shows the image but does not put anything into the imp
#   - report to Wayne
def convert_from_elastix(original_filename, output_folder, save_as_max):
  print("    reading mha")
  start_time = time.time()
  IJ.openImage(os.path.join(output_folder,"result.0.mha"))
  print("      time spent: "+str(round(time.time()-start_time,3)))
  imp = IJ.getImage()
  IJ.run(imp, "32-bit", "");
  IJ.setMinAndMax(0, 65535);
  IJ.run(imp, "16-bit", "");
  output_file = os.path.join(output_folder,original_filename+"--transformed.tif")
  print("    writing tif")
  start_time = time.time()
  IJ.saveAs(imp, "Tiff", output_file)
  print("      time spent: "+str(round(time.time()-start_time,3)))
  # optional to save maximum projections
  if(save_as_max):
    if(imp.getStackSize()>1):
      print("    make and save z-max")
      start_time = time.time()
      IJ.run(imp, "Z Project...", "projection=[Max Intensity]")
      IJ.saveAs(IJ.getImage(), "Tiff", output_file+"--z-max.tif")
      print("      time spent: "+str(round(time.time()-start_time,3)))
  return output_file

#
# GET PARAMETERS
#

# - input folder
input_folder = "X:\\Henning\\Tischi_Reg\\MIP"
#input_folder = "C:\\Users\\tischer\\Desktop\\test"

# registration method
parameter_file = "C:\\Users\\tischer\\Desktop\\parameters_Affine.txt"

# registration strategy
trafo = "running"
#trafo = "fixed"


# path to elastix
elastix = 'C:/Program Files/elastix_v4.8/elastix' 

# options
save_as_max = True

# file list
# file_list = ['t09.tif', 't10.tif']

file_list = []
for file_name in os.listdir(input_folder):
  if file_name.endswith(".tif"):
    file_list.append(file_name)

# reference image
i_ref = int(round(len(file_list)/2))

# output folder
output_folder = input_folder+"--fiji"
if not os.path.isdir(output_folder):
  os.mkdir(output_folder)

#print(file_list)


#
# COMPUTE
#


i_ref = 1

if(trafo=="running"):
  
  print("converting reference file: " + file_list[i_ref])
  convert_for_elastix(os.path.join(input_folder, file_list[i_ref]), "previous.mha", output_folder)
  previous_result_file = os.path.join(output_folder, "previous.mha")
    
  for k, i in enumerate(range(i_ref+3,i_ref+10,3)):
    print("matching: "+file_list[i])
    
    print("  converting .tif to .mha")
    next_file = convert_for_elastix(os.path.join(input_folder, file_list[i]), "moving.mha", output_folder)
    
    # run registration
    print("  running elastix")
    start_time = time.time()
    if k==0:
      output = cmd([elastix, '-f', previous_result_file, '-m', next_file, '-out', output_folder, '-p', parameter_file])
    else:
      print("    using previous transformation for initialisation")
      os.remove(os.path.join(output_folder, "previous.mha"))
      time.sleep(1)
      os.rename(os.path.join(output_folder, "result.0.mha"), os.path.join(output_folder, "previous.mha"))
      sys.exit(1)
      previous_transformation = os.path.join(output_folder, "TransformParameters.0.txt")
      output = cmd([elastix, '-f', previous_result_file, '-m', next_file, '-out', output_folder, '-p', parameter_file, '-t0', previous_transformation])
    
    print("      time spent: "+str(round(time.time()-start_time,3)))
    #print(output)
    
    # convert transformed moving file to .tif and give it the name of the input file
    #print("  converting .mha to .tif")
    
    # replace this by a simple file copy!!
    #convert_from_elastix(file_list[i], output_folder, save_as_max)

    
    # clean up
    IJ.run("Close All", "");


if(trafo=="fixed"):
  
  print("converting reference file")
  fixed_file = convert_to_mhd(os.path.join(input_folder, file_list[i_ref]), "fixed.mhd", output_folder)
  
  for f in file_list:
    print("matching: "+str(f)+" to "+file_list[i_ref])
    print("  converting .tif to .mhd")
    moving_file = convert_to_mhd(os.path.join(input_folder, f), "moving.mhd", output_folder)
    
    # run registration
    print("  running elastix")
    start_time = time.time()
    output = cmd([elastix, '-f', fixed_file,'-m', moving_file, '-out', output_folder, '-p', parameter_file])
    print("      time spent: "+str(round(time.time()-start_time,3)))
    #print(output)
    # convert transformed moving file to .tif and give it the name of the input file
    print("  converting .mhd to .tif")
    convert_result(f, output_folder, save_as_max)
    ddd
    # clean up
    IJ.run("Close All", "");

print("Done!")

