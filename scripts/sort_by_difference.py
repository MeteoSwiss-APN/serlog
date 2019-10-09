#!/usr/bin/env python3

import sys
import numpy as np
import re
import os.path
from inspect import cleandoc

def main(infile1, infile2, outfile, key_cols_str, val_col_str):

    # Maximum plausible difference
    diff_max = 100

    # Decode column and type specifications
    # Syntax: <i><t>, with <i> the column index and <f> the type code
    type_choices = {'i': int, 'f': float, 's': str}
    key_cols, key_types = [], []
    for key_str in key_cols_str.split(','):
        key_cols.append(int(key_str[: -1]))
        key_types.append(type_choices[key_str[-1]])
    try:
        deviat_mode = {'+': 'pos', '-': 'neg'}[val_col_str[-1]]
    except KeyError:
        deviat_mode = 'abs'
    else:
        val_col_str = val_col_str[:-1]
    val_col = int(val_col_str[:-1])
    val_type = type_choices[val_col_str[-1]]

    # Read input files
    content1 = import_data(infile1, key_cols, key_types, val_col, val_type)
    content2 = import_data(infile2, key_cols, key_types, val_col, val_type)

    # Take difference of values (shared keys only)
    results = {}
    key_len = None
    for key, val1 in content1.items():
        try:
            val2 = content2[key]
        except KeyError:
            continue

        if key_len is None:
            key_len = len(key)
        elif key_len != len(key):
            raise Exception(f"unexpected key len: {len(key)} != {key_len}")

        diff = val1 - val2
        if deviat_mode == 'abs':
            diff = abs(diff)
        elif deviat_mode == 'neg' and diff < 0.0:
            pass
        elif deviat_mode == 'pos' and diff > 0.0:
            pass
        else:
            continue

        if abs(diff) > diff_max:
            continue

        if key in results:
            raise Exception(r"duplicate key: {key}")
        results[key] = [val1, val2, diff]

    if not results:
        raise Exception("no shared keys!")

    results = [list(k) + v for k, v in results.items()]

    # Write results to disk
    print(f"write {outfile}")
    fmt = ''
    for val in results[0]:
        if fmt:
            fmt += ' '
        if isinstance(val, str):
            fmt += '{:20s}'
        elif isinstance(val, float):
            fmt += '{:12.7f}'
        elif isinstance(val, int):
            fmt += '{:6d}'
        else:
            raise NotImplementedError(
                f"val type {type(val).__name__} ({val})")
    fmt += '\n'
    with open(outfile, 'w') as f:
        for line in results:
            f.write(fmt.format(*line))

def import_data(file_path, key_cols, key_types, val_col, val_type):
    print(f"read {file_path}")
    n_cols_rx = max(key_cols) + 1
    rx_str = r'^'
    for i in range(n_cols_rx):
        rx_str += r'([^ ]+) ?'
    rx_str += r'([^ ]+ ?)*'
    rx = re.compile(rx_str)
    def int_or_str(s):
        try:
            i = int(s)
        except ValueError:
            return s
        else:
            if i != float(s):
                raise Exception(f"not an int: {s}")
            return i
    content = {}
    with open(file_path) as fi:
        for i_line, line in enumerate(fi.readlines()):
            line = line.strip()
            match = rx.match(line)
            if not match:
                continue
            try:
                key = tuple([t(match.groups()[i])
                             for i, t in zip(key_cols, key_types)])
            except ValueError:
                continue
            try:
                val = val_type(match.groups()[val_col])
            except ValueError:
                continue
            content[key] = val
    if not content:
        raise Exception(f"no lines read from {file_path}")
    return content

if __name__ == '__main__':
    if len(sys.argv) != 6:
        print(cleandoc(f"""
            Usage: {os.path.basename(sys.argv[0])} infile1 infile2 outfile keycols"

            From two space-separated multicolumn files, extract common rows
            based on selected columns and compute the absolute difference
            between the last rows.

            Args:
                infile1: First input file path.

                infile2: Second input file path.

                outfile: Output file path.

                keycols: Comma-separated list of indices of the columns with
                    base zero, used to identify common rows. The tuples
                    comprised of the values in the respective columns in each
                    line must be unique in each file.

                valcol: Index with base zero of values column.
        """))
        exit(1)
    main(*sys.argv[1:])
