from mpicbg.trakem2.transform import AffineModel3D;
from mpicbg.models import PointMatch, Point;

# translation by (2,2,2)
'''
pointPairs = []
pointPairs.append(PointMatch(Point([0, 0, 0]), Point([2, 2, 2])))
pointPairs.append(PointMatch(Point([1, 0, 0]), Point([3, 2, 2])))
pointPairs.append(PointMatch(Point([0, 1, 0]), Point([2, 3, 2])))
pointPairs.append(PointMatch(Point([0, 0, 1]), Point([2, 2, 3])))
'''

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
# Apply transformation to a data set
# 

# - e.g., using TransformJ
#IJ.run(imp, "TransformJ Affine", "matrix=N:/ALMF_presentations/0000--Tischi--Practical_ImageJ/data-all/registration/30-along-x.txt interpolation=Linear background=0.0");

# - e.g., using something else


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