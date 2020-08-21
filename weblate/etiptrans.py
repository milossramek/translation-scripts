#!/usr/bin/env python3
#https://github.com/WeblateOrg/weblate/issues/1476

import sys, getopt, csv, re, time
import os, shutil, filecmp
from os import path
import ipdb
import json
import polib


def usage():
    global wsite
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
    print("Commands:")
    print("\tdownload\tDownload translation files for the project specidied by the -p switch")
    print("\tmodified\tList modified files")
    print("\tdifferences\tShow differences in modified files")
    print("\trevert\t\tRevert modified files to the original state")
    print("\ttransfer\ttransfer existing translations of extended tooltips from the other project")
    print("\tupload\t\tupload modified files to server")
    print("\thelp\t\tThis help")


def parsecmd():
    global wsite, api_key, trans_project, lang, verbose
    try:
        opts, cmds = getopt.getopt(sys.argv[1:], "hvw:p:k:l:", [])
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
            print(f"request_get: curl commad corrupted")
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
    help_files = load_file_list(projects['help'], lang)
    modified_files = set()
    for hfile in help_files:
        changed = False
        po = polib.pofile(hfile)
        untranslated = po.untranslated_entries()
        for entry in untranslated:
            if "ahelp" in entry.msgid:
                ahelp_id=re.findall(r"<ahelp[^>]*>(.*)</ahelp>",entry.msgid)[0]
                if ahelp_id in ahelp_dir and not entry.msgstr:
                    if ahelp_dir[ahelp_id][0]:   # is translated
                        entry.msgstr = entry.msgid.replace(ahelp_id,ahelp_dir[ahelp_id][0])
                        print("  Translated: %s"%(ahelp_id))
                        changed = True
                    else:
                        print("Untranslated in  '%s': '%s'"%(ahelp_dir[ahelp_id][1], ahelp_id))
                    pass
        if changed:
            modified_files.add(hfile)
            po.save(hfile)

    if modified_files:
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
        'ui': "libo_ui-master"
        }
trans_project=None

pname = "libo_help-master"
api_key = os.environ.get('WEBLATE_API_KEY')
wsite = f"https://translations.documentfoundation.org/api/"
verbose = False
lang="sk"

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
                    print("\t%s"%entry.msgid)
                    print("\t< %s"%orig_dir["%04d %s"%(num,entry.msgid)])
                    print("\t> %s"%entry.msgstr)
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

    elif action == "tr":    #transfer tooltips
        if trans_project == "ui":
            transfer_tooltips_help_to_ui()
        else:
            transfer_tooltips_ui_to_help()

    elif action == "up":    #upload
        proj_files = load_file_list(projects[trans_project], lang)
        modified_files = get_modified_files(proj_files.keys())
        for fpath in modified_files:
            upload_file(fpath, proj_files[fpath])
            #rewrite the old dot file
            shutil.copyfile(fpath, get_dot_name(fpath))
        pass

    elif action == "he": 
        print("he")
        usage()
        pass

    else:
        print("\n%s error: unspecified action '%s'."%(sys.argv[0],action))
        usage()


if __name__ == "__main__":
    main()
