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
from ij.gui import Plot

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
  print("        time elapsed: "+str(round(time.time()-start_time,3)))
  print("      writing mha")
  start_time = time.time()
  IJ.run(imp, "MHD/MHA ...", "save="+output_file);
  print("        time elapsed: "+str(round(time.time()-start_time,3)))
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
  print("      time elapsed: "+str(round(time.time()-start_time,3)))
  imp = IJ.getImage()
  IJ.run(imp, "32-bit", "");
  IJ.setMinAndMax(0, 65535);
  IJ.run(imp, "16-bit", "");
  output_file = os.path.join(output_folder,original_filename+"--transformed.tif")
  print("    writing tif")
  start_time = time.time()
  IJ.saveAs(imp, "Tiff", output_file)
  print("      time elapsed: "+str(round(time.time()-start_time,3)))
  # optional to save maximum projections
  if(save_as_max):
    if(imp.getStackSize()>1):
      print("    make and save z-max")
      start_time = time.time()
      IJ.run(imp, "Z Project...", "projection=[Max Intensity]")
      IJ.saveAs(IJ.getImage(), "Tiff", output_file+"--z-max.tif")
      print("      time elapsed: "+str(round(time.time()-start_time,3)))
  return output_file



def transformix(moving_file, output_folder, p, transformation_file):
  print("  running transformix:")
  print("    transformation file: "+transformation_file)      
  print("    moving file: "+moving_file)      
  start_time = time.time()   
  output = cmd([p["transformix_binary_file"], '-in', moving_file, '-out', output_folder, '-tp',  transformation_file])
  print("    time elapsed: "+str(round(time.time()-start_time,3)))
  
  return(output)     

def scatter_plot(title, x, y, x_lab, y_lab):
  plot = Plot(title, x_lab, y_lab, [], [])
  plot.addPoints(x, y, Plot.CIRCLE)
  #plot.setLimits(min(x),
  plot.show()

def smooth_transformation_files(files, p):

  transformations = []
    
  for fn in files:
    f = open(fn)
    for line in f:
      if '(TransformParameters' in line:
        transformation = re.findall(r'[-+]?\d+[\.]?\d*', line)
        transformations.append(transformation)
        break
  f.close()
  
  for i in range(len(transformations[0])):
    trafo = [float(t[i]) for t in transformations]
    scatter_plot('trafo', range(len(trafo)), trafo, 'frame', 't'+str(i))
    median_trafo = running_median(trafo, p['median_window'])
    scatter_plot('trafo_median', range(len(trafo)),  median_trafo, 'frame', 't'+str(i))
    for j in range(len(trafo)):
      transformations[j][i] = median_trafo[j]

  for i, fn in enumerate(files):
    transformation_line = " ".join('%.10f' % x for x  in transformations[i])
    transformation_line = '(TransformParameters '+transformation_line+')\n'
    changeLine(fn, '(TransformParameters', transformation_line)
    
  return(1)
  

#
# running median: from http://code.activestate.com/recipes/578480-running-median-mean-and-mode/
#

from collections import deque
from bisect import insort, bisect_left
from itertools import islice

def running_median(seq, M):
    
    seq = iter(seq)
    s = []   
    m = M // 2

    # Set up list s (to be sorted) and load deque with first window of seq
    s = [item for item in islice(seq,M)]    
    d = deque(s)

    # Simple lambda function to handle even/odd window sizes    
    median = lambda : s[m] if bool(M&1) else (s[m-1]+s[m])*0.5

    # Sort it in increasing order and extract the median ("center" of the sorted window)
    s.sort()    
    medians = [median()]   

    # Now slide the window by one point to the right for each new position (each pass through 
    # the loop). Stop when the item in the right end of the deque contains the last item in seq
    for item in seq:
        old = d.popleft()          # pop oldest from left
        d.append(item)             # push newest in from right
        del s[bisect_left(s, old)] # locate insertion point and then remove old 
        insort(s, item)            # insert newest such that new sort is not required        
        medians.append(median())  

    # popluate boundary values (added by Tischi)
    for i in range(int(M/2)):
      medians.insert(0, medians[0])
      medians.append(medians[len(medians)-1])
    
    return medians

def elastix(fixed_file, moving_file, output_folder, p, init_with_trafo = ""):
  print("  running elastix:")
  
  if init_with_trafo: 
    fixed_file = os.path.join(output_folder, "fixed.mha") 
    if os.path.isfile(fixed_file):
      os.remove(fixed_file); time.sleep(1)
    os.rename(os.path.join(output_folder, "result.0.mha"), fixed_file); time.sleep(1)
    # fixed file exists already
    # fixed_file = os.path.join(output_folder, "fixed.mha") 
    # use previous transformation parameters as initialisation
    #previous_transformation = os.path.join(output_folder, "TransformParameters.previous.txt")
    #shutil.copyfile(os.path.join(output_folder, "TransformParameters.0.txt"), previous_transformation); time.sleep(1)
    #deleteLine(previous_transformation, "InitialTransform"); time.sleep(1)
    cmd_args = [p["elastix_binary_file"], '-priority', 'HIGH', '-f', fixed_file, '-m', moving_file, '-out', output_folder, '-p',  p["elastix_parameter_file"]]
    cmd_args.append('-t0')
    cmd_args.append(init_with_trafo)   
  else:
    cmd_args = [p["elastix_binary_file"], '-priority', 'HIGH', '-f', fixed_file, '-m', moving_file, '-out', output_folder, '-p',  p["elastix_parameter_file"]]
   
  if p['mask_file']:
    cmd_args.append('-fMask')
    cmd_args.append(p['mask_file'])
    
  print("    initial trafo: "+init_with_trafo)
  print("    register against: "+fixed_file) 
  print("    moving file: "+moving_file)      
   
  start_time = time.time()   
  output = cmd(cmd_args)
  print("    time elapsed: "+str(round(time.time()-start_time,3)))
    
  return(output)     
  
def copy_file(src, dst):
  print("  copying file: "+src)
  start_time = time.time()
  shutil.copyfile(src, dst)
  print("    time elapsed: "+str(round(time.time()-start_time,3)))


#
# Main code
#

def compute_transformations(iReference, iDataSet, tbModel, p, output_folder, init_with_trafo):
  
  #
  # INIT
  #
  IJ.run("Options...", "iterations=1 count=1"); 
  close_all_image_windows()
    
  #
  # ANALYSE
  #

  
  # store path to reference file in table
  tbModel.setFileAbsolutePath(tbModel.getFileAbsolutePathString(iReference, "Input_"+p['ch_ref'], "IMG"), iDataSet, "Reference", "IMG")
  
  #
  # find transformation
  #
  
  fixed_file = tbModel.getFileAbsolutePathString(iReference, "Input_"+p["ch_ref"], "IMG")
  moving_file = tbModel.getFileAbsolutePathString(iDataSet, "Input_"+p["ch_ref"], "IMG")
  elastix(fixed_file, moving_file, output_folder, p, init_with_trafo) 
  
  # store transformation matrix
  moving_filename = tbModel.getFileName(iDataSet, "Input_"+p["ch_ref"], "IMG")+"--transformed.mha"
  
  # copy transformation file
  transformation_file = os.path.join(output_folder, "transformation-"+str(moving_file.split('\\')[-1]+".txt"))
  copy_file(os.path.join(output_folder, "TransformParameters.0.txt"), transformation_file )
  #deleteLine(transformation_file, "InitialTransform")
  # store path to reference file in table
  #tbModel.setFileAbsolutePath(iDataSet, "IMG"), iDataSet, "Reference", "IMG")

  # copy transformed file
  #copy_file(os.path.join(output_folder, "result.0.mha"), os.path.join(output_folder, moving_filename))
    
     
  # store log file
  copy_file(os.path.join(output_folder, "elastix.log"), os.path.join(output_folder, "elastix-"+str(moving_file.split('\\')[-1]+".log")))

  return transformation_file

def apply_transformation(iDataSet, tbModel, p, output_folder):

  #
  # apply transfomations to all channel(s)
  #
  
  for ch in p["channels"]:
    moving_file = tbModel.getFileAbsolutePathString(iDataSet, "Input_"+ch, "IMG")
    moving_ref_file = tbModel.getFileAbsolutePathString(iDataSet, "Input_"+p["ch_ref"], "IMG")    
    transformation_file = os.path.join(output_folder, "transformation-"+str(moving_ref_file.split('\\')[-1]+".txt"))
    transformix(moving_file, output_folder, p, transformation_file) 
      
    # store transformed file
    moving_filename = tbModel.getFileName(iDataSet, "Input_"+ch, "IMG")+"--transformed.mha"
    copy_file(os.path.join(output_folder, "result.mha"), os.path.join(output_folder, moving_filename))
    tbModel.setFileAbsolutePath(output_folder, moving_filename, iDataSet, "Transformed_"+ch, "IMG")
    
 
#
# ANALYZE INPUT FILES
#

def get_file_list(foldername, reg_exp):

  print("#\n# Finding files in: "+foldername+"\n#")
  pattern = re.compile(reg_exp)
   
  files = []
  for root, directories, filenames in os.walk(foldername):
	for filename in filenames:
	   print("Checking:", filename)
	   if filename == "Thumbs.db":
	     continue
	   match = re.search(pattern, filename)
	   if (match == None) or (match.group(1) == None):
	     continue
	   files.append(os.path.join(foldername, filename))  
	   print("Accepted:", filename)	   

  return(sorted(files))

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
  files = get_file_list(input_folder, '(.*).tif')
  
  #
  # GET PARAMETERS
  #
  print("#\n# Parameters\n#")
  
  p = dict()
  
  # registration method
  p["to_be_analyzed"] = "all"
  p['median_window'] = 0
  p["elastix_binary_file"] = "C:\\Program Files\\elastix_v4.8\\elastix"
  p["transformix_binary_file"] = "C:\\Program Files\\elastix_v4.8\\transformix"
  p["mask_file"] = "" #'Z:\\HenningFalk\\Tischi_Reg\\mask.tif'
  p["elastix_parameter_file"] = "C:\\Users\\tischer\\Desktop\\parameters_Affine.txt"
  p["reference_id"] = 0
  p["save_maximum_projections"] = "Yes"
  p["maximum_number_of_iterations"] = 300
  # determine image size from file and use
  # number_of_resolutions = print(int(math.log(image_size/10,2))
  p["image_pyramid_schedule"] = "16,4" 
  p["image_dimensions"] = 2 
  p["channels"] = "ch1"
  p["ch_ref"] = "ch1"
  p["image_background_value"] = 307
  p["number_of_spatial_samples"] = 3000
  
  p = get_parameters(p, len(files))
  print(p)

  p["channels"] = p["channels"].split(",")
  p["image_pyramid_schedule"] = p["image_pyramid_schedule"].split(",")
    
  #
  # INIT INTERACTIVE TABLE
  #
  
  tbModel.addFileColumns('Reference','IMG')
  
  for ch in p["channels"]:
    tbModel.addFileColumns('Input_'+ch,'IMG')
  
  for ch in p["channels"]:
    tbModel.addFileColumns('Transformed_'+ch,'IMG')
    
  sorted_files = sorted(files)
  print("#\n# Files to be analyzed\n#")
  for ch in p["channels"]:
    iDataSet = 0
    for afile in sorted_files:
      if ch in afile.split("\\")[-1]:
        if ch == p["channels"][0]:
          tbModel.addRow()
          print(str(iDataSet)+": "+afile)
        tbModel.setFileAbsolutePath(afile, iDataSet, "Input_"+ch,"IMG")
        iDataSet = iDataSet + 1

  #frame=ManualControlFrame(tbModel)
  #frame.setVisible(True)
  
  #
  # ANALYZE
  #
  print("#\n# Analysis\n#")

  # reformat resolution pyramid layer parameters
  s = ""; 
  for resolution in p["image_pyramid_schedule"]:
    for d in range(p["image_dimensions"]): 
      s = s + resolution + " "
  p["number_of_resolutions"] = len(p["image_pyramid_schedule"])
  p["image_pyramid_schedule"] = s
  
  # adapt parameter file
  changeLine(p["elastix_parameter_file"], "MaximumNumberOfIterations", "(MaximumNumberOfIterations "+str(int(p["maximum_number_of_iterations"]))+")")
  changeLine(p["elastix_parameter_file"], "NumberOfResolutions", "(NumberOfResolutions "+str(p["number_of_resolutions"])+")")  
  changeLine(p["elastix_parameter_file"], "ImagePyramidSchedule", "(ImagePyramidSchedule "+str(p["image_pyramid_schedule"])+")")  
  changeLine(p["elastix_parameter_file"], "DefaultPixelValue", "(DefaultPixelValue "+str(p["image_background_value"])+")")  
  changeLine(p["elastix_parameter_file"], "NumberOfSpatialSamples", "(NumberOfSpatialSamples "+str(p["number_of_spatial_samples"])+")")  


  #
  # Compute transformations  
  #
  n_files = tbModel.getRowCount()
  #for i in range(n_files):
  #  compute_transformations(p["reference_id"], i, tbModel, p, output_folder)    

  p["reference_id"] = n_files-1
  previous_trafo = ""
  for i in range(n_files-1,-1,-1):
    previous_trafo = compute_transformations(p["reference_id"], i, tbModel, p, output_folder, previous_trafo)    

  #
  # Smooth transformations over time
  #
  if p['median_window']>1:
    files = get_file_list(output_folder, 'TransformParameters.0-(.*)')
    smooth_transformation_files(files, p)
  
  #
  # Todo; this does not always make sense!
  #
  #
  
  # Apply (smoothed) transformations
  #
  
  for i in range(n_files):
    apply_transformation(i, tbModel, p, output_folder)

  print("done!")

  close_all_image_windows()
  
  frame=ManualControlFrame(tbModel)
  frame.setVisible(True)
  
  