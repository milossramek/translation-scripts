# weblate
Scripts related to translation of the LibreOffice user interface, help and other files at https://translations.documentfoundation.org/
## etiptrans.py
A script to transfer translation of LibreOffice extended tooltips between the Help translation files and the UI translations files.

Originally, strings of extended tooltips were a part of LibreOffice/OpenOffice Help, where they were marked by the `<ahelp>` tags. Later, these strings became a part of the UI translation po files, where they were marked by `msgctxt "extended tip..."`.

Transfer of the the tooltips from Help to UI started in 2020, when first of the 6000+ tooltips we added there. The original tooltips remain part of the help text.

### Authentication
The required api key can be found in Weblate in Settings > Api access.  The script can read the key from the `WEBLATE_API_KEY` environment variable. 

### Basic documentation
Try `./epitrans.py help` or `.epitrans.y -h`

### Download translation files, transfer tooltips and upload modified filed to server:
Run the commands. Use the -v switch to see what is being downloaded
  1. `./epitrans.py -p help -l sk -v download`
  1. `./epitrans.py -p ui -l sk -v download`
  1. `./epitrans.py -p ui -l sk transfer`
  1. `./epitrans.py -p ui -l sk upload`

The `download` command will create directory `libo_help-master` (`libo_ui-master`) with po files. Each file has a hidden copy (do not change them). If downloading hangs (this happens sometimes), just cancel the script and restart it.

The `transfer` command lists all relevant tooltips. If they are not translated in the help, a notice is displayed:

`Untranslated in libo_help-master/sk/helpcontent2/source/text/shared/optionen.po: Type the name of...`

The required untranslated help strings can be translated (common editor or any relevant program) and the the `transfer` command can be repeated, so that the fresh translation is transtfered to UI. Thus, identical translation in the help and UI is secured.

The `upload` command uploads the modified files. If also help files were translated, then upload also them by `./epitrans.py -p help -l sk upload`.

### Other commands
`modified`: List modified files

`differences`: Show differences in modified files

`revert`: Revert modified files to the original state

## Updating
There is no special command to update the strings if they change on the server. Delete everything and download again.

## Other usage
The download and upload commands can be used to manage local translation by means of desktop programs (potrans, transifex, and with some effort perhap also OmegaT).

## Installation of dependencies
The script was written and tested in Linux and python3. It requires several common modules (polib, requests, filecmp, json) and the `curl` programm. The script probably runs also in the Windows Subsystem for Linux (Windows 10) and maybe also in other environments. In Linux the modules can be installed using `pip`. 


