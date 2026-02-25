import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("directory")
arg = parser.parse_args()

if arg.directory:
    directory = arg.directory

from process_elastic_tensor import combine_elastic_constant_files_into_one_file_per_network

combine_elastic_constant_files_into_one_file_per_network(directory);

#working_dir = os.path.join(os.path.dirname(__file__),"..","test_restarts");