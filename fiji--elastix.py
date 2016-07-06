# use elastix from Fiji
import os
import subprocess
from subprocess import Popen, PIPE

def cmd(args):
  p = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
  output, err = p.communicate()
  return(output)

elastix = 'C:/Program Files/elastix_v4.8/elastix' 

output = cmd([elastix, '--help'])
print(output)