#!/usr/bin/env python
# replace a string in multiple files

# python vanillons/gen_templates/findandreplace.py templates/vanillons

import fileinput
import glob
import sys
import os
import getopt

PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BLACKLIST_START = ['data', '.', 'gen_templates', 'quaid']
BLACKLIST_END = ['.egg-info', '.komodoproject', '.kpf', '.pyc', '.html.py']
TEMPLATES = ['.py', '.html', '.ini', '.txt', '.cfg', '.in']

REPLACEMENTS = {
    'vanillons': '{{package}}',
    'Vanillons': '{{project}}',
}

DIR_REPLACEMENTS = {
    'vanillons': '+package+'
}

def defaultfn(line):
    l = line
    for k, v in REPLACEMENTS.items():
        l = l.replace(k, v)
    return l

def replace(linefn, src='.', dest='.', recurse=True, blacklist_end=BLACKLIST_END, blacklist_start=BLACKLIST_START, ext='_tmpl'):
    
    def checklist(fname, fn, l):
        for blk in l:
            if getattr(fname, fn)(blk):
                return True
    
    if not os.path.exists(dest):
        os.makedirs(dest)
    
    files = glob.glob(os.path.join(src, '*'))
    for file in files:
        
        fname = os.path.basename(file)
        
        bad = checklist(fname, 'endswith', blacklist_end)
        bad = bad or checklist(fname, 'startswith', blacklist_start)
        if bad: continue
        
        if os.path.isdir(file):
            if recurse:
                if fname in DIR_REPLACEMENTS:
                    fname = DIR_REPLACEMENTS[fname]
                replace(linefn, file, os.path.join(dest, fname),
                        recurse=recurse, blacklist_end=blacklist_end,
                        blacklist_start=blacklist_start, ext=ext)
            continue
        
        #input parsing
        input = open(file, 'r')
        lines = []
        
        if checklist(fname, 'endswith', TEMPLATES):
            fname = os.path.join(dest, fname+ext)
            for line in input.readlines():
                lines.append(linefn(line))
        else:
            fname = os.path.join(dest, fname)
            lines = input.readlines()
        
        input.close()
        
        #output write
        output = open(fname, 'w')
        output.writelines(lines)
        output.close()

if __name__ == '__main__':
    replace(defaultfn, src=PROJECT_PATH, dest=sys.argv[1], recurse=True)
