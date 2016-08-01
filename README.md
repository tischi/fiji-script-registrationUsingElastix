# fiji-registration

This repository contains information about registration algorithms (in Fiji). 

## fiji--elastix--interactive.py

Fiji script to run elastix registration.
Fiji handles the data and runs elastix via system calls.

### installation

- install fiji: https://fiji.sc/
- Windows
  - install elastix (tested with windows binary): http://elastix.isi.uu.nl/download.php
  - install Visual C++: http://www.microsoft.com/en-us/download/details.aspx?id=30679
    - see also here: http://elastix.isi.uu.nl/FAQ.php
- download and extract this repository: https://github.com/tischi/fiji-registration/archive/master.zip
  - move __AutoMic_JavaTools-1.1.0-SNAPSHOT-19072016.jar__ to Fiji's plugin folder

### running

- drag __fiji--elastix--interactive.py__ onto Fiji and [Run]
- select a file in the __/examples/2d-affine__ folder 
  - it should work with default settings
