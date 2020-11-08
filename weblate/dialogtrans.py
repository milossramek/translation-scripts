#!/usr/bin/env python3
import sys, os, getopt, csv, re, time, subprocess, imageio, glob
import pyscreenshot as ImageGrab
import ipdb
import numpy as np
import matplotlib.pyplot as plt
import scipy.ndimage as ndi
from collections import defaultdict
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
    try:
        with open(path.join(trans_project, lang, 'files.json'), "r") as fp:
            proj_files = json.load(fp)
    except Exception as error: 
        print("%s:"%sys.argv[0], error)
        print("\t Download the ui/%s project first using the potrans.py tool"%lang)
        sys.exit(0)
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
    trans_dir = defaultdict(list)
    for ufile in ui_files:
        po = polib.pofile(ufile)
        for entry in po:
            if entry.obsolete: continue
            key=get_key_id_code(entry)
            trans_dir[entry.msgctxt].append([key, entry.msgid, entry.msgstr])
    return trans_dir


# create two new versions of an ui_file: 
# one with appended keu_id to a translateble string and one with transleted translatable string
def process_ui_file(ui_file):
    try:
        with open(ui_file) as f:
            ui_text = f.read()
    except Exception as error: 
        print("%s:"%sys.argv[0], error) 
        sys.exit(0)
    #lang_text: ui with strings translated to 'lang'
    #ui_text: key_id will be appended to original strings
    lang_text = ui_text


    #find translatable 'property' strings
    #<property name="label" translatable="yes" context="installforalldialog|yes">_Only for me</property>
    #<property name="AtkObject::accessible-name" translatable="yes" comments="This string is used by the eyedropper dialog to denote a color in an image that will be replaced by another color." context="dockingcolorreplace|cbx1-atkobject">Source Color 1</property>
    prop_re=r'(<property name="[^"]*" translatable="yes" [^<]*</property>)'
    translatables = re.findall(prop_re, ui_text)

    context_re=r'context="([^"]*)"[^>]*>([^<]*)</property>'
    for trans_in in translatables:
        #if not "context=" in trans_in: continue
        trans = re.findall(context_re, trans_in)
        if not trans:
            ipdb.set_trace()
            continue
            pass
        trans=trans[0]
        #trans: (context, string)
        #('installforalldialog|InstallForAllDialog', 'For whom do you want to install the extension?')
        if not trans[0] in ui_translations_dir:
            exportCSVWriter.writerow([ui_file]+ ["%s not found in UI translation"%trans[0]])
            continue

        #if we happen to have are two or more strings with the same 'context', choose the right one
        if len(ui_translations_dir[trans[0]]) > 1:
            for val in ui_translations_dir[trans[0]]:
                if val[1] == trans[1]:
                    act_val = val
                    break
        else:
            act_val=ui_translations_dir[trans[0]][0]
    
        # modify ui_text and lang_text
        tr_key = trans_in.replace(trans[1],"%s (%s)"%(trans[1], act_val[0]))
        ui_text = ui_text.replace(trans_in, tr_key)
    
        tr_lang = trans_in.replace(trans[1],act_val[2])
        lang_text = lang_text.replace(trans_in, tr_lang)
        # export 
        exportCSVWriter.writerow([ui_file]+ act_val) 

    # create modified ui files and render their content
    fpath = ui_file[:-3]
    fname = "%s-key.ui"%fpath
    with open(fname, "w") as f:
        f.write(ui_text)
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


    #concatenate rendered dialogs to one image and save to png file, expect non-equal height/width
    height = max(dialog_key.shape[0], dialog_lang.shape[0])
    width = max(dialog_key.shape[1], dialog_lang.shape[1])
    if height > 0.7*width:
        # concatenate horizontally
        if dialog_key.shape[0] < height:
            strip = dialog_key[:height-dialog_key.shape[0]].copy()
            strip[:]=255
            dialog_key=np.concatenate((dialog_key,strip))
        else:
            strip = dialog_lang[:height-dialog_lang.shape[0]].copy()
            strip[:]=255
            dialog_lang=np.concatenate((dialog_lang,strip))
        dialog = np.concatenate((dialog_key, dialog_lang), axis=1)
    else:
        # concatenate vertically
        if dialog_key.shape[1] < width:
            strip = dialog_key[:,:width-dialog_key.shape[1]].copy()
            strip[:]=255
            dialog_key=np.concatenate((dialog_key,strip), axis=1)
        else:
            strip = dialog_lang[:,:width-dialog_lang.shape[1]].copy()
            strip[:]=255
            dialog_lang=np.concatenate((dialog_lang,strip), axis=1)
        dialog = np.concatenate((dialog_key, dialog_lang), axis=0)
    imageio.imwrite("%s.png"%fpath, dialog)


def usage():
    global wsite, csv_import, projects
    print()
    print("%s: render LibreOffice ui files"%sys.argv[0])
    print("Usage: ",sys.argv[0]+ " switches directory")
    print("Switches:")
    print("\t-h                this usage")
    print("\t-l lang_code      language code {taken from the WEBLATE_API_LANG environment variable}")
    print()
    print("\tThe procedure:")
    print("\t1. Copy the 'libreofficedevX.Y/share/config/soffice.cfg' directory here")
    print("\t2. Download the weblate ui project using the 'potrans.py -p ui down' tool here" )
    print("\t3. Run this script by '%s  soffice.cfg/xxx > trans.csv'"%sys.argv[0])
    print("\t4. Check the png renderings in soffice.cfg/xxx/ui, modify translations in trans.csv")
    print("\t5. Import trans.csv by 'potrans.py -p ui -c trans.csv im'")
    print("\t6. Upload modified translation by 'potrans.py -p ui up'")


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
glade_bin = os.environ.get('WEBLATE_GLADE_BIN')
lang = os.environ.get('WEBLATE_API_LANG')

in_files = parsecmd()

ui_translations_dir = build_dirs()

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

