#!/usr/bin/env python3

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt

import click
import itertools
import numpy as np

import IPython

#======================================================================

class NoValuesError(Exception): pass

class SkipLineException(Exception): pass

DEFAULT_VAR_COL=6
DEFAULT_VAR=['t_so_b', 't_so_new_b', 'w_so_b', 'w_so_ice_b', 'w_so_ice_new_b']

#======================================================================

@click.command()
@click.option('-i', '--infile', 'named_infiles', type=(str, str),
              metavar=('name', 'file'), multiple=True, required=True,
              help="Input file path, along with name used in the plot legend.")
@click.option('-o', '--outfile', help="Output plot file path.")
@click.option('-v', 'verbosity', count=True,
              help="Successively increase level of verbosity.")
@click.option('--var-col', type=int, default=DEFAULT_VAR_COL,
              help="Variable column (zero-based).")
@click.option('--var-name', type=str, required=True, help="Variable name.")
@click.option('--relative/--absolute', help="Plot relative to first line.")
@click.option('--title', help="Plot title.")
def main(named_infiles, outfile, verbosity, var_col, var_name, relative,
         title):

    if verbosity >= 2:
        print('-'*30)
        print(f"named_infiles : {named_infiles}")
        print(f"outfile       : {outfile}")
        print(f"verbosity     : {verbosity}")
        print(f"var_col       : {var_col}")
        print(f"var_name      : {var_name}")
        print(f"relative      : {relative}")
        print(f"title         : {title}")
        print('-'*30)

    named_vals = read_files(named_infiles, var_name, var_col,
                            verbosity=verbosity)

    plot_hist(outfile, var_name, named_vals, relative=relative, title=title,
              verbosity=verbosity)

#======================================================================

def read_files(named_infiles, *args, **kwargs):
    named_vals = []
    for name, infile in named_infiles:
        try:
            vals = read_file(infile, *args, **kwargs)
        except NoValuesError:
            pass
        else:
            named_vals.append((name, vals))
    return named_vals

def read_file(infile, var_name, var_col, *, skip_zeros=True, verbosity=0):
    if verbosity >= 1:
        print(f"read {infile}")
    vals = []
    try:
        with open(infile, 'r') as fi:
            for line in fi.readlines():
                try:
                    val = line_to_val(line, var_col, var_name, skip_zeros)
                except SkipLineException:
                    continue
                else:
                    vals.append(abs(val))
    except FileNotFoundError:
        print(f"error: file not found: {infile}")
        exit(1)
    if not vals:
        raise NoValuesError(var_name)
    return vals

def line_to_val(line, var_col, var_name, skip_zeros):
    elements = line.split()
    try:
        var_i = elements[var_col]
    except IndexError:
        raise  #SR_TMP
    if var_i != var_name:
        raise SkipLineException(f"{var_i} != {var_name}")
    try:
        val = float(elements[-1])
    except ValueError:
        raise  #SR_TMP
    if skip_zeros and val == 0.0:
        raise SkipLineException('skip zero')
    return val

#======================================================================

def plot_hist(outfile, var_name, named_vals, *, relative=False, title=None,
              verbosity=0):
    if verbosity == 0:
        print(outfile)
    else:
        print(f"plot {outfile}")

    fig, ax = plt.subplots(figsize=(12, 9))

    if title is None:
        title = var_name
    ax.set_title(title)

    if relative:
        ylabel = 'frequency rel. to [0] (%)'
    else:
        ylabel = 'frequency (%)'
    ax.set_ylabel(ylabel)
    ax.set_xlabel(f'abs. deviation')

    ax.yaxis.set_major_formatter(mpl.ticker.FormatStrFormatter('% 4d'))

    ax.set_xscale('log')

    if named_vals:

        bins = derive_bins_log(named_vals)

        color_cycle, marker_cycle = get_color_marker_cycle()
        markersizes_iter = iter(np.linspace(12.0, 2.0, len(named_vals)))

        bin_edges = set()
        hist_ref = None
        for i, (name, vals) in enumerate(named_vals):
            marker = next(marker_cycle)
            color = next(color_cycle)
            markersize = next(markersizes_iter)
 
            n = np.asarray(vals).size
 
            label = f"[{i}] {name} ({n:,d})"
 
            hist, bin_edges_i = np.histogram(vals, bins=bins) #, density=True)
            hist = hist/n
            if hist_ref is None:
                hist_ref = hist
            if relative:
                hist = hist/np.where(hist_ref > 0, hist_ref, np.nan)
            ys = 100*hist
            xs = 0.5*(bin_edges_i[:-1] + bin_edges_i[1:])
 
            bin_edges |= set(bin_edges_i)
 
            p = ax.plot(xs, ys, color=color, label=label, marker=marker,
                        markersize=markersize, markerfacecolor='w',
                        markeredgewidth=1.5)

        for x in sorted(bin_edges):
            ax.axvline(x, c='lightgray', lw=0.5, zorder=0)

        ax.legend()

    fig.savefig(outfile, bbox_inches='tight')
    plt.close()

def get_color_marker_cycle():

    # Color palette derived from colorbrewer2.org
    colors1 = [
        '#e41a1c',  # red
        '#377eb8',  # blue
        '#4daf4a',  # green
        '#984ea3',  # purple
        '#ff7f00',  # orange
        '#ffff33',  # yellow
        '#a65628',  # brown
        '#f781bf',  # pink
        '#999999',  # gray
    ]
    colors2 = [
        '#a6cee3',  # light blue
        '#1f78b4',  # blue
        '#b2df8a',  # light green
        '#33a02c',  # green
        '#fb9a99',  # light red
        '#e31a1c',  # red
        '#fdbf6f',  # light orange
        '#ff7f00',  # orange
        '#cab2d6',  # light purple
    ]
    colors3 = [
        '#1f78b4',  # blue
        '#e31a1c',  # red
        '#33a02c',  # green
        '#ff7f00',  # orange
        '#984ea3',  # purple
    ]
    colors = colors3

    markers = [
        'o', 's', 'v', '^', '<', '>', '1', '2', '3', '4', '8', 'p', 'P', '*',
        'h', 'H', '+', 'x', 'X', 'D', 'd', '|', '_']
    markers = [m for m in markers for _ in range(len(colors))]

    return itertools.cycle(colors), itertools.cycle(markers)

def derive_bins_log(named_vals):
    if not named_vals:
        return None
    vals_flat = np.array([v for n, d in named_vals for v in d])
    vals_flat = vals_flat[~np.isnan(vals_flat)]
    vals_flat = vals_flat[vals_flat != 0.0]
    vals_flat = np.abs(vals_flat)
    if vals_flat.size == 0:
        return None
    start = np.floor(np.log10(vals_flat.min()))
    end = np.ceil(np.log10(vals_flat.max()))
    n = (end - start)*10 + 1
    return np.logspace(start, end, n)

#======================================================================

if __name__ == '__main__':
    main()
