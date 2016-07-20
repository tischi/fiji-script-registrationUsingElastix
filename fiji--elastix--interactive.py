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
# General Todo:
# - write load and save functions giving: MB, time, MB/time
#
# Elastix Todo:
# - use masks
# - use last trafo as input for next: -t0 TransformParameters.0.txt
# - when it is 8-bit input save as 8-bit input (check the unsigned issue)
# - option to find trafo in downsampled and apply to full-size
# - tmp storage on VM that is automatically deleted upon log-off?
# - if key contains file open file selection box
# - non-zero background is an issue I think; check manual; maybe not....
#
# Structure for batch analysis:
#  
# - main 
#  - parameters = get_analysis_parameters()
#  - folder = get_folder()
#  - table = init_results_table()
#  - get_data_info(folder, table) 
#  - batch_analyze(parameters, table) 
#    - for row in table 
#       - analyze(row, table, parameters)
#         - imp = load_imp(table, row)
#         - write results to table(row)
#         - write segmentation overlay images (use from table(row))



from ij.io import OpenDialog
from ij.io import Opener
from fiji.util.gui import GenericDialogPlus
from ij.plugin import ZProjector, RGBStackMerge, SubstackMaker, Concatenator
from ij import IJ, ImagePlus, ImageStack, WindowManager
from ij.plugin import Duplicator
from ij.process import StackStatistics
from ij.plugin import ImageCalculator
from ij.measure import ResultsTable
from ij.plugin.frame import RoiManager
import os, os.path, re, sys
from subprocess import Popen, PIPE
from ij.process import ImageConverter
import os, time, shutil, sys, math
from ij.macro import MacroRunner

from loci.plugins import BF
from loci.common import Region
from loci.plugins.in import ImporterOptions

from automic.table import TableModel			# this class stores the data for the table
from automic.table import ManualControlFrame 	# this class visualises TableModel via GUI
from java.io import File
from automic.utils.roi import ROIManipulator2D as ROIManipulator

#
#  Functions
#  

def close_all_image_windows():
  # forcefully closes all open images windows
  ids = WindowManager.getIDList();
  if (ids==None):
    return
  for i in ids:
     imp = WindowManager.getImage(i)
     if (imp!=None):
       win = imp.getWindow()
       if (win!=None):
         imp.changes = False # avoids the "save changes" dialog
         win.close()
         
def mean(x):
  mean = sum(x) / len(x)
  return mean
  
def sd(x):
  mean = sum(x) / len(x)
  differences = [xx - mean for xx in x]
  sq_differences = [xx**2 for xx in differences]
  sd = sqrt(sum(sq_differences)/len(x))
  return sd

def extractChannel(imp, nChannel, nFrame):
  """ Extract a stack for a specific color channel and time frame """
  stack = imp.getImageStack()
  ch = ImageStack(imp.width, imp.height)
  for i in range(1, imp.getNSlices() + 1):
    index = imp.getStackIndex(nChannel, i, nFrame)
    ch.addSlice(str(i), stack.getProcessor(index))
  return ImagePlus("Channel " + str(nChannel), ch)

def measureSumIntensity3D(imp):
  stats = StackStatistics(imp)
  return stats.mean * stats.pixelCount

def autoThreshold(imp, method):
  impout = imp.duplicate() 
  IJ.run(impout, "Auto Threshold", "method=" + method + " white stack use_stack_histogram");
  impout.setTitle("Auto Threshold")
  return impout

def threshold(_img, threshold):
  imp = Duplicator().run(_img)
  #imp.show(); time.sleep(0.2)
  #IJ.setThreshold(imp, mpar['lthr'], mpar['uthr'])
  IJ.setThreshold(imp, threshold, 1000000000)
  IJ.run(imp, "Convert to Mask", "stack")
  imp.setTitle("Threshold");
  #IJ.run(imp, "Divide...", "value=255 stack");
  #IJ.setMinAndMax(imp, 0, 1);
  return imp

def compute_overlap(tbModel, iDataSet, impA, iChannelA, iChannelB):
  imp_bw = ImageCalculator().run("AND create stack", impA[iChannelA-1], impA[iChannelB-1])
  overlap_AandB = measureSumIntensity3D(imp_bw)/255
  tbModel.setNumVal(overlap_AandB, iDataSet, "PAT_"+str(iChannelA)+"AND"+str(iChannelB))
  return tbModel

def cmd(args):
  p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
  output, err = p.communicate()
  return(output)
     
def convert_for_elastix(input_file, output_file):
  print("    creating mha")
  print("      reading tif")
  start_time = time.time()
  imp = IJ.openImage(input_file)
  IJ.run(imp, "Properties...", "unit=pixel pixel_width=1.0000 pixel_height=1.0000 voxel_depth=1.0000")
  print("        time spent: "+str(round(time.time()-start_time,3)))
  print("      writing mha")
  start_time = time.time()
  IJ.run(imp, "MHD/MHA ...", "save="+output_file);
  print("        time spent: "+str(round(time.time()-start_time,3)))
  return output_file

def deleteLine(fn, txt):
  f = open(fn)
  output = []
  for line in f:
    if not txt in line:
      output.append(line)
  f.close()
  f = open(fn, 'w')
  f.writelines(output)
  f.close()

def changeLine(fn, txt_id, txt):
  f = open(fn)
  output = []
  for line in f:
    if not txt_id in line:
      output.append(line)
    elif txt_id in line:
      print(line)
      output.append(txt+"\n")
      print(txt+"\n")
  f.close()
  f = open(fn, 'w')
  f.writelines(output)
  f.close()

  
  

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


def transform(fixed_file, moving_file, output_folder, p, init_with_previous_trafo = 0):
  print("  running elastix:")
  print("    fixed file:  "+fixed_file)
  print("    moving file: "+moving_file)      
  #moving_file = convert_for_elastix(moving_file, os.path.join(output_folder,"moving.mha"))    
     
  if init_with_previous_trafo:
     '''
     fixed_file = os.path.join(output_folder, "fixed.mha") 
     os.remove(fixed_file); time.sleep(1)
     os.rename(os.path.join(output_folder, "result.0.mha"), fixed_file); time.sleep(1)
     '''
     # fixed file exists already
     # fixed_file = os.path.join(output_folder, "fixed.mha") 
     # use previous transformation parameters as initialisation
     previous_transformation = os.path.join(output_folder, "TransformParameters.previous.txt")
     shutil.copyfile(os.path.join(output_folder, "TransformParameters.0.txt"), previous_transformation); time.sleep(1)
     deleteLine(previous_transformation, "InitialTransform"); time.sleep(1)
     start_time = time.time()   
     output = cmd([p["elastix_binary_file"], '-f', fixed_file, '-m', moving_file, '-out', output_folder, '-p',  p["elastix_parameter_file"] , '-t0', previous_transformation])
     print("    time spent: "+str(round(time.time()-start_time,3)))
  else:
    # generate fixed file
    #fixed_file = convert_for_elastix(fixed_file, os.path.join(output_folder,"fixed.mha"))   
    start_time = time.time()   
    output = cmd([p["elastix_binary_file"], '-f', fixed_file, '-m', moving_file, '-out', output_folder, '-p',  p["elastix_parameter_file"] ])
    print("    time spent: "+str(round(time.time()-start_time,3)))
  
  return(output)     
  
def copy_file(src, dst):
  print("  copying file: "+src)
  start_time = time.time()
  shutil.copyfile(src, dst)
  print("    time spent: "+str(round(time.time()-start_time,3)))


#
# Main code
#

def analyze(iReference, iDataSet, tbModel, p, output_folder):
  
  #
  # INIT
  #
  IJ.run("Options...", "iterations=1 count=1"); 
  close_all_image_windows()
    
  #
  # ANALYSE
  #
  
  # store path to reference file in table
  reference_file = tbModel.getFileAbsolutePathString(iReference, "RAW", "IMG")
  tbModel.setFileAbsolutePath(reference_file, iDataSet, "Reference", "IMG")
  fixed_file = tbModel.getFileAbsolutePathString(iReference, "RAW", "IMG")
  moving_file = tbModel.getFileAbsolutePathString(iDataSet, "RAW", "IMG")
  
  if abs(iReference-iDataSet) == 0: 
    init_with_previous_trafo = 0 # first transformation
  else:
    init_with_previous_trafo = 1 # subsequent transformations
    
  transform(fixed_file, moving_file, output_folder, p, init_with_previous_trafo) 
  
  #fixed_filename = tbModel.getFileName(iReference, "RAW", "IMG")+"--transformed.mha"
  #copy_file(os.path.join(output_folder, "fixed.mha"), os.path.join(output_folder, fixed_filename) )
  #tbModel.setFileAbsolutePath(output_folder, fixed_filename, iReference, "Transformed", "IMG")
  #else:
  #  #fixed_file = "use_previous_result"
  #  fixed_file = tbModel.getFileAbsolutePathString(iReference, "RAW", "IMG")
  #  transform(fixed_file, moving_file, output_folder, p, init_with_previous_trafo = 1)  
  
  # store transformed file
  moving_filename = tbModel.getFileName(iDataSet, "RAW", "IMG")+"--transformed.mha"
  copy_file(os.path.join(output_folder, "result.0.mha"), os.path.join(output_folder, moving_filename))
  tbModel.setFileAbsolutePath(output_folder, moving_filename, iDataSet, "Transformed", "IMG")
  	   
  #
  # SHOW DATA
  # 
  
  #imp.show()

  #
  # SCALING
  #
  
  #IJ.run(imp, "Scale...", "x="+str(p["scale"])+" y="+str(p["scale"])+" z=1.0 interpolation=Bilinear average process create"); 
  
  #
  # CONVERSION
  #
  
  #IJ.run(imp, "8-bit", "");
 
  #
  # CROPPING
  #
  
  #imp.setRoi(392,386,750,762);
  #IJ.run(imp, "Crop", "");

  
  #
  # BACKGROUND SUBTRACTION
  #
  
  # IJ.run(imp, "Subtract...", "value=32768 stack");

  #
  # REGION SEGMENTATION
  #
 

#
# ANALYZE INPUT FILES
#
def determine_input_files(foldername, tbModel):

  print("#\n# Determine input files in: "+foldername+"\n#")
  pattern = re.compile('(.*).tif') 
  #pattern = re.compile('(.*)--beats.tif') 
   
  i = 0
  for root, directories, filenames in os.walk(foldername):
	for filename in filenames:
	   print("Checking:", filename)
	   if filename == "Thumbs.db":
	     continue
	   match = re.search(pattern, filename)
	   if (match == None) or (match.group(1) == None):
	     continue
	   tbModel.addRow()
	   tbModel.setFileAbsolutePath(foldername, filename, i, "RAW","IMG")
	   print("Accepted:", filename)	   
	   i += 1

  print("#\n# Files to be analyzed\n#")
  for i in range(tbModel.getRowCount()):
    filename = tbModel.getFileName(i, "RAW", "IMG") 
    print(str(i)+": "+filename)
  
  return(tbModel)

#
# GET PARAMETERS
#
def get_parameters(p, num_data_sets):
  gd = GenericDialogPlus("Please enter parameters")

  gd.addMessage("found "+str(num_data_sets)+" data sets")
  
  for k in p.keys():
    if "_file" in k:
      gd.addFileField(k, str(p[k]))		
    elif type(p[k]) == type(""):
      gd.addStringField(k, p[k])
    elif type(p[k]) == type(1):
      gd.addNumericField(k, p[k],0)
    elif type(p[k]) == type(1.0):
      gd.addNumericField(k, p[k],2)
  
  gd.showDialog()
  if gd.wasCanceled():
    return

  for k in p.keys():
    if type(p[k]) == type(""):
      p[k] = gd.getNextString()
    elif type(p[k]) == type(1):
      p[k] = int(gd.getNextNumber())
    elif type(p[k]) == type(1.0):
      p[k] = gd.getNextNumber()
    
  return p

    
if __name__ == '__main__':

  print("#\n# Elastix registration\n#")

  #
  # GET INPUT FOLDER
  #
  od = OpenDialog("Select one of the images to be analysed", None)
  input_folder = od.getDirectory()
  if input_folder is None:
    sys.exit("No folder selected!")
    
  #
  # MAKE OUTPUT FOLDER
  #
  output_folder = input_folder[:-1]+"--fiji"
  if not os.path.isdir(output_folder):
    os.mkdir(output_folder)

  #
  # DETERMINE INPUT FILES
  #
  tbModel = TableModel(input_folder)
  tbModel.addFileColumns('RAW','IMG')
  tbModel = determine_input_files(input_folder, tbModel)
  
 
  #
  # GET PARAMETERS
  #
  print("#\n# Parameters\n#")
  
  p = dict()
  
  # registration method
  p["to_be_analyzed"] = "all"
  p["elastix_binary_file"] = "C:\\Program Files\\elastix_v4.8\\elastix"
  p["elastix_parameter_file"] = "C:\\Users\\tischer\\Desktop\\parameters_Affine.txt"
  p["reference_id"] = int(tbModel.getRowCount()/2) 
  p["strategy"] = "running"
  p["save_maximum_projections"] = "Yes"
  p["maximum_number_of_iterations"] = 500
  # determine image size from file and use
  # number_of_resolutions = print(int(math.log(image_size/10,2))
  p["image_pyramid_schedule"] = "32,16,8" 
  p["image_dimensions"] = 2 
     
  p = get_parameters(p, tbModel.getRowCount())
  print(p)
  
  
  #
  # INIT AND SHOW INTERACTIVE TABLE
  #
  
  tbModel.addFileColumns('Transformed','IMG')
  tbModel.addFileColumns('Reference','IMG')
  
  
  #
  # ANALYZE
  #
  print("#\n# Analysis\n#")


  resolutions = p["image_pyramid_schedule"].split(",")
  s = ""; 
  for resolution in resolutions:
    for d in range(p["image_dimensions"]): 
      s = s + resolution + " "
  p["number_of_resolutions"] = len(resolutions)
  p["image_pyramid_schedule"] = s
  
  # adapt parameter file
  changeLine(p["elastix_parameter_file"], "MaximumNumberOfIterations", "(MaximumNumberOfIterations "+str(int(p["maximum_number_of_iterations"]))+")")
  changeLine(p["elastix_parameter_file"], "NumberOfResolutions", "(NumberOfResolutions "+str(p["number_of_resolutions"])+")")  
  changeLine(p["elastix_parameter_file"], "ImagePyramidSchedule", "(ImagePyramidSchedule "+str(p["image_pyramid_schedule"])+")")  
    
  i_ref = p["reference_id"]
  n_files = tbModel.getRowCount()
  
  if not p["to_be_analyzed"]=="all":
    close_all_image_windows()
    analyze(i_ref, int(p["to_be_analyzed"])-1, tbModel, p, output_folder)
  else:  
    for i in range(i_ref,n_files,1):
      analyze(i_ref, i, tbModel, p, output_folder)    
    for i in range(i_ref-1,-1,-1):
      analyze(i_ref, i, tbModel, p, output_folder)    
  print("done!")

  close_all_image_windows()
  
  frame=ManualControlFrame(tbModel)
  frame.setVisible(True)
  
  