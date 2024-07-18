# Krona Compare

Compare samples with linked [Krona](https://github.com/marbl/Krona/wiki)
charts.

Input samples should be in the "cladecounts" format produced by the [NAO MGS
Pipeline](https://github.com/naobservatory/mgs-pipeline), or any TSV in the
format:

    <taxid> <n_direct_assignments>

## Dependencies

Install [Krona Tools](https://github.com/marbl/Krona/wiki/KronaTools).  When I
did this on 2024-07-17 this looked like:

```
$ wget https://github.com/marbl/Krona/releases/download/v2.8.1/KronaTools-2.8.1.tar
$ tar -xvf KronaTools-2.8.1.tar
$ cd KronaTools-2.8.1
$ sudo ./install.pl
$ ./updateTaxonomy.sh
```

## Usage

    ./krona-compare.py counts1.tsv counts2.tsv ...

    ./krona-compare.py --group <name1> counts1a.tsv counts1b.tsv ... \
                       --group <name2> counts2a.tsv counts2b.tsv ... \
                       ...

If you choose to group inputs, within each group list the counts will be
combined and presented as a single chart with the provided name.
