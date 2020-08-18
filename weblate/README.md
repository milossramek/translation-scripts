# weblate
Scripts related to translation of the LibreOffice user interface, help and other files at https://translations.documentfoundation.org/
## etiptrans.py
A script to transfer translation of LibreOffice extended tooltips between the Help translation files and the UI translations files.

Originally, strings of extended tooltips were a part of LibreOffice/OpenOffice help, where they were marked by the <ahelp> tags. Later, these strings became a part of the UI translation po files, where they were marked by "msgctxt "extended tip...".

Transfer of the the tooltips from help to UI started in 2020, when the first of the 6000+ tooltips we added there. The original tooltips are part of the help text and remain there.

## Usage
1. Authentication
The required api key can be found in Weblate in Settings > Api access
1. The script can read the key from the WEBLATE_API_KEY
1. Usage: try ./epitrans.py help
1. Download translation files, transfer tooltip and upload modified filed to server:
 1. ./epitrans.py -p help -l sk download
 1. ./epitrans.py -p ui -l sk download
 1. ./epitrans.py -p ui -l sk trans
 1. ./epitrans.py -p ui -l sk upload
 

# Installation of dependencies
The script was written and tested in Linux and python3. It requires several common modules (polib, requests, filecmp, json) and the curl programm. It probably runs also in Windows Subsystem for Linux (Windows 10) and maybe also ain other environments. In Linux the modules can be installed using pip. 


