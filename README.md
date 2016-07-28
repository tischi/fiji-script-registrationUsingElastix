# fiji-registration

This repository contains information about registration algorithms (in Fiji). 

## fiji--elastix--interactive.py

Fiji script to run elastix registration.
Fiji handles the data and runs elastix via system calls.

### installation

- fiji: https://fiji.sc/
- elastix (tested with windows binary): http://elastix.isi.uu.nl/download.php
- download and extract this repository: https://github.com/tischi/fiji-registration/archive/master.zip
  - move AutoMic_JavaTools-1.1.0-SNAPSHOT-19072016.jar to Fiji's plugin folder

### running

- drag fiji--elastix--interactive.py onto Fiji and [Run] at bottom of the script editor

## other things to try

### x,y,z maximum projections with stackreg and then 3-D with TransformJ

- would have to write code

### Perrine's java code

- try to get it running

### Amira

- ???

### Icy with ec-CLEM Plugin

- only 2D or with manual annotation

### Imglib2

- Saalfeld: "Tobias implemented the basic Thenevaz approach for full affines some
years ago for ImgLib2. It's in one of the advanced tutorials and works
in an arbitrary number of dimensions. Images need to be approximately
registered."
- find tutorial
