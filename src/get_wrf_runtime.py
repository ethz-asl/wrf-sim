import argparse
import numpy as np

parser = argparse.ArgumentParser(description='Parse the logfile and compile the runtime')
parser.add_argument('-f', '--file', required=True, help='Toplevel folder with all the cases')
args = parser.parse_args()

file = open(args.file, 'rt')

data = {}

for line in file:
    if 'Timing for main' in line:
        data_string = line.split('domain')[-1]
        domain = int(data_string.split(':')[0])
        domain_key = str(domain)
        time = float(data_string.split(':')[1].split('elapsed')[0])

        if domain_key in data.keys():
            data[domain_key].append(time)
        else:
            data[domain_key] = [time]

for key in data.keys():
    data[key] = np.array(data[key])


print('=======================')
total_runtime = 0
for key in data.keys():
    runtime_h = data[key].sum() / 3600
    steptime_s = data[key].mean()
    stepstd_s = data[key].std()
    total_runtime += runtime_h
    print('Domain {0} total runtime: {1:2f} h (per step: {2:2f}+-{3:2f} s)'.format(key, runtime_h, steptime_s, stepstd_s))
print('============')
print('Total runtime: {0:2f} h'.format(total_runtime))
print('=======================')

