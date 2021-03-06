import signal_to_noise as snr
import random_dither
from astropy import units as u
from astropy.coordinates import SkyCoord
import yaml
config = yaml
config_file = 'performance.yaml'
config = dict()

with open(config_file, 'r') as f:
    config = yaml.load(f.read())


def create_imager_array():
    """ Create an instance of ImagerArray class present in the module 'snr'

    Args:
        config: config file that stores the information about the optics, cameras, bands, and imagers, required to create
        and ImagerArray object.
    """

    optics = dict()
    cameras = dict()
    filters = dict()
    psfs = dict()
    imagers = dict()

    # Setup imagers
    for name, imager_info in config['imagers'].items():
        optic_name = imager_info['optic']
        try:
            # Try to get from cache
            optic = optics[optic_name]
        except KeyError:
            # Create optic from this imager
            optic_info = config['optics'][optic_name]
            optic = snr.Optic(**optic_info)

            # Put in cache
            optics[optic_name] = optic
            camera_name = imager_info['camera']
        try:
            # Try to get from cache
            camera = cameras[camera_name]
        except KeyError:
            # Create camera for this imager
            camera_info = config['cameras'][camera_name]
            if type(camera_info['resolution']) == str:
                camera_info['resolution'] = [int(a) for a in camera_info['resolution'].split(',')]
            camera = snr.Camera(**camera_info)

            # Put in cache
            cameras[camera_name] = camera

        filter_name = imager_info['filter']
        try:
            # Try to get from cache
            filter = filters[filter_name]
        except KeyError:
            # Create optic from this imager
            filter_info = config['filters'][filter_name]
            filter = snr.Filter(**filter_info)

            # Put in cache
            filters[filter_name] = filter

        psf_name = imager_info['psf']
        try:
            # Try to get from cache
            psf = psfs[psf_name]
        except KeyError:
            # Create optic from this imager
            psf_info = config['psfs'][psf_name]
            psf = snr.Moffat_PSF(**psf_info)

            # Put in cache
            psfs[psf_name] = psf

        imagers[name] = snr.Imager(optic, camera, filter, imager_info.get('num_imagers', 1), imager_info.get
                                   ('num_per_computer', 1), psf)
    imager_array = snr.ImagerArray(imagers)
    return imager_array


def get_hdr_target_list(imager_array, ra_dec, name, minimum_magnitude, imager_name, long_exposures=1,
                        dither_function=random_dither.dither_dice9,
                        dither_parameters={'pattern_offset': 0.5 * u.degree, 'random_offset': 0.1 * u.degree},
                        factor=2, maximum_exptime=300 * u.second, priority=100, maximum_magnitude=None):
    """ Returns a target list

    Args:
        imager_array: An instance of ImagerArray class
        ra_dec: Astropy coordinates of the target
        name: name of the target
        minimum_magnitude: minimum magnitude that we want to observe before saturation
        imager_name: name of the imager that we want to use to generate the exposure time array
        long_exposures: number of long exposures wanted
        dither_function: dither function that we want to use
        dither_parameters: parameters required for the dither function
        factor: increment step between successive exposure times, up until the maximum exposure time
        maximum_exptime: maximum exposure time that we want to use for the imagers
        priority: priority value assigned to the target
        maximum_magnitude(optional): maximum magnitude that we want to observe at a snr of 5.0

    """

    if not isinstance(ra_dec, SkyCoord):
        ra_dec = SkyCoord(ra_dec)

    explist = imager_array.exposure_time_array(minimum_magnitude=minimum_magnitude,
                                               name=imager_name, long_exposures=long_exposures,
                                               factor=factor, maximum_exptime=maximum_exptime,
                                               maximum_magnitude=maximum_magnitude)
    target_list = []
    position_list = dither_function(ra_dec, **dither_parameters, loop=len(explist))
    for i in range(0, len(explist)):
        target = {}
        if ra_dec.obstime is not None:
            target['epoch'] = ra_dec.obstime
        if ra_dec.equinox is not None:
            target['equinox'] = ra_dec.equinox
        target['frame'] = ra_dec.frame.name
        target['name'] = name
        target['position'] = position_list[i].to_string('hmsdms')
        target['priority'] = priority
        target['visit'] = {'primary_nexp': 1, 'primary_exptime': explist[i].value}
        target_list.append(target)

    return target_list
