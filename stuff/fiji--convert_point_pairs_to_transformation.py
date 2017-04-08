from mpicbg.trakem2.transform import AffineModel3D;
from mpicbg.models import PointMatch, Point;

#
# List of matching point pairs; for 3-D one needs 4; for 2-D one needs 3 
#
pointPairs = []
pointPairs.append(PointMatch(Point([230, 100, 0]), Point([200, 100, 0])))
pointPairs.append(PointMatch(Point([130, 300, 0]), Point([100, 300, 0])))
pointPairs.append(PointMatch(Point([330, 300, 0]), Point([300, 300, 0])))
pointPairs.append(PointMatch(Point([130, 300, 100]), Point([100, 300, 100])))

#
# Compute transformation matrix corresponding to the points
#
model = AffineModel3D();
model.fit( pointPairs );

#
# Apply transformation data set
# 

# using TransformJ
# - save transformation matrix as affine.txt file
# - make sure that the image scaling is in pixels, as TransfromJ works on scaled coordinates

#  IJ.run(imp, "TransformJ Affine", "matrix=[.../affine.txt] interpolation=Linear background=0.0");

# using imglib2 

# using IJ ops


#
# Print transformation matrix
#
s = model.toDataString()
s = s.split(" ")
t = ""
for i in range(0,4):
  t = t + str(round(float(s[i]),2)) + " "
print(t)
t = ""
for i in range(4,8):
  t = t + str(round(float(s[i]),2)) + " "
print(t)
t = ""
for i in range(8,12):
  t = t + str(round(float(s[i]),2)) + " "
print(t)
'''
