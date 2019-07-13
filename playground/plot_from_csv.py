import pandas as pd
import numpy as np
from scipy.ndimage.filters import gaussian_filter1d
import argparse
import warnings
import math
import csv
import re
import os
import sys

sys.path.append("/home/farzad/devel/SymmetricRL")

from common.plots import Plot, LinePlot, plt, ScatterPlot
from common.misc_utils import str2bool


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--load_paths", type=str, nargs="+")
    parser.add_argument("--columns", type=str, nargs="+")
    parser.add_argument("--row", type=str, default="total_num_steps")
    parser.add_argument("--alpha", type=float, default=0.9)
    parser.add_argument("--smoothing", type=float, default=0)
    parser.add_argument("--group", type=str2bool, default=False)
    parser.add_argument("--log_scale", type=str2bool, default=False)
    parser.add_argument("--xlog_scale", type=str2bool, default=False)
    parser.add_argument("--legend", type=str2bool, default=True)
    parser.add_argument("--name_regex", type=str, default="")
    parser.add_argument("--final", type=str2bool, default=False)
    args = parser.parse_args()

    N = len(args.columns)
    nrows = math.floor(math.sqrt(N))
    title = "Results with smoothing %.1f" % args.smoothing
    if args.log_scale:
        title += " (Log Scale)"
    plot = Plot(nrows=nrows, ncols=math.ceil(N / nrows), title=title)
    plots = []
    for column in args.columns:
        if args.final:
            plots.append(ScatterPlot(parent=plot, ylabel=column, xlabel=args.row))
        else:
            plots.append(
                LinePlot(
                    parent=plot,
                    ylabel=column,
                    xlabel=args.row,
                    ylog_scale=args.log_scale,
                    xlog_scale=args.xlog_scale,
                    alpha=args.alpha,
                    num_scatters=len(args.load_paths),
                )
            )

    smoothing_method = lambda x: x
    if args.smoothing > 0.1:
        smoothing_method = lambda x: gaussian_filter1d(x, sigma=args.smoothing)

    if args.name_regex:
        legends = [re.findall(args.name_regex, path)[0] for path in args.load_paths]
        legend_paths = sorted(zip(legends, args.load_paths))
        legends = [x[0] for x in legend_paths]
        args.load_paths = [x[1] for x in legend_paths]
    else:
        common_prefix = os.path.commonprefix(args.load_paths)
        warnings.warn("Ignoring the prefix (%s) in the legend" % common_prefix)
        legends = [path[len(common_prefix) :] for path in args.load_paths]

    data = [load_path(path, args) for path in args.load_paths]

    # getting rid of
    legends = [l for (l, d) in zip(legends, data) if d is not None]
    data = [d for d in data if d is not None]

    if args.group:
        data, legends = compute_group_data(data, legends, args.row, args.columns)

    if args.legend:
        plot.fig.legend(legends, loc="upper center")

    for i, df in enumerate(data):
        for j, column in enumerate(args.columns):
            if args.final:
                y = df[column][-1:].item()
                x = float(legends[i])
                plots[j].add_point([x, y])
            else:
                df[column] = smoothing_method(df[column])
                plots[j].update(df[[args.row, column]].values, line_num=i)
                if args.group:
                    plots[j].fill_between(
                        df[args.row],
                        smoothing_method(df[column + "_min"]),
                        smoothing_method(df[column + "_max"]),
                        line_num=i,
                    )

    plt.ioff()
    plt.show()


def load_path(path, args):
    print("Loading ... ", path)
    filename = os.path.join(path, "evaluate.csv" if args.final else "progress.csv")
    try:
        return pd.read_csv(filename)
    except:
        warnings.warn("Could not load %s" % filename)
        return None


def compute_group_data(data, group_names, row, columns):
    groups = {}
    for df, gname in zip(data, group_names):
        if gname not in groups:
            groups[gname] = []
        groups[gname].append(df)

    stat_funcs = {"": np.mean, "_min": np.min, "_max": np.max}

    for key, dfs in groups.items():
        df_column_names = [row] + [
            c + fname for c in columns for fname in stat_funcs.keys()
        ]
        stats = np.concatenate(
            [
                [dfs[0][row]],
                [
                    func([df[c] for df in dfs], axis=0)
                    for c in columns
                    for func in stat_funcs.values()
                ],
            ]
        )
        groups[key] = pd.DataFrame(stats.transpose(), columns=df_column_names)

    return list(groups.values()), list(groups.keys())


if __name__ == "__main__":
    main()
