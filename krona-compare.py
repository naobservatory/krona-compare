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

SELECT_NODE_MONKEY_PATCH_JS = """
if (newNode && !window.externallyInitiatedTargeting) {
  const targetName = newNode.name;
  console.log("Searching other windows to select the node with", targetName);

  function findNamedNode(node) {
    if (node.name == targetName) {
      return node;
    }
    for (const child of node.children) {
      const possibleTarget = findNamedNode(child);
      if (possibleTarget) {
        return possibleTarget;
      }
    }
    return null;
  }

  const otherIframes = window.parent.document.body.getElementsByTagName(
      "iframe");
  for (let i = 0; i < otherIframes.length; i++) {
    if (i == %s) {
      continue;  // only sync the other kronas on the page
    }

    const otherIframe = otherIframes[i];
    const otherWindow = otherIframe.contentWindow;
    let other = otherWindow.focusNode;
    if (!other || other.name == targetName) {
      continue;
    }
    while (other.parent) {
      other = other.parent;
    }
    const otherRoot = other;
    //console.log("The root in", i, "is", otherRoot);
    const target = findNamedNode(otherRoot);
    console.log("The target in", i, "is", target);
    if (target) {
      otherWindow.externallyInitiatedTargeting = true;
      otherWindow.expand(target);
      otherWindow.externallyInitiatedTargeting = false;
    }
  }
}
"""

NAVIGATE_BACK_MONKEY_PATCH_JS = """
if (!window.externallyInitiatedTargeting) {
  const otherIframes =
     window.parent.document.body.getElementsByTagName("iframe");
  for (let i = 0; i < otherIframes.length; i++) {
    if (i == %s) {
      continue;  // only sync the other kronas on the page
    }
    const otherIframe = otherIframes[i];
    const otherWindow = otherIframe.contentWindow;
    otherWindow.externallyInitiatedTargeting = true;
    otherWindow.navigateBack();
    otherWindow.externallyInitiatedTargeting = false;
  }
}
"""

def rewrite_to_update_other_children(raw_html, my_index):
    for target, js in [
            ("if ( selectedNode != newNode )",
             SELECT_NODE_MONKEY_PATCH_JS),
            ("if ( nodeHistoryPosition > 0 )",
             NAVIGATE_BACK_MONKEY_PATCH_JS)]:
        raw_html = raw_html.replace(target, "%s%s" % (
            js % my_index, target))
    return raw_html

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
        krona_iframes = []
        krona_fname =  os.path.join(tmpdir, "krona.html")
        run_krona(prepare_inputs(groups, tmpdir), krona_fname)
        with open(krona_fname) as inf:
            krona_srcdoc_raw = inf.read()

        for my_index, (name, fnames) in enumerate(groups):
            rewritten_html = rewrite_to_update_other_children(
                krona_srcdoc_raw, my_index)

            krona_iframes.append(
              '<td><iframe srcdoc="%s" height="800px" '
              'onload="maybeSelectDatasets()"></iframe>' %
                  html.escape(rewritten_html, quote=True))

        with open(combined_html, "w") as outf:
            outf.write("""
<html>
  <head>
    <title>Krona Charts</title>
    <style>
      table { width: 100%%; height: 100%% }
      iframe { width: 100%%; height: 100%% }
    </style>
    <script>
    function selectDatasets() {
      const iframes = document.getElementsByTagName('iframe');
      for (let i = 0; i < iframes.length; i++) {
        const otherWindow = iframes[i].contentWindow;
        otherWindow.document.getElementById(
          'datasets').selectedIndex = i;
        otherWindow.onDatasetChange();
      }
    }
    let iframesLoaded = 0;
    function maybeSelectDatasets() {
      iframesLoaded++;
      if (iframesLoaded == %s) {
        selectDatasets();
      }
    }
    </script>
  </head>
  <body>
    <table>
      <tr>%s
    </table>
  </body>
  </html>
</html>
            """ % (len(krona_iframes),
                   "".join(krona_iframes)))

    subprocess.check_call(["open", combined_html])

if __name__ == "__main__":
    start(sys.argv[1:])
