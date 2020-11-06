#!/usr/bin/env python3
import sys, getopt, csv, re, time, subprocess, imageio, glob
import pyscreenshot as ImageGrab
import ipdb
import numpy as np
import matplotlib.pyplot as plt
import scipy.ndimage as ndi
from os import path
import json
import polib

def plot(data):
    # data is tuple of lists
    for d in data:
        plt.plot(range(len(d)),d)
    plt.show()

def _disp(iimg, label = None, gray=False):
    """ Display an image using pylab
    """
    import pylab, matplotlib
    #matplotlib.interactive(True)
    matplotlib.pyplot.imshow(iimg, interpolation='none')

def disp(iimg, label = None, gray=False):
    """ Display an image using pylab """
    plt.figure()
    plt.imshow(iimg)
    plt.show()

def get_dialog(im, frame_density=196, frame_thickness=3):
    #ipdb.set_trace()
    #ipdb.set_trace()
    dialog_mask = im[...,0]==frame_density
    dialog_mask = ndi.binary_opening(dialog_mask,np.ones((frame_thickness,frame_thickness)))
    if dialog_mask.sum() == 0:
        return None
    nz = np.nonzero(dialog_mask)
    return im[nz[0].min():nz[0].max(),nz[1].min():nz[1].max()] 

def grab_screen(ui_file):
    subp = subprocess.Popen([glade_bin, ui_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3.0)
    #print('proc1 = ', subp.pid)
    im = ImageGrab.grab()
    subprocess.Popen.kill(subp)
    return(np.array(im))

def load_file_list(trans_project, lang):
    with open(path.join(trans_project, lang, 'files.json'), "r") as fp:
        proj_files = json.load(fp)
    return proj_files

# key_id is in one of the rows of poentry.comment (usually the first)
def get_key_id_code(poentry):
    key_id = poentry.comment.split("\n")
    if len(key_id) == 1:
        key_id=key_id[0]
    else:
        lenghts = np.nonzero([len(k)==5 for k in key_id])
        key_id=key_id[lenghts[0][0]]
    return key_id

projects = {
        'help': "libo_help-master",
        'ui': "libo_ui-master",
        'ui70': "libo_ui-7-0",
        'ui64': "libo_ui-6-4",
        'ui63': "libo_ui-6-3"
        }
lang = "sk"

def build_dirs():
    ui_files = load_file_list(projects['ui'], lang)
    trans_dir ={}
    for ufile in ui_files:
        po = polib.pofile(ufile)
        for entry in po:
            if entry.obsolete: continue
            key=get_key_id_code(entry)
            trans_dir[entry.msgctxt]=[key, entry.msgid, entry.msgstr]
    return trans_dir


def process_ui_file(ui_file):
    try:
        with open(ui_file) as f:
            key_text = f.read()
    except Exception as error: 
        print("%s:"%sys.argv[0], error)
        sys.exit(0)
    lang_text = key_text


    #<property name="label" translatable="yes" context="fmsearchdialog|flOptions">Settings</property>
    #<item translatable="yes" context="hatchpage|linetypelb">Single</item>
    #<property name="label" translatable="yes" context="optsavepage|odfwarning_label" comments="EN-US, the term 'extended' must not be translated.">Not using ODF 1.3 Extended may cause information to be lost.</property>
    prop_re=r'(<property name="[^"]*" translatable="yes" context="[^"]*">[^<]*</property>)'
    #prop_re=r'<property[^>]*>[^<]*</property>'
    #prop_re=r'(<property name="[^"]*" translatable="yes"[^>]*>[^<]*</property>)'
    #prop_re=r'(<property name="[^"]*" translatable="yes"[^>]*>[^<]*</property>)'
    translatables = re.findall(prop_re, key_text)

    #trans_re=r'<property name="[^"]*" translatable="yes" context="([^"]*)">([^<]*)</property>'
    trans_re=r'context="([^"]*)"[^>]*>([^<]*)</property>'
    for tr_in in translatables:
        if not "context=" in tr_in: continue
        if 'translatable="no"' in tr_in: continue
        if "This release was supplied by" in tr_in:
            ipdb.set_trace()
            pass
        trans = re.findall(trans_re, tr_in)
        if not trans:
            ipdb.set_trace()
            continue
            pass
        trans=trans[0]
        if not trans[0] in trans_dir:
            exportCSVWriter.writerow([ui_file]+ ["%s not found"%trans[0]])
            continue

        act_val=trans_dir[trans[0]]
    
        tr_key = tr_in.replace(trans[1],"%s (%s)"%(trans[1], act_val[0]))
        key_text = key_text.replace(tr_in, tr_key)
    
        tr_lang = tr_in.replace(trans[1],act_val[2])
        lang_text = lang_text.replace(tr_in, tr_lang)
        # export 
        exportCSVWriter.writerow([ui_file]+ act_val) 

    # create modified ui files and render their content
    fpath = ui_file[:-3]
    fname = "%s-key.ui"%fpath
    with open(fname, "w") as f:
        f.write(key_text)
    dialog_key=get_dialog(grab_screen(fname))
    if dialog_key is None: 
        print("UI error: %s"%fname, file=sys.stderr)
        return
    
    fname = "%s-%s.ui"%(fpath,lang)
    with open(fname, "w") as f:
        f.write(lang_text)
    dialog_lang=get_dialog(grab_screen(fname))
    if dialog_lang is None: 
        print("UI error: %s"%fname, file=sys.stderr)
        return


    #concatenate to one image, expect non-equal height
    #ipdb.set_trace()
    height = max(dialog_key.shape[0], dialog_lang.shape[0])
    if dialog_key.shape[0] < height:
        strip = dialog_key[:height-dialog_key.shape[0]].copy()
        strip[:]=255
        dialog_key=np.concatenate((dialog_key,strip))
    else:
        strip = dialog_lang[:height-dialog_lang.shape[0]].copy()
        strip[:]=255
        dialog_lang=np.concatenate((dialog_lang,strip))
    dialog = np.concatenate((dialog_key, dialog_lang), axis=1)
    imageio.imwrite("%s.png"%fpath, dialog)


def usage():
    global wsite, csv_import, projects
    proj_abb = [k for k in projects.keys()]
    print()
    print("%s: render LibreOffice ui files"%sys.argv[0])
    print("Usage: ",sys.argv[0]+ " switches directory")
    print("Switches:")
    print("\t-h                this usage")
    print("\t-l lang_code      language code {taken from the WEBLATE_API_LANG environment variable}")


def parsecmd():
    global lang
    try:
        opts, ddir = getopt.getopt(sys.argv[1:], "hl:", [])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err)) # will print something like "option -a not recognized")
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ("-l"):
            lang = a
        elif o in ("-h"):
            usage()
            sys.exit(0)
        else:
            assert False, "unhandled option"
    return ddir


ui_file="soffice.cfg/vcl/ui/moreoptionsdialog.ui"
ui_file="soffice.cfg/cui/ui/colorpickerdialog.ui"
glade_bin="/snap/bin/glade"

in_files = parsecmd()

trans_dir = build_dirs()

exportCSVWriter = csv.writer(sys.stdout, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
exportCSVWriter.writerow(['File name', 'KeyID', 'Source', 'Target'])

for in_file in in_files:
    if in_file[-3:] == ".ui":
        ui_files = [in_file]
    else:
        ui_files=glob.glob(in_file+"/ui/*.ui")
    for ui_file in ui_files:
        if "-key.ui" in ui_file or "-%s.ui"%lang in ui_file: continue
        process_ui_file(ui_file)

