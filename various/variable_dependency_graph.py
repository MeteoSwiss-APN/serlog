#!/usr/bin/env python3

import click
import igraph
import re

import IPython

@click.command()
@click.option('-i', '--infile', required=True, help="Input text file.")
def main(infile):

    rx_empty = re.compile(r'^$')
    rx_title = re.compile(r'^(\w+):$')
    rx_uline = re.compile(r'^([=-]+)$')
    rx_depcy = re.compile(r'^(\w+) +((\w+) +)?([^ ]+)$')

    print(f"read {infile}")
    with open(infile, 'r') as fi:
        state = 'closed'
        var_type = None
        for line in fi.readlines():
            line = line.strip()

            # Empty line
            if rx_empty.match(line):
                state = 'closed'
                continue

            # Title
            m = rx_title.match(line)
            if m:
                if state != 'closed':
                    raise Exception(
                        f"line matches title, but state is '{state}', "
                        f"not 'closed': '{line}'")
                target_name = m.groups(1)
                state = 'opening'
                continue
            elif state == 'closed':
                raise Exception(
                    f"state is 'closed', but line is not a title: '{line}'")

            # Title underline
            m = rx_uline.match(line)
            if m:
                if state != 'opening':
                    raise Exception(
                        f"line matches title underline, but state is '{state}', "
                        f"not 'opening': '{line}'")

                ch = m.group(1)[0]
                if ch == '=':
                    target_type = 'root'
                elif ch == '-':
                    target_type = 'regular'
                else:
                    raise Exception(
                        f"invalid title character '{ch}' in line: '{line}'")
                state = 'open'

                continue

            elif state == 'opening':
                raise Exception(
                    f"state is 'opening', but line is no underline: '{line}'")

            # Dependency
            m = rx_depcy.match(line)
            if m:
                if state != 'open':
                    raise Exception(
                        f"line matches dependency definition, but state is "
                        f"'{state}', not 'open', in line: '{line}'")

                depcy_name = m.group(1)
                depcy_type = m.group(3)
                depcy_orig = m.group(4)

                if depcy_type in [None, 'array']:
                    depcy_type = 'array'
                elif depcy_type == 'scalar':
                    pass
                else:
                    raise Exception(
                        f"invalid dependency type '{depcy_type}' in line: "
                        f"'{line}'")

                if depcy_orig in ['[above]', '[below]']:
                    pass
                elif depcy_orig == 'constant':
                    pass
                elif depcy_orig == 'external':
                    pass
                else:
                    raise Exception(
                        f"invalid dependency origin '{depcy_orig}' n line: "
                        f"'{line}'")

                continue

            IPython.embed()

            raise Exception(f"invalid line: '{line}'")

if __name__ == '__main__':
    main()
