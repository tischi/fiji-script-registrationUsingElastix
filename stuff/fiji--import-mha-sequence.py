# Walk recursively through an user-selected directory
# and add all found filenames that end with ".tif"
# to a VirtualStack, which is then shown.
#
# It is assumed that all images are of the same type
# and have the same dimensions.
 
import os, re
from ij.io import DirectoryChooser
from ij import IJ, ImagePlus, ImageStack
 
def run():
  srcDir = DirectoryChooser("Choose!").getDirectory()
  if not srcDir:
    # user canceled dialog
    return
  # Assumes all files have the same size
  filepaths = []
  pattern = re.compile('ch1(.*)_(.*)transformed.mha')
  for root, directories, filenames in os.walk(srcDir):
    for filename in filenames:
      # Skip non-TIFF files
      match = re.search(pattern, filename)
      if (match == None) or (match.group(1) == None):
	    continue
      print(filename)
      path = os.path.join(root, filename)
      filepaths.append(path)
      # Upon finding the first image, initialize the VirtualStack
  
  vs = None
  sorted_filepaths = sorted(filepaths)
  
  for f in sorted(filepaths):
      IJ.openImage(f)
      print(f.split('\\')[-1])
      imp = IJ.getImage()  
      if vs is None:
        vs = ImageStack(imp.width, imp.height)
      # Add a slice, relative to the srcDir
      vs.addSlice(f.split('\\')[-1],imp.getProcessor())
      imp.hide()

  ImagePlus("Stack from subdirectories", vs).show()
 
run()