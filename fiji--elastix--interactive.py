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
import collections, pickle, platform

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
  os.environ["DYLD_LIBRARY_PATH"] = "/Users/tischi/Downloads/elastix_macosx64_v4.8/lib:$DYLD_LIBRARY_PATH"
  #p = Popen(['/Users/tischi/Downloads/elastix_macosx64_v4.8/bin/elastix','--help'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
  #output, err = p.communicate()  
  p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
  output, err = p.communicate()  
  #print args
  #print output
  #print err
  return(output)
     
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
    median_trafo = running_median(trafo, p['median'])
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
  
  cmd_args = [p["elastix_binary_file"], '-priority', 'HIGH', '-f', fixed_file, '-m', moving_file, '-out', output_folder, '-p',  p["elastix_parameter_file"]]

  if init_with_trafo: 
    cmd_args.append('-t0')
    cmd_args.append(init_with_trafo)   
   
  if p['mask_file']:
    cmd_args.append('-fMask')
    cmd_args.append(p['mask_file'])
    
  print("    initial trafo: "+init_with_trafo)
  print("    reference: "+fixed_file) 
  print("    to be transformed: "+moving_file)      
   
  start_time = time.time()   
  output = cmd(cmd_args)
  print("    time elapsed: "+str(round(time.time()-start_time,3)))
    
  return(output)     
  
def copy_file(src, dst):
  #print("  copying file: ")
  #print("    src: "+src)
  #print("    dst: "+dst)
  #start_time = time.time()
  shutil.copyfile(src, dst)
  #print("    time elapsed: "+str(round(time.time()-start_time,3)))


#
# Make parameter file
#

def make_parameter_file(p):

  file_path = p['elastix_parameter_file']
  script_file = file(file_path, "w")

  image_pyramid_schedule = p["image_pyramid_schedule"].split(",")
  s = ""; 
  for resolution in image_pyramid_schedule:
    for d in range(p["image_dimensions"]): 
      s = s + resolution + " "
  image_pyramid_schedule = s


  txt = [
  '(Transform "'+p['transformation']+'")',
  '(NumberOfResolutions '+str(p["number_of_resolutions"])+')',
  '(ImagePyramidSchedule '+image_pyramid_schedule+')',
  '(MaximumNumberOfIterations '+str(int(p["maximum_number_of_iterations"]))+')',
  '(NumberOfSpatialSamples '+str(p["number_of_spatial_samples"])+')',
  '(DefaultPixelValue '+str(p["image_background_value"])+')',
  '(WriteTransformParametersEachIteration "false")',
  '(WriteTransformParametersEachResolution "false")',
  '(WriteResultImageAfterEachResolution "false")',
  '(WritePyramidImagesAfterEachResolution "false")',
  '(FixedInternalImagePixelType "float")',
  '(MovingInternalImagePixelType "float")',
  '(UseDirectionCosines "false")', # ?
  '(Registration "MultiResolutionRegistration")',
  '(Interpolator "LinearInterpolator")',
  '(ResampleInterpolator "FinalLinearInterpolator")', # Could be BSpline
  '(Resampler "DefaultResampler")',
  '(FixedImagePyramid "FixedRecursiveImagePyramid")', # check manual
  '(MovingImagePyramid "MovingRecursiveImagePyramid")', # check manual
  '(Optimizer "AdaptiveStochasticGradientDescent")',
  '(Metric "AdvancedMeanSquares")',
  '(AutomaticScalesEstimation "true")',
  '(AutomaticTransformInitialization "false")',  # better false as this might fail
  '(HowToCombineTransforms "Compose")',
  '(NumberOfHistogramBins 32)',
  '(ErodeMask "false")',
  '(NewSamplesEveryIteration "true")',
  '(ImageSampler "Random")',
  '(BSplineInterpolationOrder 1)', 
  '(FinalBSplineInterpolationOrder 3)',
  '(WriteResultImage "true")',
  '(ResultImagePixelType "short")', # adapt this!
  '(ResultImageFormat "'+p['output_format']+'")' # why not tif?
  ]
  txt = '\n'.join(txt)
  txt = txt + '\n'
  print(txt)
  script_file.write(txt)
  script_file.close()

  return file_path

def show_standard_error_message():
  IJ.error("There was an error.\n\
Please check the text below the script editor window.\n\
Please toggle between [Show Errors] and [Show Output], as both are relevant.")
    
def rename(old_filepath, new_filepath):
  try:
    os.rename(old_filepath, new_filepath); time.sleep(1)
  except:
    show_standard_error_message()
    print("\n  error during renaming:")
    print("    renaming: "+old_filepath)
    print("        into: "+new_filepath)
    print("  Often this happens because the target file exists already and is write protected; please try again with a new output folder.")
    sys.exit(0)
  

#
# Transformation
#

def compute_transformations(iReference, iDataSet, tbModel, p, output_folder, init_with_trafo, previous_transformed_image):
  
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
  # find transformation using reference channel
  #
  
  if not previous_transformed_image:
    fixed_file = tbModel.getFileAbsolutePathString(iReference, "Input_"+p["ch_ref"], "IMG")
  else:
    fixed_file = previous_transformed_image
  moving_file = tbModel.getFileAbsolutePathString(iDataSet, "Input_"+p["ch_ref"], "IMG")
  
  elastix(fixed_file, moving_file, output_folder, p, init_with_trafo) 
  elastix_output_filepath = os.path.join(output_folder, "result.0."+p['output_format'])
  
  # check if it worked
  if not os.path.isfile(elastix_output_filepath):
    show_standard_error_message()
    print("\nThe elastix output file was not produced: " + elastix_output_filepath)
    print("Please check the elastix log file: " + os.path.join(output_folder, "elastix.log"))
    sys.exit(0)

  #
  # store results
  #

  # construct transformed filename 
  transformed_filename = tbModel.getFileName(iDataSet, "Input_"+p["ch_ref"], "IMG")+"--transformed."+p['output_format']
  
  # secure transformed file by renaming
  rename(elastix_output_filepath, os.path.join(output_folder, transformed_filename))
    
  tbModel.setFileAbsolutePath(output_folder, transformed_filename, iDataSet, "Transformed_"+p['ch_ref'], "IMG")
    
  # store transformation file
  transformation_file = os.path.join(output_folder, "transformation-"+str(moving_file.split(os.sep)[-1]+".txt"))
  copy_file(os.path.join(output_folder, "TransformParameters.0.txt"), transformation_file )
         
  # store log file
  copy_file(os.path.join(output_folder, "elastix.log"), os.path.join(output_folder, "elastix-"+str(moving_file.split(os.sep)[-1]+".log")))

  return tbModel, transformation_file, os.path.join(output_folder, transformed_filename)



def apply_transformation(iDataSet, tbModel, p, output_folder):

  #
  # apply transfomations to all channel(s)
  #
  
  for ch in p["channels"]:
    if not ch==p["ch_ref"]:
      moving_file = tbModel.getFileAbsolutePathString(iDataSet, "Input_"+ch, "IMG")
      moving_ref_file = tbModel.getFileAbsolutePathString(iDataSet, "Input_"+p["ch_ref"], "IMG") # only needed to get the reference file   
      transformation_file = os.path.join(output_folder, "transformation-"+str(moving_ref_file.split(os.sep)[-1]+".txt"))
      transformix(moving_file, output_folder, p, transformation_file) 
      
      # store transformed file by renaming
      transformed_filename = tbModel.getFileName(iDataSet, "Input_"+ch, "IMG")+"--transformed."+p['output_format']
      rename(os.path.join(output_folder, "result."+p['output_format']), os.path.join(output_folder, transformed_filename))
      tbModel.setFileAbsolutePath(output_folder, transformed_filename, iDataSet, "Transformed_"+ch, "IMG")
   
  return tbModel

 
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

def get_parameters(p):
  gd = GenericDialogPlus("Please enter parameters")

  for k in p['expose_to_gui']['value']:
    if p[k]['type'] == 'folder':
      gd.addDirectoryField(k, p[k]['value'], 100)	
    if p[k]['type'] == 'file':
      gd.addFileField(k, p[k]['value'], 100)	
    elif p[k]['type'] == 'string':
      if p[k]['choices']:
        gd.addChoice(k, p[k]['choices'], p[k]['value'])	
      else:
        gd.addStringField(k, p[k]['value'])	 
    elif p[k]['type'] == 'int':
      if p[k]['choices']:
        gd.addChoice(k, p[k]['choices'], p[k]['value'])	
      else:
        gd.addNumericField(k, p[k]['value'], 0)	 
    elif p[k]['type'] == 'float':
      gd.addNumericField(k, p[k]['value'], 2)
  
  gd.showDialog()
  if gd.wasCanceled():
    return

  for k in p['expose_to_gui']['value']:
    if p[k]['type'] == 'folder' or p[k]['type'] == 'file':
      p[k]['value'] = gd.getNextString()
    elif p[k]['type'] == 'string':
      if p[k]['choices']:
        p[k]['value'] = gd.getNextChoice()	
      else:
        p[k]['value'] = gd.getNextString()	 
    elif p[k]['type'] == 'int':
      if p[k]['choices']:
        p[k]['value'] = int(gd.getNextChoice())	
      else:
        p[k]['value'] = int(gd.getNextNumber()) 
    elif p[k]['type'] == 'float':
        p[k]['value'] = gd.getNextNumber()
    
  return p

    
if __name__ == '__main__':

  print("#\n# Elastix registration\n#")
    
  #
  # GET PARAMETERS
  #
  print("#\n# Parameters\n#")

  #
  # Load gui parameters
  #

  od = OpenDialog("Select parameter file (press CANCEL if you don't have one)", None)
  f = od.getPath()
  
  if f:
    print('loading parameters from file')
    f = open(f, 'r'); p_gui = pickle.load(f); f.close()
  else:
    print('starting from default parameters')
    # make parameter structure if it has not been loaded
    p_gui = {}
    # exposed to GUI
    p_gui['expose_to_gui'] = {'value': ['input_folder', 'output_folder', 'output_format', 'channels', 'ch_ref', 'reference_image_index', 'transformation', 
                          'image_background_value', 'mask_file', 'maximum_number_of_iterations', 'image_pyramid_schedule',
                          'number_of_spatial_samples', 'elastix_binary_file', 'transformix_binary_file']}
    p_gui['input_folder'] = {'choices': '', 'value': 'C:\\Users\\tischer\\Documents', 'type': 'folder'}
    p_gui['output_folder'] = {'choices': '', 'value': 'C:\\Users\\tischer\\Documents', 'type': 'folder'}
    p_gui['output_format'] = {'choices': ['mha','tif'], 'value': 'tif', 'type': 'string'}
    p_gui['image_dimensions'] = {'choices': [2,3], 'value': 2, 'type': 'int'} 
    p_gui['channels'] = {'choices': '', 'value': 'ch0,ch1', 'type': 'string'}
    p_gui['ch_ref'] = {'choices': '', 'value': 'ch0', 'type': 'string'}
    p_gui['reference_image_index'] = {'choices': '', 'value': 0, 'type': 'int'}
    p_gui['transformation'] = {'choices': ['TranslationTransform', 'EulerTransform', 'AffineTransform'], 'value': 'AffineTransform', 'type': 'string'}
    p_gui['image_background_value'] = {'choices': '', 'value': 16, 'type': 'int'}
    p_gui['mask_file'] = {'choices': '', 'value': '', 'type': 'file'}
    p_gui['maximum_number_of_iterations'] = {'choices': '', 'value': 500, 'type': 'int'}
    p_gui['image_pyramid_schedule'] = {'choices': '', 'value': '16,4', 'type': 'string'}
    p_gui['number_of_spatial_samples'] = {'choices': '', 'value': 1000, 'type': 'int'}    
    p_gui['elastix_binary_file'] = {'choices': '', 'value': 'C:\\Program Files\\elastix_v4.8\\elastix', 'type': 'file'}
    p_gui['transformix_binary_file'] = {'choices': '', 'value': 'C:\\Program Files\\elastix_v4.8\\transformix', 'type': 'file'}
    p_gui['number_of_resolutions'] = {'value': ''}
    p_gui['elastix_parameter_file'] = {'value': ''}

  #
  # Expose parameters to users
  #
  p_gui = get_parameters(p_gui)
  
  #
  # Create derived paramters
  #
  p_gui['number_of_resolutions'] = {'value': len(p_gui['image_pyramid_schedule']['value'].split(","))}
  p_gui['elastix_parameter_file'] = {'value': os.path.join(p_gui['output_folder']['value'], 'elastix-parameters.txt')}
  
  #
  # Save gui parameters
  #
  f = open(os.path.join(p_gui['output_folder']['value'], 'fiji-elastix-gui-parameters.txt'), 'w')
  pickle.dump(p_gui, f)
  f.close()
   
  #
  # Reformat gui parameters for actual usage
  # 
  p = {}
  for k in p_gui.keys():
    p[k] = p_gui[k]['value']
  
  p['channels'] = p_gui['channels']['value'].split(",")

  #
  # DETERMINE INPUT FILES
  #
      
  tbModel = TableModel(p['input_folder'])
  files = get_file_list(p['input_folder'], '(.*).tif')
  

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
      if ch in afile.split(os.sep)[-1]:
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

  #
  # Create elastix parameter file
  #
  
  make_parameter_file(p)

  #
  # Compute transformations  
  #
  n_files = tbModel.getRowCount()
  
  # backwards from reference file
  previous_trafo = ""
  previous_transformed_image = ""
  for i in range(p['reference_image_index'],-1,-1):
    # compute transformation and transform reference channel
    tbModel, previous_trafo, previous_transformed_image = compute_transformations(p['reference_image_index'], i, tbModel, p, p['output_folder'], previous_trafo, previous_transformed_image)    
    # apply transformation to all other channels
    tbModel = apply_transformation(i, tbModel, p, p['output_folder'])

  # forward from reference file
  previous_trafo = ""
  previous_transformed_image = ""
  for i in range(p['reference_image_index'],n_files,+1):
    # compute transformation and transform reference channel
    tbModel, previous_trafo, previous_transformed_image = compute_transformations(p['reference_image_index'], i, tbModel, p, p['output_folder'], previous_trafo, previous_transformed_image)    
    # apply transformation to all other channels
    tbModel = apply_transformation(i, tbModel, p, p['output_folder'])

  #
  # Smooth transformations over time
  #
  #if p['median_window'] > 1:
  #  files = get_file_list(p['output_folder'], 'TransformParameters.0-(.*)')
  #  smooth_transformation_files(files, p)
  
  print("done!")

  close_all_image_windows()
  
  frame = ManualControlFrame(tbModel)
  frame.setVisible(True)
  
  