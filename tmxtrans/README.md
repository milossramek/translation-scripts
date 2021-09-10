# tmxtrans.py
A script to translate "untranslated" messages of a tmx file by using API of the [deepl](https://www.deepl.com/) translation service.

An untranslatd tmx file can be created by, for example, the [OmegaT](https://www.omegat.org/)  CAT tool using a command:
```
java -jar /path/to/OmegaT.jar /path/to/project --mode=console-createpseudotranslatetmx --pseudotranslatetmx=untranslated.tmx

```
The `untranslated.tmx` file contains all strings from all files, which are in the `/path/to/project/source` directory.

In order to not to translate already translated strings, the script can load OmegaT's translation memory from the `omegat/project_save.tmx` file.
## Using the script

### Operating system and dependencies
The script was developed and tested in a Linux environment using Python 3.

It is likely that the script works equally well in WSL ([Windows subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/install-win10)).

The script has the following dependencies: `deepl`, `copy` and `lxml`. The ca be installed, e. g., by
```
pip install deepl
```

### Setting of environment variables

When using `bash`, set the environment variables in the `.bashrc` file:

```
export TMXTRANS_API_KEY=khdpxiu4yrcp4w8ubvt;o4inaoitn;igj;5ew
export TMXTRANS_TARGET_LANG=sk
export TMXTRANS_OMEGAT_PROJECT=/home/.....
```

To be loaded, log out or open a new terminal.

To get the Deepl key, create first a "DeepL API Free" account at https://www.deepl.com/pro?cta=menu-plans. Then, you get the key from https://www.deepl.com/docs-api/accessing-the-api/.

### Run the Script
The scripts should be run this way:

`tmxtrans.py switches`

for example, `tmxtrans.py -h` displays a short help.

### Switches
Common switches are:

```
	-k key           Deepl account key {taken from the TMXTRANS_API_KEY environment variable}
	-l lang_code     Language to translate to {taken from the TMXTRANS_TARGET_LANG environment variable}
	-p path          Path of the omegat project {taken from the TMXTRANS_OMEGAT_PROJECT environment variable}
	-i input_file    Input tmx file. Default: in.tmx
	                 The file can be created using
	                 java -jar /path/to/OmegaT.jar /path/to/project --mode=console-createpseudotranslatetmx --pseudotranslatetmx=in.tmx
	-o output_file   translated output file
	-h               this usage
```
If all environment variables are set, run the following:
```
tmxtrans.py -i in.tmx -o out.tmx
```

### Restarting translation
The script saves the output file after every 1000 processed strings. The output file contains all translated and also untranslated strings. Thus, in the case the script crashes, it can be restarted by using the original output file as input:
```
tmxtrans.py ..switches... -i out.tmx -o out1.tmx
```

### Using the translated tmx file
The translated tmx file should be copied to the `tm` subdirectory of the omegat project.
