#!/usr/bin/env python3
#https://github.com/WeblateOrg/weblate/issues/1476

# spellcheck translated messages
#cat ui_sk.csv |tr " " "\n" | tr "/-" "\n"| tr "]" "." |sed -e "s/[.,\"()<*>=:;%?&'{}[]//g"|sed -e "s/[0-9\!\^„“#]//g"|sed -e "s/.*[a-Z][A-Z].*//"|sort|uniq|aspell -l sk list

# edit all by sed
#for i in `find libo_ui-master -name [a-Z]\*.po`; do sed -i -f err-sel.sed $i; done


import sys, getopt, csv, re, time
import os, shutil, filecmp
from os import path
import ipdb
import json
import polib
from collections import defaultdict


def usage():
    global wsite, csv_import
    print()
    print("%s: Transfer extended tooltip string from the LibreOffice help translation files to UI files or vice versa"%sys.argv[0])
    print("Usage: ",sys.argv[0]+ " switches command")
    print("Switches:")
    print("\t-h                this usage")
    print("\t-v                be verbose")
    print("\t-p {ui|help}      project")
    print("\t-w site           Weblate site {%s}"%wsite)
    print("\t-k key            Weblate account key {taken from the WEBLATE_API_KEY environment variable}")
    print("\t-l lang_code      language code {%s}"%lang)
    print("Commands (with their specific switches):")
    print("\tdownload\tDownload translation files for the project specidied by the -p switch")
    print("\tmodified\tList modified files")
    print("\tdifferences\tShow differences in modified files")
    print("\trevert\t\tRevert modified files to the original state")
    print("\ttransfer\ttransfer existing translations of extended tooltips from another project")
    print("\t\t-n project        project to transfer translations from.")
    print("\t\t                  If transferring between 'ui' projects, tranfers are only between messages with identical KeyId.")
    print("\t\t                  If transferring between 'ui' and 'help' project, only tooltips are transferred.")
    print("\timport\t\timport translations from csv file (source<tab>target)")
    print("\t\t-c csv_file       csv file to import translations.")
    print("\t\t\t\t  Structure:")
    print("\t\t\t\t   source<tab>target    (replace all)")
    print("\t\t\t\t   source<tab>current_target<tab>new_target    (replace only specific translations)")
    print('\texport\t\texport unique messages in csv format to stdout  as "source","target" with stripped newlines.')
    print("\t\t-a                remove accelerator characters _ and ~")
    print("\t\t-f                export only conflicting translations (more than one msgstr for one msgid")
    print("\t\t-r                export only conflicting translations (reversed, more than one msgid for one msgstr")
    print("\t\t-t                export only extended tooltips (<ahelp> in help, 'extended' in entry.msgctxt in ui")
    print("\t\t-o                export extended tooltips, if they are translated on the 'other' side")
    print("\tfixchar\t\tfix trailing characters and extra spaces")
    print("\tupload\t\tupload modified files to server")
    print("\thelp\t\tThis help")


def parsecmd():
    global wsite, api_key, trans_project, lang, verbose, csv_import, remove_accelerators,conflicts_only, tooltips_only, conflicts_only_rev, translated_other_side,transfer_from
    try:
        opts, cmds = getopt.getopt(sys.argv[1:], "hvafrtow:p:k:l:c:n:", [])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err)) # will print something like "option -a not recognized")
        usage(desc)
        sys.exit(2)
    for o, a in opts:
        if o in ("-w"):
            wsite = a
        if o in ("-v"):
            verbose = True
        elif o in ("-p"):
            trans_project = a
        elif o in ("-k"):
            api_key = a
        elif o in ("-l"):
            lang = a
        elif o in ("-c"):
            csv_import = a
        elif o in ("-n"):
            transfer_from = a
        elif o in ("-a"):
            remove_accelerators = True
        elif o in ("-f"):
            conflicts_only = True
        elif o in ("-r"):
            conflicts_only_rev = True
        elif o in ("-t"):
            tooltips_only = True
        elif o in ("-o"):
            translated_other_side = True
        elif o in ("-h"):
            usage()
            sys.exit(0)
        else:
            assert False, "unhandled option"
    return cmds

#hidden dot files are used to back up the translation files
def get_dot_name(filename):
    return path.join(path.dirname(filename),"."+path.basename(filename))

def request_get(url):
    global token
    curl_command = f'curl -s -X GET -H "authorization: {token}" {url}'

    for rep in range(3):
        response=os.popen(curl_command).read()
        if not response:
            print(f"request_get: no response from server")
        elif "DOCTYPE html" in response:
            respname = "server-error-%s.html"%time.ctime().replace(" ","-")
            print(f"request_get: server problem, repeating the request. Server response saved to %s"%respname)   
            with open(respname, 'w') as f:
                f.write(response)
        elif "Bad Request" in response:
            print(f"request_get: curl commad corrupted (Bad Request)")
        elif "Bad Gateway" in response:
            print(f"request_get: curl commad failed (Bad Gateway)")
        elif "<html>" in response:
            print(f"request_get: curl commad corrupted (HTML response)")
        else:
            response_dir=json.loads(response)
            if 'detail' in response_dir:
                print(f"request_get: Commad failed ({response_dir['detail']})")
            else:
                return response_dir
    sys.exit(1)

def request_get_po(url):
    global token
    curl_command = f'curl -s -X GET -H "authorization: {token}" {url}'

    for rep in range(3):
        response=os.popen(curl_command).read()
        if not response:
            print(f"request_get: no response from server")
        elif "DOCTYPE html" in response:
            respname = "server-error-%s.html"%time.ctime().replace(" ","-")
            print(f"request_get: server problem, repeating the request. Server response saved to %s"%respname)   
            with open(respname, 'w') as f:
                f.write(response)
        elif "Bad Request" in response:
            print(f"request_get: curl commad corrupted")
        else:
            return response
    sys.exit(1)

def upload_file(fpath, furl):
    global token
    curl_command = f'curl -s -X POST -F overwrite=true -F file=@{fpath} -H "authorization: {token}" {furl}/'
    if verbose: print(f"Uploading file {fpath}")
    response=os.popen(curl_command).read()
    if not response:
        print(f"Upload_file: Probably incorrect file path ({fpath})")
        sys.exit(1)
    elif "DOCTYPE html" in response:
        print(f"Upload_file: Probably incorrect url path ({furl})")
        sys.exit(1)
    elif "Bad Request" in response:
        print(f"Upload_file: curl commad corrupted")
        sys.exit(1)
    else:
        response_dir=json.loads(response)
        if 'detail' in response_dir:
            print(f"Upload_file: Commad failed ({response_dir['detail']})")
            sys.exit(1)
        else:
            if verbose: print("  Result: %s"%response)

#get subproject slugs (slug: a machine name of a subproject in Weblate)
def get_subproject_slugs(project_name):
    global wsite, lang
    subprojects = request_get(f"{wsite}projects/{project_name}/components/")
    slugs=[]
    if verbose: print("Getting %d subprojects for %s:"%(subprojects['count'],project_name))
    cnt = len(subprojects['results'])
    while True:
        for sub in subprojects['results']:
            slugs.append(sub['slug'])
        if not subprojects['next']: break
        if verbose: print("  %3d/%3d  %s"%(cnt,subprojects['count'],subprojects['next']))
        subprojects = request_get(subprojects['next'])
        cnt += len(subprojects['results'])
    return slugs

def download_subprojects(project_name, slugs):
    global wsite, lang
    if verbose: print(f"Downloading translation files:")
    subprojects = request_get(f"{wsite}projects/{project_name}/components/")
    filenamedir={}
    for slug in slugs:
        filename, url = download_subproject_file(project_name, slug, lang)
        time.sleep(1)
        filenamedir[filename] = url
    return filenamedir

#create path, download file, create hidden file
def download_subproject_file(project_name, component_name, language_code):
    global wsite, token
    
    translations_url = f"{wsite}translations/{project_name}/{component_name}/{language_code}/"
    translations = request_get(translations_url)
    filename = path.join(project_name, translations['filename'])

    os.makedirs(path.dirname(filename), exist_ok=True)

    if os.path.exists(filename):
        if verbose: print(f"  {filename}: already downloaded, skipping")
        return filename, f"{translations_url}/file"
    if verbose: print(f"  {filename}")

    url = f"{translations_url}/file/"
    curl_command = f'curl -s -X GET -H "authorization: {token}" {url}'
    #for rep in range(3):
        #response=os.popen(curl_command).read()
    #ipdb.set_trace()
    po_data = request_get_po(url)
    with open(filename, 'w') as f:
        f.write(po_data)
    # create 'backup'of the file for reference - will never be changed
    shutil.copyfile(filename, get_dot_name(filename))
    return filename, f"{translations_url}/file"

def clear_translations_folder():
    for root, dirs, files in os.walk(f"{os.path.dirname(os.path.abspath(__file__))}/translations", topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

def get_modified_files(flist):
    filecmp.clear_cache()
    modlist=[]
    for fname in flist:
        if not filecmp.cmp(fname, get_dot_name(fname), shallow=False):
            modlist.append(fname)
    return modlist

def transfer_tooltips_ui_to_help():
    #load messages with ahelp strings from help
    ui_files = load_file_list(projects['ui'], lang)
    ahelp_dir ={}
    for ufile in ui_files:
        po = polib.pofile(ufile)
        for entry in po:
            if entry.obsolete: continue
            if "extended" in entry.msgctxt:
                ahelp_id = entry.msgid
                ahelp_str = entry.msgstr
                if ahelp_str:
                    ahelp_dir[ahelp_id] = [ahelp_str, ufile]
                else:
                    ahelp_dir[ahelp_id] = ["", ufile]
                pass
    #load help catalogs and find eventually translated nessages in ahelp_dir
    #ipdb.set_trace()
    csvWriter = csv.writer(sys.stdout, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    help_files = load_file_list(projects['help'], lang)
    modified_files = set()
    for hfile in help_files:
        changed = False
        po = polib.pofile(hfile)
        untranslated = po.untranslated_entries()
        for entry in untranslated:
            if entry.obsolete: continue
            if "ahelp" in entry.msgid:
                notags=re.sub(r"<[^<]*>","",entry.msgid)
                ahelp_id=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgid)[0]
                if ahelp_id in ahelp_dir and not entry.msgstr:
                    if ahelp_dir[ahelp_id][0]:   # is translated
                        entry.msgstr = entry.msgid.replace(ahelp_id,ahelp_dir[ahelp_id][0])
                        if notags==ahelp_id:
                            csvWriter.writerow(["Translated", entry.msgid, entry.msgstr])
                        else:
                            csvWriter.writerow(["Partially translated", entry.msgid, entry.msgstr])
                        changed = True
                    else:
                        csvWriter.writerow(["Untranslated", entry.msgid, entry.msgstr])
                    pass
        if changed:
            modified_files.add(hfile)
            po.save(hfile)

def transfer_translations_ui_to_ui():
    #load all messages, organize them by keyid
    ui_files = load_file_list(projects['ui'], lang)
    key_dir ={}
    for ufile in ui_files:
        po = polib.pofile(ufile)
        for entry in po:
            if entry.obsolete: continue
            # keyid is stored in entry.comment
            # store also msgid, to enable checking  
            key_dir[entry.comment] = [entry.msgid, entry.msgstr] 
    #load input catalogs
    csvWriter = csv.writer(sys.stdout, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    input_files = load_file_list(projects[trans_project], lang)
    modified_files = set()
    nmod=0
    for ifile in input_files:
        changed = False
        po = polib.pofile(ifile)
        for entry in po:
            if entry.obsolete: 
                continue
            if entry.comment in key_dir:
                if entry.msgid == key_dir[entry.comment][0]:
                    if entry.msgstr != key_dir[entry.comment][1]:
                        if entry.msgid != key_dir[entry.comment][0]:
                            csvWriter.writerow(["Conflict", entry.msgid, key_dir[entry.comment][0]])
                        csvWriter.writerow(["Replaced", entry.msgid+":", entry.msgstr+" >> "+ key_dir[entry.comment][1]])
                        #ipdb.set_trace()
                        entry.msgstr = key_dir[entry.comment][1]
                        changed=True
                        nmod += 1
                else:
                    csvWriter.writerow(["Conflict", entry.comment, entry.msgid, key_dir[entry.comment][0]])
        if changed:
            modified_files.add(ifile)
            po.save(ifile)

    if modified_files:
        print ("Number of transferred changes: %s"%nmod)
        print ("Modified files:")
        for mf in modified_files:
            print("  %s"%mf)

# export unique messages without newlines
# can be used for offline translation and subsequent import
# can be used as a glossary in external translation tools as OmegaT
def export_messages_to_csv(project):
    files = load_file_list(projects[project], lang)
    csvWriter = csv.writer(sys.stdout, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    mset=set()
    for file in files:
        po = polib.pofile(file)
        for entry in po:
            if entry.obsolete: continue

            if tooltips_only and project == "help":
                if not "<ahelp" in entry.msgid: continue
                eid=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgid)[0]
                estr=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgstr)
                estr = estr[0] if estr else ""
            elif tooltips_only and project == "ui":
                if not "extended" in entry.msgctxt: continue
                eid = entry.msgid
                estr = entry.msgstr
            else:
                eid = entry.msgid
                estr = entry.msgstr

            eid = eid.replace("\n",line_break_placeholder)
            estr = estr.replace("\n",line_break_placeholder)
            if remove_accelerators:
                eid = eid.replace("_","").replace("~","")
                estr = estr.replace("_","").replace("~","")
            if not eid+estr in mset:
                csvWriter.writerow([eid,estr])
                mset.add(eid+estr)

# export conflicting translations
def export_conflicting_messages_to_csv(project):
    files = load_file_list(projects[project], lang)
    csvWriter = csv.writer(sys.stdout, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    # dictionary with potentially conflicting entries (if len>1)
    conf_dict = defaultdict(list)
    # a set to detect repetitions
    repetitions = set()
    for fname in files:
        po = polib.pofile(fname)
        for entry in po:

            if entry.obsolete: continue
            if tooltips_only and not ("<ahelp" in entry.msgid or "extended" in entry.msgctxt): continue

            if trans_project == 'ui':
                #remove newlines, starting and ending spaces
                eid = entry.msgid.replace("\n",line_break_placeholder)
                estr = entry.msgstr.replace("\n",line_break_placeholder)
            else: #help
                if tooltips_only:
                    eid=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgid)
                    estr=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgstr)
                    if not estr: continue
                    eid=eid[0]
                    estr=estr[0]
                else:
                    eid=entry.msgid
                    estr=entry.msgstr
                #ipdb.set_trace()

            # ignore untranslated
            if not estr: continue
            
            if conflicts_only_rev:
                aux=eid
                eid=estr
                estr=aux
                #ipdb.set_trace()
                pass
            #remove accelerators
            if remove_accelerators:
                eid = eid.replace("_","").replace("~","")
                estr = estr.replace("_","").replace("~","")
            #add to the dictionary
            if eid+estr.lower() not in repetitions: #ignore case in estr when detecting conflicts
                repetitions.add(eid+estr.lower())
                if not eid in conf_dict:
                    conf_dict[eid].append(estr)
                elif estr not in conf_dict[eid]:
                    conf_dict[eid].append(estr)
    # export only those with more than one entry
    for eid in conf_dict:
        if len(conf_dict[eid]) > 1:
            for estr in conf_dict[eid]:
                csvWriter.writerow([eid,estr])

#export translated tooltips, if they are translated on the 'other' side
#useful if tooltips on the 'other' side (help) were of poor quality, but still transferred to ui
def export_etips_trans_help():
    #load messages with ahelp strings from help
    help_files = load_file_list(projects['help'], lang)
    ahelp_dir ={}
    for hfile in help_files:
        po = polib.pofile(hfile)
        for entry in po:
            if entry.obsolete: continue
            if "ahelp" in entry.msgid:
                ahelp_id=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgid)[0]
                ahelp_str=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgstr)
                if ahelp_str:
                    ahelp_dir[ahelp_id] = [ahelp_str[0], hfile]
                pass
    #load ui catalogs and find if they have translated counterpart in help
    csvWriter = csv.writer(sys.stdout, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    ui_files = load_file_list(projects['ui'], lang)
    for uifile in ui_files:
        po = polib.pofile(uifile)
        for entry in po:
            if not "extended" in entry.msgctxt: continue
            if entry.msgid in ahelp_dir and entry.msgstr:
                csvWriter.writerow([entry.msgid, entry.msgstr, uifile])

def strip_interpuct_end(txt, inp):
    while txt[-1] in inp and len(txt) > 1:
        txt = txt[:-1]
    return txt

# unifies message trailing chracters and removes extra space in a message
# the fixes were adjusted to the actual situation in the  Slovak translation
# prior to upload check the result using etiptrans.py -p ui diff
def fix_trailing_characters(project):
    files = load_file_list(projects[project], lang)
    modified_files = set()
    for file in files:
        changed = False
        po = polib.pofile(file)
        for entry in po:
            if not entry.msgstr or entry.obsolete:
                continue
            #remove trailing interpunction
            if entry.msgid in ["...", "'", ".", ":", "!"]:
                continue
            # add interpunction from msgid
            if entry.msgid[-3:] == "...":
                msgstr = strip_interpuct_end(entry.msgstr,".…:")
                entry.msgstr = msgstr+"..."
                changed = True
            elif entry.msgid[-1] == "…":
                msgstr = strip_interpuct_end(entry.msgstr,".…")
                entry.msgstr = msgstr+"..."
                changed = True
            elif entry.msgid[-1] in ".":
                msgstr = strip_interpuct_end(entry.msgstr,",. !")
                entry.msgstr = msgstr+entry.msgid[-1]
                changed = True
            elif entry.msgid[-1] in ":":
                msgstr = strip_interpuct_end(entry.msgstr," :")
                entry.msgstr = msgstr+entry.msgid[-1]
                changed = True
            elif entry.msgid[-1] in "!":
                msgstr = strip_interpuct_end(entry.msgstr," !.")
                entry.msgstr = msgstr+entry.msgid[-1]
                changed = True
            elif entry.msgid[-1] in " ":
                msgstr = strip_interpuct_end(entry.msgstr," ")
                entry.msgstr = msgstr+entry.msgid[-1]
                changed = True
            else:
                if entry.msgstr[-1] in ".: ":
                    if entry.msgstr[-3:] == '...':
                        entry.msgstr = entry.msgstr[:-3]
                    else:
                        entry.msgstr = entry.msgstr[:-1]
                    changed = True
                    pass
            # fix spaces
            if "  " in entry.msgstr:
                entry.msgstr = entry.msgstr.replace("  ", " ")
                changed = True
            if " , " in entry.msgstr:
                entry.msgstr = entry.msgstr.replace(" , ", ", ")
                changed = True
            if entry.msgstr[0] == " " and entry.msgid[0] != " ":
                entry.msgstr = entry.msgstr[1:]
                changed = True
        if changed:
            modified_files.add(file)
            po.save(file)
    if modified_files:
        print ("Modified files:")
        for mf in modified_files:
            print("  %s"%mf)



def import_translations(project):
    with open(csv_import, 'rt', encoding='utf-8') as ifile:
        reader = csv.reader(ifile, delimiter='\t', quotechar='"',quoting=csv.QUOTE_MINIMAL)
        import_dir ={}
        ncols=0
        for row in reader:
            if ncols == 0:
                ncols = len(row)
            if len(row) != ncols:
                print(f"\n%s import error: inconsistent number of columns at %s."%(sys.argv[0], row))
                sys.exit(1)
            import_dir[row[0]] = row[1:]

    #load ui catalogs and find eventually translated messages in import_dir
    ui_files = load_file_list(projects[project], lang)
    modified_files = set()
    ntrans=0
    for uifile in ui_files:
        changed = False
        po = polib.pofile(uifile)
        for entry in po:
            if entry.obsolete: continue
            #if entry.msgid in import_dir and not entry.msgstr:
            # 2 columns, just replace, useful if no translation exists
            if ncols == 2:
                if entry.msgid in import_dir:
                    if import_dir[entry.msgid] and not entry.msgstr:
                        print("  New translation: %s"%(entry.msgid))
                    else:
                        print("  Replaced translation: %s"%(entry.msgid))
                    #ipdb.set_trace()
                    entry.msgstr = import_dir[entry.msgid][0]
                    changed = True
                    ntrans += 1
            # 3 columns, replace matching translation
            else :
                if entry.msgid in import_dir:
                    if entry.msgstr == import_dir[entry.msgid][0]:
                        print("  Replaced translation: %s"%(entry.msgid))
                        #ipdb.set_trace()
                        entry.msgstr = import_dir[entry.msgid][1]
                        changed = True
                        ntrans += 1
        if changed:
            modified_files.add(uifile)
            po.save(uifile)

    if modified_files:
        print ("Number of imported translations: %s"%ntrans)
        print ("Modified files:")
        for mf in modified_files:
            print("  %s"%mf)

def transfer_tooltips_help_to_ui():
    #load messages with ahelp strings from help
    help_files = load_file_list(projects['help'], lang)
    ahelp_dir ={}
    for hfile in help_files:
        po = polib.pofile(hfile)
        for entry in po:
            if entry.obsolete: continue
            if "ahelp" in entry.msgid:
                ahelp_id=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgid)[0]
                ahelp_str=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgstr)
                if ahelp_str:
                    ahelp_dir[ahelp_id] = [ahelp_str[0], hfile]
                else:
                    ahelp_dir[ahelp_id] = ["", hfile]
                pass
    #load ui catalogs and find eventually translated nessages in ahelp_dir
    ui_files = load_file_list(projects['ui'], lang)
    modified_files = set()
    for uifile in ui_files:
        changed = False
        po = polib.pofile(uifile)
        untranslated = po.untranslated_entries()
        for entry in untranslated:
            if entry.msgid in ahelp_dir and not entry.msgstr:
                #ipdb.set_trace()
                if ahelp_dir[entry.msgid][0]:
                    #ipdb.set_trace()
                    entry.msgstr = ahelp_dir[entry.msgid][0]
                    print("  Translated: %s"%(entry.msgid))
                    changed = True
                else:
                    print("Untranslated in  '%s': '%s'"%(ahelp_dir[entry.msgid][1], entry.msgid))
                pass
        if changed:
            modified_files.add(uifile)
            po.save(uifile)

    if modified_files:
        print ("Modified files:")
        for mf in modified_files:
            print("  %s"%mf)

def load_file_list(trans_project, lang):
    with open(path.join(trans_project, lang, 'files.json'), "r") as fp:
        proj_files = json.load(fp)
    return proj_files

projects = {
        'help': "libo_help-master",
        'ui': "libo_ui-master",
        'ui70': "libo_ui-7-0",
        'ui64': "libo_ui-6-4",
        'ui63': "libo_ui-6-3"
        }
trans_project=None

pname = "libo_help-master"
api_key = os.environ.get('WEBLATE_API_KEY')
lang = os.environ.get('WEBLATE_API_LANG')
wsite = f"https://translations.documentfoundation.org/api/"
verbose = False
csv_import=""
remove_accelerators=False
conflicts_only=False
conflicts_only_rev=False
tooltips_only=False
translated_other_side=False
transfer_from=""

#placeholder to mark line breaks in export
line_break_placeholder="<ASDFGHJK>"

def main():
    global token

    #response = http.get("https://en.wikipedia.org/w/api.php")
    action = parsecmd()
    if action: action=action[0][:2]

    if action != "he" and not trans_project in projects:
        print(f"\n%s error: translation project not specified."%sys.argv[0])
        usage()
        sys.exit(1)

    if not api_key:
        print("\n%s error: no API key"%sys.argv[0])
        print("  Set environment variable WEBLATE_API_KEY or use the -k switch.") 
        usage()
        sys.exit(1)
    token = 'Token '+api_key

    if not lang:
        print("\n%s error: no API key"%sys.argv[0])
        print("  Set environment variable WEBLATE_API_LANG or use the -l switch.") 
        usage()
        sys.exit(1)

    if action == "do":  #download
        subproject_slugs = get_subproject_slugs(projects[trans_project])
        proj_files = download_subprojects(projects[trans_project], subproject_slugs)
        #write file paths and urls to a json file
        with open(path.join(projects[trans_project], lang, 'files.json'), "w") as fp:
            json.dump(proj_files, fp, sort_keys=True, indent=4)
        pass

    elif action == "mo":    #modified
        proj_files = load_file_list(projects[trans_project], lang)
        modified_files = get_modified_files(proj_files.keys())
        print("Modified files in %s:"%projects[trans_project])
        for mfile in modified_files:
            print("\t%s"%mfile)
        pass

    elif action == "di":    #differences
        proj_files = load_file_list(projects[trans_project], lang)
        modified_files = get_modified_files(proj_files.keys())
        for mfile in modified_files:
            print("Differences in  %s:"%mfile)
            #load original messagaes
            po = polib.pofile(get_dot_name(mfile))
            orig_dir ={}
            num = 0
            for entry in po:
                orig_dir["%04d %s"%(num,entry.msgid)] = entry.msgstr
                num += 1

            #compare modified messagaes
            po = polib.pofile(mfile)
            num = 0
            for entry in po:
                if orig_dir["%04d %s"%(num,entry.msgid)] != entry.msgstr:
                    print("\t'%s'"%entry.msgid)
                    print("\t< '%s'"%orig_dir["%04d %s"%(num,entry.msgid)])
                    print("\t> '%s'"%entry.msgstr)
                    print()
                num += 1

    elif action == "re":    #revert
        proj_files = load_file_list(projects[trans_project], lang)
        modified_files = get_modified_files(proj_files.keys())
        if modified_files:
            print("Reverting files:")
            for fname in modified_files:
                print("\t%s"%fname)
                shutil.copyfile(get_dot_name(fname), fname)
        else:
            print("No files to revert.")

    elif action == "tr":    #transfer translations
        if trans_project == "ui" and transfer_from == "help":
            transfer_tooltips_help_to_ui()
        elif trans_project == "help" and transfer_from == "ui":
            transfer_tooltips_ui_to_help()
        elif trans_project[:2] == "ui" and transfer_from == "ui":
            transfer_translations_ui_to_ui()
        else:
            print("\n%s error: You can transfer translations only from 'help' to 'ui', from 'ui' to 'help' and from 'ui' to other 'ui' projects."%sys.argv[0])
            print("\n%s error: You wanted to transfer translations from '%s' to '%s'."%(sys.argv[0], transfer_from, trans_project))
            usage()

    elif action == "im":    #import translations from csv file (-c switch)
        if not csv_import:
            print("\n%s import error: specify a csv file with translation'."%sys.argv[0])
            usage()
        else:
            if trans_project == "ui":
                import_translations("ui")
            else:
                import_translations("help")

    elif action == "up":    #upload
        proj_files = load_file_list(projects[trans_project], lang)
        modified_files = get_modified_files(proj_files.keys())
        for fpath in modified_files:
            upload_file(fpath, proj_files[fpath])
            #rewrite the old dot file
            shutil.copyfile(fpath, get_dot_name(fpath))
        pass

    elif action == "ex":    #export
        if conflicts_only or conflicts_only_rev:
            export_conflicting_messages_to_csv(trans_project)
        elif translated_other_side:
            if trans_project == "ui":
                export_etips_trans_help()
            else:
                print("\n%s: not implemented yet for help'."%sys.argv[0])
        else:
            export_messages_to_csv(trans_project)

    elif action == "fi":    #fix trailing characters
        fix_trailing_characters(trans_project)

    elif action == "he":    #help
        print("he")
        usage()
        pass

    else:
        print("\n%s error: unspecified action '%s'."%(sys.argv[0],action))
        usage()


if __name__ == "__main__":
    main()
