import argparse
import fileinput

parser = argparse.ArgumentParser(description='Correct the resolution for the index file')
parser.add_argument('-i', '--index-file', required=True, help='Path to the index file')
parser.add_argument('-r', '--resolution', type=float, default=0.000277777777777, help='Correct resolution')
args = parser.parse_args()

for line in fileinput.input(args.index_file, inplace=True):
    if 'dx = ' in line:
        line = 'dx = {:.15f}\n'.format(args.resolution) 
    if 'dy = ' in line:
        line = 'dy = {:.15f}\n'.format(args.resolution) 
    print(line, end='')
