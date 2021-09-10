#! /usr/bin/python
# -*- coding: utf-8 -*-
import sys, getopt, os, json, re, csv
from collections import defaultdict
from lxml import etree
from copy import deepcopy
from ipdb import set_trace as trace
import deepl

#java -jar /opt/OmegaT_4.3.2_Linux_64/OmegaT.jar /path_to_project --mode=console-createpseudotranslatetmx --pseudotranslatetmx=output.tmx

#ipdb
class Trans():
    def __init__(self, lang, api_key, omegat_project = None, glossary = None):
        self.targetlang = lang
        self.translator = deepl.Translator(api_key) 

        # load tmx with existing translations
        self.translated = {}
        if omegat_project:
            self.translated = self.load_tmx(f"{omegat_project}/omegat/project_save.tmx")
        
        # load tmx with existing translations
        self.glossary = {}
        if glossary:
            self.glossary = self.loadCSV(glossary)
        
    #fix problems in the translations
    def fix(self, src, tgt):
        # simple fixes
        tgt = tgt.replace("- ", "– ")
        tgt = tgt.replace(" -", " –")

        #fixes depending on src content
        if not '"' in src and '"' in tgt:
            #opening quote
            tgt = re.sub(r'"([^ ).,])', r'„\1',tgt) 
            #closing quote
            tgt = re.sub(r'([^ (])"', r'\1“',tgt) 
        accs = ["Ctrl+", "Alt+", "Shift+", "Ctrl + ", "Alt + ", "Shift + "]
        for acc in accs:
            if acc in src and not acc in tgt:
                tacc = acc.replace(" ","").replace("+","") + " "
                tgt = tgt.replace(tacc, acc)
        return tgt

    def translate_ui(self, src):
        items = re.findall(r"<f[0-9]>([^<]*)</f[0-9]>", src)
        # create list of ui items
        ui_items = []
        for item in items:
            for part in item.split(" > "):
                print(f"UI:   {part}")
                if part in self.glossary and len(self.glossary[part]) == 1:
                    ui_items.append(part)
                    print(f"      {self.glossary[part][0]}")
        placeholders = {}
        for nn, item in enumerate(sorted(ui_items, key=len)[::-1]):
        #for nn, item in enumerate(ui_items):
            placeholder = "PL%03d"%nn
            src = src.replace(item, placeholder)
            placeholders[placeholder] = self.glossary[item][0]
        return src, placeholders

    def translate(self, src):
        if src in self.translated:
            return None
        else:
            # translate ui items (replaced by placeholders in translation_ui)
            translation_ui, placeholders = self.translate_ui(src)
            # translate all
            translation = self.translator.translate_text(translation_ui, target_lang=self.targetlang).text
            # remove placeholders
            for ph in placeholders:
                translation = translation.replace(ph, placeholders[ph])
            #fix common  problems and return
            return self.fix(src, translation)

    def load_tmx(self, fname, reversed=False):
        tree = etree.parse(fname)
        root = tree.getroot()
        mdict = {}
        for iitem in tree.xpath('//tu'):
            item = deepcopy(iitem)
            try:
                src, tgt = item.xpath("//seg")
                if reversed:
                    mdict[tgt.text] = src.text
                else:
                    mdict[src.text] = tgt.text
            except:
                print("except")
        return mdict 

    def loadCSV(self,ifile):
        # get information about the slices first
        #ipdb.set_trace()
        items = defaultdict(list)
        with open(ifile, 'rt', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile, delimiter='\t', quotechar='"',quoting=csv.QUOTE_MINIMAL)
            for row in reader:
                if len(row) > 0: 
                    items[row[0]].append(row[1])
        return items

def isTU(item):
    if item.tag == "tu":
        return True
    else:
        return False

def usage():
    global iname, oname, gname
    print("%s: Translate OmegaT strings from English using the deepL service"%sys.argv[0])
    print("\t-k key           Deepl account key {taken from the TMXTRANS_API_KEY environment variable}")
    print("\t-l lang_code     Language to translate to {taken from the TMXTRANS_TARGET_LANG environment variable}") 
    print("\t-p path          Path of the omegat project {taken from the TMXTRANS_OMEGAT_PROJECT environment variable}") 
    print("\t-i input_file    Input tmx file. Default: %s"%iname)
    print("\t                 The file can be created by")
    print("\t                 java -jar /path/to/OmegaT.jar /path/to/project --mode=console-createpseudotranslatetmx --pseudotranslatetmx=%s"%iname)
    print("\t-g csv_file      glossary with the UI translation. Default: %s"%gname)
    print("\t-o output_file   translated output file")
    print("\t-h               this usage")

def parsecmd():
    global iname, oname, lang, omegat_project, api_key
    try:
        opts, Names = getopt.getopt(sys.argv[1:], "k:hi:o:l:p:", [])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err)) # will print something like "option -a not recognized"
        usage(desc)
        sys.exit(2)
    for o, a in opts:
        if o in ("-o"):
            oname = a
        elif o in ("-i"):
            iname = a
        elif o in ("-l"):
            lang = a
        elif o in ("-p"):
            omegat_project = a
        elif o in ("-k"):
            api_key = a
        elif o in ("-h"):
            usage()
            sys.exit(0)
        else:
            assert False, "unhandled option"

api_key = os.environ.get('TMXTRANS_API_KEY')
lang = os.environ.get('TMXTRANS_TARGET_LANG')
omegat_project = os.environ.get('TMXTRANS_OMEGAT_PROJECT')
oname = 'out.tmx'
iname = 'in.tmx'
gname = f'glossary_{lang}.csv'

parsecmd()
tr = Trans(lang=lang, api_key=api_key, omegat_project=omegat_project, glossary=gname)

#tree = etree.parse(iname)
tree = etree.parse(iname)
root = tree.getroot()
verbose = False

translated = 0
for iitem in tree.xpath('//tu'):
    item = deepcopy(iitem)
    src, tgt = item.xpath("//seg")
    #trace()

    # skip, if already translated
    if tgt.text and src.text != tgt.text:
        translated += 1
        continue

    trtext = tr.translate(src.text)
    if trtext:
        translated += 1
        print(f"Translating: {src.text}")
        print(f"             {trtext}")
        tgt.text = trtext
        iitem.getparent().replace(iitem, item)
        #intermediate saving
        if not translated%1000:
            tree.write (oname)
    else:
        iitem.getparent().remove(iitem)
tree.write (oname)
print()
print(f"Done, translated {translated} strings")
print(f"Now, copy the output file {oname} to the {omegat_project}/tm directory")
