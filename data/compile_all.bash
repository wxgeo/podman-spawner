#!/usr/bin/env bash
# Compile the Java project.
javac -encoding utf8 -cp webcompresslib/src -d webcompresslib/bin $(find webcompresslib/src -name '*.java' ! -name '*Test.java' ! -path '*/test*')
javac -encoding utf8 -cp webpagesaver/src:webcompresslib/src -d webpagesaver/bin $(find webpagesaver/src -name '*.java' ! -name '*Test.java' ! -path '*/test*')
echo "Compilation successful."