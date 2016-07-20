# Walk recursively through an user-selected directory
# and add all found filenames that end with ".tif"
# to a VirtualStack, which is then shown.
#
# It is assumed that all images are of the same type
# and have the same dimensions.
 
import os
from ij.io import DirectoryChooser
from ij import IJ, ImagePlus, ImageStack
 
def run():
  srcDir = DirectoryChooser("Choose!").getDirectory()
  if not srcDir:
    # user canceled dialog
    return
  # Assumes all files have the same size
  filepaths = []
  for root, directories, filenames in os.walk(srcDir):
    for filename in filenames:
      # Skip non-TIFF files
      if not filename.endswith("transformed.mha"):
        continue
      print(filename)
      path = os.path.join(root, filename)
      filepaths.append(path)
      # Upon finding the first image, initialize the VirtualStack
  
  vs = None
  for f in sorted(filepaths):
      IJ.openImage(f)
      imp = IJ.getImage()  
      if vs is None:
        vs = ImageStack(imp.width, imp.height)
      # Add a slice, relative to the srcDir
      vs.addSlice(imp.getProcessor())
      imp.hide()

  ImagePlus("Stack from subdirectories", vs).show()
 
run()