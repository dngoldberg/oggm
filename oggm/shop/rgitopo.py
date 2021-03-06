import logging

import os
import shutil

try:
    import salem
except ImportError:
    pass

from oggm import utils, workflow
from oggm.exceptions import InvalidParamsError

# Module logger
log = logging.getLogger(__name__)

DEMS_URL = 'https://cluster.klima.uni-bremen.de/data/gdirs/dems_v1/default/'
DEMS_HR_URL = 'https://cluster.klima.uni-bremen.de/data/gdirs/dems_v1/highres/'


def init_glacier_directories_from_rgitopo(rgidf=None, dem_source=None,
                                          resolution='default',
                                          keep_dem_folders=False,
                                          reset=False,
                                          force=True):
    """Initialize a glacier directory from an RGI-TOPO DEM.

    Wrapper around :func:`workflow.init_glacier_directories`, which selects
    a default source for you (if not set manually with `dem_source`).

    The default source is NASADEM for all latitudes between 60N and 56S,
    and COPDEM elsewhere.

    Parameters
    ----------
    rgidf : GeoDataFrame or list of ids, optional for pre-computed runs
        the RGI glacier outlines. If unavailable, OGGM will parse the
        information from the glacier directories found in the working
        directory. It is required for new runs.
    reset : bool
        delete the existing glacier directories if found.
    force : bool
        setting `reset=True` will trigger a yes/no question to the user. Set
        `force=True` to avoid this.
    dem_source : str
        the source to pick from (default: NASADEM and COPDEM)
    keep_dem_folders : bool
        the default is to delete the other DEM directories to save space.
        Set this to True to prevent that (e.g. for sensitivity tests)
    Returns
    -------
    gdirs : list of :py:class:`oggm.GlacierDirectory` objects
        the initialised glacier directories

    Notes
    -----
    This task is very similar to init_glacier_regions, with one main
    difference: it does not process the DEMs for this glacier.
    Eventually, init_glacier_regions will be deprecated and removed from the
    codebase.
    """

    if resolution == 'default':
        base_url = DEMS_URL
    elif resolution == 'lr':
        base_url = DEMS_URL
    elif resolution == 'hr':
        base_url = DEMS_HR_URL
    else:
        raise InvalidParamsError('`resolution` should be of `lr` or `hr`')

    gdirs = workflow.init_glacier_directories(rgidf, reset=reset, force=force,
                                              prepro_base_url=base_url,
                                              from_prepro_level=1,
                                              prepro_rgi_version='62')

    workflow.execute_entity_task(select_dem_from_dir, gdirs,
                                 dem_source=dem_source,
                                 keep_dem_folders=keep_dem_folders)

    return gdirs


@utils.entity_task(log, writes=['dem'])
def select_dem_from_dir(gdir, dem_source=None, keep_dem_folders=False):
    """Select a DEM from the ones available in an RGI-TOPO glacier directory.

    Parameters
    ----------
    gdir : :py:class:`oggm.GlacierDirectory`
        the glacier directory
    dem_source : str
        the source to pick from (default: NASADEM and COPDEM)
    keep_dem_folders : bool
        the default is to delete the other DEM directories to save space.
        Set this to True to prevent that (e.g. for sensitivity tests)
    """

    # Start by deleting noise
    for fn in ['log.txt', 'diagnostics.json']:
        fp = os.path.join(gdir.dir, fn)
        if os.path.exists(fp):
            os.remove(fp)

    sources = [f.name for f in os.scandir(gdir.dir) if f.is_dir()]

    if dem_source is None:
        if 'NASADEM' in sources:
            dem_source = 'NASADEM'
        else:
            dem_source = 'COPDEM'

    if dem_source not in sources:
        raise RuntimeError('source {} not in folder'.format(dem_source))

    shutil.copyfile(os.path.join(gdir.dir, dem_source, 'dem.tif'),
                    gdir.get_filepath('dem'))
    shutil.copyfile(os.path.join(gdir.dir, dem_source, 'dem_source.txt'),
                    gdir.get_filepath('dem_source'))

    if not keep_dem_folders:
        for source in sources:
            shutil.rmtree(os.path.join(gdir.dir, source))
