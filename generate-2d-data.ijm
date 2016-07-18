newImage("Untitled", "8-bit black", 512, 512, 11);
makeRectangle(100, 100, 200, 200);
setForegroundColor(150, 150, 150);
run("Fill", "stack");
run("Select None");
for(i=1; i<11; i++) {
  run("Next Slice [>]");
  wait(100);
  angle = 5*i;
  run("Rotate... ", "angle=&angle grid=1 interpolation=Bilinear slice");
  translation = 5*i;
  run("Translate...", "x=&translation y=&translation interpolation=None slice");
  shrinkage = 3*i;
  run("Minimum...", "radius=&shrinkage slice");
  
}
// background
run("Add...", "value=25 stack");
// blur
run("Gaussian Blur...", "sigma=30 stack");
// noise
run("Divide...", "value=1.5 stack");
run("RandomJ Poisson", "mean=1.0 insertion=Modulatory");
run("8-bit");