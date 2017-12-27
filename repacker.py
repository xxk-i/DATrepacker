#!/usr/local/bin/python3

import sys

from dat_utils import *

def main():
	if len(sys.argv) < 2:
		print("need input directory")
		sys.exit(1)
	
	indir = sys.argv[1]
	outfile = indir.lstrip(".") + ".dat"
	if len(sys.argv) == 3:
		outfile = sys.argv[2]
	
	pack = FilePackInfo(indir)
	write = Writer(pack)
	write.setOutFile(outfile)
	write.write()


if __name__ == '__main__':
	main()