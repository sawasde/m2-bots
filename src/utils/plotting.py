""" Plot charts with Cosmo data """
# pylint: disable=no-name-in-module, import-error

import gc
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
import mpld3
from utils import utils


@utils.logger.catch
def plot_sublots(df_initial, plot_features_dicts, xaxis='',
                    save=None, html=None, style='-o', show=False):
    """ One plot with multiple subplots """
    # pylint: disable=too-many-arguments

    total_plots = len(plot_features_dicts)

    fig, axes = plt.subplots(total_plots, 1, sharex=True)
    axes[0].yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    fig.set_size_inches(13, 8)

    for i, axis in enumerate(axes):

        for feature, color in plot_features_dicts[i].items():
            axis.plot(df_initial[xaxis], df_initial[feature], style, color=color)

    # Show figure
    if show:
        plt.show()

    # Save figure as image format
    if save:
        fig.savefig(save)

    if html:
        with open(html, "w", encoding='utf-8') as html_file:
            html_file.write(mpld3.fig_to_html(fig))
            html_file.close()

    # close
    plt.close(fig)
    gc.collect()
