# Weblate
Scripts related to translation of the LibreOffice user interface, help and other files. LibreOffice uses for translation the [Weblate](https://weblate.org) tool.
## etiptrans.py
A script to download, modify and upload LibreOffice translation subprojects (in Weblate called *slugs*)  from the [LibreOffice Weblate server](https://translations.documentfoundation.org/) by means of the Weblate's API.

On download the script creates a directory with two copies of each subproject's po file. One of them, starting by dot, is in Linux not visible in regular file viewing and serves as a backup, for example to cancel current changes.

Currently the following sub projects are supported:
* 'help': "libo_help-master",
* 'ui': "libo_ui-master",
* 'ui70': "libo_ui-7-0",
* 'ui64': "libo_ui-6-4",
* 'ui63': "libo_ui-6-3"

Abbreviations on the left are shortcuts used in the script commands. The slug names on the right are used as directory names.

Using the Weblate's web interface one translates the 'master' sub projects and translations are propagated to other related sub projects (libo_ui-master > libo_ui-7-0 etc.). This does not work when uploading po files using the Weblate's API, so one has to transfer translations between subprojects using this script (libo_ui-master > libo_ui-7-0 etc.) and then upload them separately.

### Using the script
#### Operating system and dependencies
The script was developed and tested in a Linux environment using Python3. Scenarios described below may require also other Linux specific tools.

It is likely that the script and related tools work equally well in WSL ([Windows subsystem for Linux](https://docs.microsoft.com/en-us/windows/wsl/install-win10)).

#### Run the Script
The scripts nas swithes and commands and should be run this way:

`etiptrans.py switches command`

for example, `etiptrans.py -h` displays a help.

#### Switches
Some switches apply to all commands, some switches are command specific.

Common switches are:

```
-h                this usage
-w site           Weblate site URL {taken from the WEBLATE_API_SITE environment variable}
-p project        Abbreviation of Weblate's subproject (slug) ['help', 'ui', 'ui70', 'ui64', 'ui63']
-k key            Weblate account key {taken from the WEBLATE_API_KEY environment variable}
-l lang_code      language code {taken from the WEBLATE_API_LANG environment variable}

```

When using `bash`, set the environment variables in the `.bashrc` file:
```
export WEBLATE_API_SITE=https://translations.documentfoundation.org/api/
export WEBLATE_API_KEY=vt6ttvT6t9T976t&^t76T76vt^tv7^Tv76tV6tv6t
export WEBLATE_API_LANG=sk
```
You can find your key in Weblate's GUI [Settings](https://translations.documentfoundation.org/accounts/profile/#api) (Your profile > Settings > API Access, the icon in the upper right corner).

Commands and their specific switches are described below. We assume that language is set to `sk`. Commands can be abbreviated to usually 2 letters.

### Download a subproject

`etiptrans.py -p ui download ` (default language: `sk`, taken from environment)

`etiptrans.py -p ui -l cz download ` (with specified language, in this case `cz`)

Downloads the `ui` subproject, creates directory `libo_ui-master/lang_code` with the po files.

Dowloading of individual files may fail. Usually a failure is detected and download is restarted. Sometimes, however, downloading hangs. In that case abort the script (CRTL-C) and restart it. Already downloaded po files will be skipped.

### Upload a subproject

`etiptrans.py -p ui upload ` (default language: `sk`)

`etiptrans.py -p ui -l cz upload ` (with specified language, in this case `cz`)

### View current changes
`etiptrans.py -p ui modified` lists modified files

`etiptrans.py -p ui diff` lists differences, for example:

```
Differences in  libo_ui-master/sk/sc/messages.po:
	_Show changes in spreadsheet```
       < _Zobraziť zmeny v zošite
	   > _Zobraziť zmeny v hárku
```
The line marked by `<` is the original, markred by `>` is the new version.

### Cancel current changes
`etiptrans.py -p ui reset`
All changes will be cancelled to the download state.

### Remove a subproject
Use system tools, e. g.:

`rm -rf libo_ui-master`

or

`rm -rf libo_ui-master/sk`

to remove only the `sk` language.

### Normalize string ending characters
Quite often a source string and translated string end with a different character. Weblate can detect some of these inconsistencies and lists them in the `Checks` column. They need to be fixed one-by-one, which is cumbersome.

To fix the problem, run
```
etiptrans.py -p ui fixchar
```
The command also removes double spaces and removes spaces before the `,` and `.` interpunction.

For example (run `etiptrans.py -p ui diff` to display changes):
```
'Line Spacing:'
	< 'Riadkovanie'
	> 'Riadkovanie:'
```
or
```
'Specifies additional sorting criteria. You can also combine sort keys.'
	< 'Určuje ďalšie kritériá zoraďovania. Zoraďovacie kľúče môžete kombinovať .'
	> 'Určuje ďalšie kritériá zoraďovania. Zoraďovacie kľúče môžete kombinovať.'
```
### Export glossary
A two column "Source<TAB>Translation" csv file is exported. It can be used, e. g., in OmegaT as a glossary (OmegaT then offers translation suggestions for substrings of a translated string equal to GUI items):
```
etiptrans -p ui glossary > output.csv
```
To use the glossary file in OmegaT, copy the resulting csv file to OmegaT's working directory (the 'glossary' subdirectory). It is necessary to change suffix of the file to .txt.

### Export translations
The goal is to export translated and/or untranslated messages to a csv file, which can be translated and imported back, used to find typos and translation conflicts or perhaps also for other purposes.

A csv file with 4 tab separated columns is exported:
`File name <TAB> KeyID <TAB> Source <TAB> Target`, for example:
```
libo_ui-master/sk/avmedia/messages.po	yTBHR	200%	200 %
```

To export translations run
```
etiptrans -p ui {switches} export > output.csv
```
Allowed switches are:

`-f`: export only conflicting translations (different translations for one source string)

`-r`: export only conflicting translations (reversed, two or several different source strings for one translation string)

`-t`: export only extended tooltips (<ahelp> in help, 'extended' in entry.msgctxt in ui, without the <ahelp> tags)


#### Basic Export
Use the following command:
```
etiptrans -p ui export
```
or
```
etiptrans -p ui -a export
```
The second version removes accelerators `–` and `~`

### Find and correct typos
Weblate does not have a tool to find typos. The proposed procedure consists of several steps: export strings, find typos by a spell checker and correct the typos by the `sed` editor.
1. Export all strings without accelerators

`etiptrans.py -p sk -a export >en_sk.csv`

Open the `en_sk.csv` file in LibreOfficedelete the column with English strings and save as `sk.csv`
1. Find typos
Run this horrible script:
```
cat sk.csv |tr " " "\n" | tr "/-" "\n"| tr "]" "." |sed -e "s/[.,\"()<*>=:;%?&'{}[]//g"|sed -e "s/[0-9\!\^„“#]//g"|sed -e "s/.*[a-Z][A-Z].*//"|sort|uniq|aspell -l sk list
```
The scripts breaks lines in single words (`tr " " "\n" | tr "/-" "\n"`), removes special characters (`tr "]" "." |sed -e "s/[.,\"()<*>=:;%?&'{}[]//g"|sed -e "s/[0-9\!\^„“#]//g"|sed -e "s/.*[a-Z][A-Z].*//">typos.txt`), finds unique words (`sort|uniq`) and finally uses the `aspell` spellchecker to find misspelled words.

The script was assembled in a trial-and-error way, maybe that there is a much nicer way, hoh to reach the same goal.
2. Correct typos
