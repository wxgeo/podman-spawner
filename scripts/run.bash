#!/bin/bash

# Check the number of arguments
if [ $# -eq 0 ]; then
    # No arguments, execute `tree`.
    tree -P "*.java" --prune
elif [ $# -eq 1 ]; then
    # One argument, execute `java`.
    java -cp webpagesaver/bin:webcompresslib/bin "$1"
else
    # More than one argument, print usage
    echo "Usage: $0 [package.JavaClass]"
fi



