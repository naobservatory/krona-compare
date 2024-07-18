#!/usr/bin/env python3

import os
import sys
import html
import tempfile
import subprocess
from collections import Counter

def prepare_inputs(groups, tmpdir):
    inputs = []
    for name, fnames in groups:
        print(name, fnames)
        out_tsv = os.path.join(tmpdir, name + ".tsv")

        counter = Counter()
        for fname in fnames:
            with open(fname) as inf:
                for line in inf:
                    taxid, count = line.strip().split()
                    counter[int(taxid)] += int(count)

        with open(out_tsv, "w") as outf:
            for taxid, count in sorted(counter.items()):
                outf.write("%s\t%s\n" % (taxid, count))

        inputs.append(out_tsv)
    return inputs

def run_krona(inputs, out_fname):
    subprocess.check_call(
        ["ktImportTaxonomy",
         "-o", out_fname,
         "-t", "1",
         "-m", "2",
         *inputs])

def parse_args_groups(args):
    group_name = None
    expect_name = False
    groups = []
    group = []
    for arg in args:
        if arg == "--group":
            if expect_name:
                raise Exception("Two --group arguments in a row")
            expect_name = True
            if group:
                assert group_name
                groups.append((group_name, group))
                group = []
                group_name = None
            else:
                if group_name:
                    raise Exception("Empty group %s" % group_name)
        elif expect_name:
            assert not group
            assert not group_name
            group_name = arg
            expect_name = False
        else:
            assert group_name
            group.append(arg)
    if expect_name:
        raise Exception("Trailing --group")
    if group_name:
        if not group:
            raise Exception("Empty group %s" % group_name)
        groups.append((group_name, group))
    return groups

def parse_args_no_groups(args):
    groups = []
    for path in args:
        name, ext = os.path.splitext(os.path.basename(path))
        groups.append((name, [path]))
    return groups

def start(args):
    if "--group" in args:
        groups = parse_args_groups(args)
    else:
        groups = parse_args_no_groups(args)

    for name, group in groups:
        for fname in group:
            if not os.path.exists(fname):
                raise Exception("Missing file %r in group %s" % (
                    fname, name))

    combined_html = "combined.krona.html"
    with tempfile.TemporaryDirectory() as tmpdir:
        krona_names = []
        krona_iframes = []
        for name, fnames in groups:
            krona_names.append("<th>%s" % html.escape(name))
            
            krona_fname = os.path.join(tmpdir, name + ".krona.html")
            run_krona(prepare_inputs([(name, fnames)], tmpdir),
                      krona_fname)

            with open(krona_fname) as inf:
                krona_srcdoc_raw = inf.read()
                
            krona_iframes.append(
                '<td><iframe srcdoc="%s" height="800px">'
                '</iframe>' % (
                    html.escape(krona_srcdoc_raw, quote=True)))

        with open(combined_html, "w") as outf:
            outf.write("""
<html>
  <head>
    <title>Krona Charts</title>
    <style>
      table { width: 100%% }
      iframe { width: 100%% }
    </style>
  </head>
  <body>
    <table>
      <tr>%s
      <tr>%s
    </table>
  </body>
  </html>
</html>
            """ % ("".join(krona_names), "".join(krona_iframes)))

    subprocess.check_call(["open", combined_html])

if __name__ == "__main__":
    start(sys.argv[1:])
