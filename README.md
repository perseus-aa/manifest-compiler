# Manifest Compiler
A tool to compile IIIF manifests and web pages for Art & Archaeology artifacts.

## To Install
(Info about installing and using uv.)

## To Use
uv run python compile_manifests.py

The script generates manifests and web pages that embed Javascript invoking Mirador on each manifest.

This writes files to a temporary directory (/tmp/output). It takes a long time to run, because it is verifying that the image files actually exist on the image server (part of iiiprezi).

(There needs to be a script that does that validation and writes a report; there are many images missing at this point.)
