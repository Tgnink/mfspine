""" plot: plotting
copy from liaozhenghan
"""

import numpy as np
import matplotlib.pyplot as plt
import napari
from . import utils
import colorcet as cc
from matplotlib.widgets import MultiCursor
from matplotlib.colors import LinearSegmentedColormap
__all__ = [
    # matplotlib: 2d plot
    "imshow", "scatter", "imoverlay",
    # napari: 3d viewer
    "imshow3d"
]


#=========================
# matplotlib
#=========================

def setup_subplots(n, shape, figsize1):
    """ setup subplots
    :param n: number of subplots, can be different from shape
    :param shape: (nrows, ncols), either can be None
    :param figsize1: size of one subplot
    :return: fig, axes
    """
    # setup shape
    if shape is None:
        shape = (1, n)
    elif (shape[0] is None) and (shape[1] is None):
        shape = (1, n)
    elif shape[0] is None:  # (None, ncols)
        shape = (int(np.ceil(n/shape[1])), shape[1])
    elif shape[1] is None:  # (nrows, None)
        shape = (shape[0], int(np.ceil(n/shape[0])))

    # setup figsize
    if figsize1 is None:
        figsize = None
    else:
        figsize = (
            figsize1[0]*shape[1],  # size_x * ncols
            figsize1[1]*shape[0]  # size_y * nrows
        )

    # setup figure
    fig, axes = plt.subplots(
        nrows=shape[0], ncols=shape[1],
        sharex=True, sharey=True,
        figsize=figsize,
        constrained_layout=True,
        squeeze=False  # always return axes as 2d array
    )
    return fig, axes

def imshow(
        I_arr, shape=None, style="binary",
        vrange=None, qrange=(0, 1),
        cmap="gray", colorbar=True, colorbar_shrink=0.6,
        title_arr=None, suptitle=None,
        figsize1=None, save=None, dpi=None
    ):
    """ show multiple images
    :param I_arr: a 1d list of images
    :param shape: (nrows, ncols), will auto set if either is None
    :param style: custom, gray, binary, orient
    :param vrange, qrange: range of value(v) or quantile(q)
    :param cmap, colorbar, colorbar_shrink: set colors
    :param title_arr, suptitle, supxlabel, supylabel: set labels
    :param figsize1: size of one subplot
    :param save: name to save fig
    :param dpi: dpi of saved fig
    :return: fig, axes
    """
    # setup styles
    # grayscale image: adjust qrange
    if style == "gray":
        cmap = "gray"
        vrange = None
        qrange = (0.02, 0.98)
    # orientation: circular cmap, convert rad to deg
    elif style == "orient":
        cmap = "hsv"
        vrange = (0, 180)
        I_arr = [np.mod(I, np.pi)/np.pi*180 for I in I_arr]
    elif style == "binary":
        cmap = "gray"
        vrange = (0, 0.1)
        colorbar = False
    elif style == "custom":
        pass
    else:
        raise ValueError("style options: custom, gray, orient")

    # setup subplots
    fig, axes = setup_subplots(len(I_arr), shape, figsize1)
    shape = axes.shape

    # plot on each ax
    for idx1d, I in enumerate(I_arr):
        # get 2d index
        idx2d = np.unravel_index(idx1d, shape)

        # setup vrange
        if vrange is not None:
            vmin, vmax = vrange
        else:
            vmin = np.quantile(I, qrange[0])
            vmax = np.quantile(I, qrange[1])
        
        # plot
        axes[idx2d].set_aspect(1)
        im = axes[idx2d].imshow(
            I, vmin=vmin, vmax=vmax,
            cmap=cmap, origin="lower"
        )

        # setup colorbar, title
        if colorbar:
            fig.colorbar(im, ax=axes[idx2d], shrink=colorbar_shrink)
        if title_arr is not None:
            axes[idx2d].set_title(title_arr[idx1d])
        
    # setup fig title
    fig.suptitle(suptitle)

    # save fig
    if save is not None:
        fig.savefig(save, dpi=dpi)

    return fig, axes

def scatter(
        xy_arr,
        labels_arr=None,
        shape=None,
        marker_size=0.1,
        cmap="viridis", colorbar=True, colorbar_shrink=0.6,
        title_arr=None, suptitle=None,
        figsize1=None, save=None, dpi=None
    ):
    """ show multiple scatters
    :param xy_arr: 1d list of 2d array [x, y]
    :param labels_arr: 1d list of labels for each xy
    :param shape: (nrows, ncols), will auto set if either is None
    :param cmap, colorbar, colorbar_shrink: set colors
    :param title_arr, suptitle, supxlabel, supylabel: set labels
    :param figsize1: size of one subplot
    :param save: name to save fig
    :param dpi: dpi of saved fig
    :return: fig, axes
    """
    # regularize labels_arr
    if labels_arr is None:
        labels_arr = [None]*len(xy_arr)

    # setup subplots
    fig, axes = setup_subplots(len(xy_arr), shape, figsize1)
    shape = axes.shape

    # plot on each ax
    for idx1d, (xy, labels) in enumerate(zip(xy_arr, labels_arr)):
        # get 2d index
        idx2d = np.unravel_index(idx1d, shape)

        # plot
        axes[idx2d].set_aspect(1)
        im = axes[idx2d].scatter(
            xy[:, 0], xy[:, 1],
            s=marker_size,
            c=labels, cmap=cmap
        )

        # setup colorbar, title
        if colorbar:
            fig.colorbar(im, ax=axes[idx2d], shrink=colorbar_shrink)
        if title_arr is not None:
            axes[idx2d].set_title(title_arr[idx1d])

    # setup fig title
    fig.suptitle(suptitle)

    # save fig
    if save is not None:
        fig.savefig(save, dpi=dpi)

    return fig, axes

def imoverlay(im_dict, shape=None,
        figsize1=None, save=None, dpi=200,
        bg_qrange=(0.02, 0.98), bg_alpha=0.5, bg_cmap='gray',
        fg_alpha=1., fg_cmaps=('Blues','Oranges','Greens','Reds')
    ):
    """ show multiple images with overlays
    :param im_dict: {title1: {I: I, yxs: [yx1, yx2]}, title2: ...}
    :param shape: (nrows, ncols), will auto set if either is None
    :param bg_qrange, bg_alpha, bg_cmap: quantile range, alpha value, colormap of the background image
    :param fg_alpha: alpha value of foreground images
    :param figsize1: size of one subplot
    :param save: name to save fig
    :param dpi: dpi of saved fig
    :return: fig, axes
    """
    # setup figure
    fig, axes = setup_subplots(len(im_dict), shape, figsize1)
    shape = axes.shape

    # plot on each ax
    for idx1d, (label, item) in enumerate(im_dict.items()):
        # setup axes
        idx2d = np.unravel_index(idx1d, shape)
        axes[idx2d].set_aspect(1)
        axes[idx2d].set_axis_off()
        axes[idx2d].set(title=label)

        # background image
        vmin = np.quantile(item["I"], bg_qrange[0])
        vmax = np.quantile(item["I"], bg_qrange[1])
        axes[idx2d].imshow(
            item["I"], vmin=vmin, vmax=vmax,
            cmap=bg_cmap, alpha=bg_alpha, origin="lower"
        )
        # overlaying images
        # yx to im, set zero pixels to alpha=0
        for i, yx in enumerate(item["yxs"]):
            im_i = utils.points_to_voxels(yx, item["I"].shape)
            axes[idx2d].imshow(
                # set vmax=2 so that midpoint of cmap is shown
                im_i, vmin=0, vmax=2,
                cmap=fg_cmaps[i], alpha=im_i*fg_alpha,
                origin="lower", interpolation='none'
            )

    # save fig
    if save is not None:
        fig.savefig(save, dpi=dpi)

    return fig, axes
def showims(*ims):
    fig,axes=plt.subplots(1,len(ims),sharex=True,sharey=True)
    # print(im1.shape)
    for i,im in enumerate(ims):
        #print(im.shape)
        np.dtype
        if  "int" in im.dtype.__repr__() and len(np.unique(im))<500:
            cmap=LinearSegmentedColormap.from_list("isolum",cc.glasbey)
            axes[i].imshow(im,interpolation='none',cmap=cmap)
        else:
            axes[i].imshow(im,interpolation='none')
    # axes[1].imshow(im2,interpolation='none')
    # axes[2].imshow(im3,interpolation='none')
    multi = MultiCursor(fig.canvas, axes, color='r', lw=1, horizOn=True, vertOn=True)
    plt.show()
#=========================
# napari
#=========================

def imshow3d(
        I, Is_overlay=(),
        vecs_zyx=(), vecs_dir=(), vec_width=0.1,point_lay=(),label_lay=(),label_lay_name=(),
        name_I="image", name_Is=None, name_vecs=None,
        cmap_Is=None, cmap_vecs=None,
        visible_Is=True, visible_vecs=True
    ):
    """ plot images using napari
    :param I: main image
    :param Is_overlay: array of overlaying images
    :param vecs_zyx: array of vector positions, each shape = (npts, 3)
    :param vecs_dir: array of vector directions, each shape = (npts, 3)
    :param vec_width: width of vectors
    :param name_I, name_Is, name_vecs: names for I, Is, vecs
    :param cmap_Is, cmap_vecs: default=["green", "yellow", "cyan", "magenta",
        "bop blue", "bop orange", "bop purple", "red", "blue"]
    :param visible_Is, visible_vecs: if visible, True/False, or array of bools
    :return: viewer
    """
    # setup defaults
    # cmaps
    if cmap_Is is None:
        cmap_Is = [
            "green", "yellow", "cyan", "magenta",
            "bop blue", "bop orange", "bop purple", "red", "blue",
           
        ]
    if cmap_vecs is None:
        cmap_vecs = cmap_Is
    # Is
    if name_Is is None:
        name_Is = [f"overlay {i+1}" for i in range(len(Is_overlay))]
    if visible_Is in [True, False]:
        visible_Is = [visible_Is for _ in range(len(Is_overlay))]
    # vecs
    if name_vecs is None:
        name_vecs = [f"vector {i+1}" for i in range(len(vecs_zyx))]
    if visible_vecs in [True, False]:
        visible_vecs = [visible_vecs for _ in range(len(vecs_zyx))]
    
    # setup viewer
    viewer = napari.Viewer()

    # view images
    # flip y-axis, napari doesn't seem to support orient="lower" as in imshow
    # main image
    #I = np.flip(I, -2)
    viewer.add_image(
        I, name=name_I, colormap="gray",
        opacity=0.75, blending="additive"
    )
    # overlay images
    for i in range(len(Is_overlay)):
        Ii = np.array(Is_overlay[i])
        viewer.add_image(
            Ii, name=name_Is[i], colormap=cmap_Is[i%len(cmap_Is)],
            opacity=1, blending="additive", visible=visible_Is[i]
        )
    for i in range(len(point_lay)):
        viewer.add_points(point_lay[i],size=2,opacity=0.7)
    for i in range(len(label_lay)):
        viewer.add_labels(label_lay[i],name=label_lay_name[i])
    # view vectors
    for i in range(len(vecs_zyx)):
        zyx = vecs_zyx[i]
        dzyx = vecs_dir[i]
        # construct vector according to napari's requirement
        # flip y, as is done to the image
        vec = np.zeros((len(zyx), 2, 3))
        vec[:, 0, :] = zyx
        vec[:, 0, 1] = I.shape[1] - zyx[:, 1] - 1
        vec[:, 1, :] = dzyx
        vec[:, 1, 1] = -dzyx[:, 1]
        # add vector layer
        viewer.add_vectors(
            vec, name=name_vecs[i], opacity=1, visible=visible_vecs[i],
            edge_width=vec_width, edge_color=cmap_vecs[i]
        )
    return viewer

