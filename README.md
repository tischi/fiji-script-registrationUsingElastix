# fiji-registration

For questions please contact: tischitischer@gmail.com

This repository conatins a Fiji script to run elastix registration algorithms; Fiji handles the data and runs elastix via system calls.

### installation

- install fiji: https://fiji.sc/
- Windows
  - install elastix: http://elastix.isi.uu.nl/download.php
  - install corresponding Visual C++: http://www.microsoft.com/en-us/download/details.aspx?id=30679
    - see also here: http://elastix.isi.uu.nl/FAQ.php
- download and extract this repository: https://github.com/tischi/fiji-registration/archive/master.zip
  - move __AutoMic_JavaTools-1.1.0-SNAPSHOT-19072016.jar__ to Fiji's plugin folder

### run it

- drag __fiji--elastix--interactive.py__ onto Fiji and [Run]
- select a file in the __.../examples/2d-affine__ folder 
  - it should work with default settings
  - the results will appear in an automatically created output folder named __.../examples/2d-affine--fiji__

### learn more

- elastix manual: http://elastix.isi.uu.nl/download/elastix_manual_v4.8.pdf

### usage notes and tips

- the reference_image_index is used to determine the reference file (counting from 0 using the python sort() command on the image filenames)
- using a Mask file is usually improving the results; one good way to make one is to blur and threshold the reference image; the values in the mask image need to be 0 and 1(not 255!)
