newImage("Untitled", "8-bit black", 512, 512, 11);
makeRectangle(141, 146, 217, 194);
setForegroundColor(255, 255, 255);
run("Fill", "stack");
run("Select None");
for(i=1; i<11; i++) {
  run("Next Slice [>]");
  wait(100);
  angle = 5*i;
  run("Rotate... ", "angle=&angle grid=1 interpolation=Bilinear slice");
}
run("Gaussian Blur...", "sigma=30 stack");
run("Divide...", "value=1.5 stack");
run("RandomJ Poisson", "mean=1.0 insertion=Modulatory");