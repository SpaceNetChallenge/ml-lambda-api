"""app.main: handle request for lambda-tiler"""

import re
import json
import urllib.request
import numpy as np
from rasterio import features
from rio_tiler import main
from rio_tiler.utils import array_to_img, linear_rescale, get_colormap
from rio_tiler.utils import expression, b64_encode_img
from lambda_proxy.proxy import API
from distutils import util

APP = API(app_name="ml-lambda-api")


@APP.route('/stac/bounds', methods=['GET'], cors=True)
def stac_bounds():
    """Handle bounds requests."""
    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}
    # TODO: next line doesn't handle case of empty query
    address = query_args['url']

    with urllib.request.urlopen(address) as url:
        data = json.loads(url.read().decode())

    return ('OK', 'application/json',
            json.dumps({"geometry": data['geometry']}))


@APP.route('/stac/info', methods=['GET'], cors=True)
def stac_info():
    """Handle info requests, returning the entire STAC .json."""
    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}
    # TODO: next line doesn't handle case of empty query
    address = query_args['url']

    with urllib.request.urlopen(address) as url:
        data = json.loads(url.read().decode())

    return ('OK', 'application/json', json.dumps(data))


@APP.route('/stac/tiles/<int:z>/<int:x>/<int:y>.<ext>', methods=['GET'],
           cors=True)
def stac_tile_image(tile_z, tile_x, tile_y, tileformat):
    """Handle tile requests, returning b64-encoded image."""
    if tileformat == 'jpg':
        tileformat = 'jpeg'
    # get query arguments from request
    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}
    tile, mask, _ = get_stac_tile(tile_x, tile_y, tile_z, query_args)
    # linearStretch: should pixel value [min, max] be rescaled to [1, 255]
    linearStretch = query_args.get('linearStretch', 'False')
    if util.strtobool(linearStretch):
        tile = linear_rescale(tile, in_range=(np.min(tile), np.max(tile)))
    img = array_to_img(tile, mask=mask)
    str_img = b64_encode_img(img, tileformat)

    return ('OK', f'image/{tileformat}', str_img)


@APP.route('/stac/summary/<int:z>/<int:x>/<int:y>.<ext>', methods=['GET'],
           cors=True)
def stac_tile_summary(tile_z, tile_x, tile_y, tileformat):
    """Handle tile summary requests."""
    if tileformat == 'jpg':
        tileformat = 'jpeg'
    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    tile, mask, stac_data = get_stac_tile(tile_x, tile_y, tile_z, query_args)

    asset_key = query_args.get('asset_key', 'raster')
    asset_data = stac_data['assets'][asset_key]
    tile_mask = tile >= asset_data['binary_threshold']
    tilesize = int(query_args.get('tile', '512'))

    if tilesize == 512:
        asset_data['pixel_count'] = np.sum(tile_mask[0])/2
    else:
        asset_data['pixel_count'] = np.sum(tile_mask[0])

    geom_list = []
    # Extract feature shapes and values from the array.
    for geom, val in features.shapes(tile_mask[0].astype(np.uint8), mask=mask):
        geom_list.append(geom)

    asset_data['object_count'] = len(geom_list)
    asset_data['object_list'] = geom_list

    return ('OK', 'application/json', json.dumps(asset_data))


@APP.route('/bounds', methods=['GET'], cors=True)
def cog_bounds():
    """Handle bounds requests."""
    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}
    address = query_args['url']
    info = main.bounds(address)
    return ('OK', 'application/json', json.dumps(info))


@APP.route('/tiles/<int:z>/<int:x>/<int:y>.<ext>', methods=['GET'], cors=True)
def cog_tile_image(tile_z, tile_x, tile_y, tileformat):
    """Handle tile requests."""
    if tileformat == 'jpg':
        tileformat = 'jpeg'

    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}
    tile, mask = get_tile(tile_x, tile_y, tile_z, query_args['url'],
                          query_args)
    linearStretch = query_args.get('linearStretch')
    if linearStretch is not None:
        if util.strtobool(linearStretch):
            tile = linear_rescale(tile, in_range=(np.min(tile), np.max(tile)))
    img = array_to_img(tile, mask=mask)
    str_img = b64_encode_img(img, tileformat)

    return ('OK', f'image/{tileformat}', str_img)


@APP.route('/processing/<int:z>/<int:x>/<int:y>.<ext>', methods=['GET'],
           cors=True)
def ratio(tile_z, tile_x, tile_y, tileformat):
    """Handle processing requests.
    NW note: I don't know what this does."""
    if tileformat == 'jpg':
        tileformat = 'jpeg'

    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}
    address = query_args['url']
    ratio_value = query_args['ratio']
    tilesize = query_args.get('tile', 512)
    tilesize = int(tilesize) if isinstance(tilesize, str) else tilesize

    tile, mask = expression(address,
                            tile_x,
                            tile_y,
                            tile_z,
                            ratio_value,
                            tilesize=tilesize)

    if len(tile.shape) == 2:
        tile = np.expand_dims(tile, axis=0)
    range_value = query_args.get('range', [-1, 1])
    rtile = np.where(mask, linear_rescale(tile, in_range=range_value,
                                          out_range=[0, 255]),
                     0).astype(np.uint8)
    img = array_to_img(rtile, color_map=get_colormap(name='cfastie'),
                       mask=mask)
    str_img = b64_encode_img(img, tileformat)
    return ('OK', f'image/{tileformat}', str_img)


@APP.route('/favicon.ico', methods=['GET'], cors=True)
def favicon():
    """Favicon."""
    return('NOK', 'text/plain', '')


# HELPER FUNCTIONS #

def get_tile(tile_x, tile_y, tile_z, raster_url, query_args):
    """Get an image tile and mask for a STAC or COG query."""
    # get indexes of RGB channels from request if provided, otherwise (1, 2, 3)
    indexes = query_args.get('indexes')
    if indexes:
        indexes = tuple(int(s) for s in re.findall(r'\d+', indexes))
    else:
        indexes = (1, 2, 3)

    # get desired tile extent from request
    tilesize = int(query_args.get('tile', '512'))
    # get nodata value
    nodata = query_args.get('nodata')
    nodata = int(nodata) if nodata is not None else None
    # next line is rio_tiler.main, reads in tile and mask arrays.
    tile, mask = main.tile(raster_url, tile_x, tile_y, tile_z, indexes=indexes,
                           tilesize=tilesize, nodata=nodata)

    return tile, mask


def get_stac_tile(tile_x, tile_y, tile_z, query_args):
    """Helper function to get image tile and mask."""
    address = query_args['url']
    # Read Stac File
    with urllib.request.urlopen(address) as url:
        stac_data = json.loads(url.read().decode())
    # asset_key indicates what type of data - defaults to raster if not passed
    asset_key = query_args.get('asset_key', 'raster')
    # get URL for raster
    raster_url = stac_data['assets'][asset_key]['href']
    tile, mask = get_tile(tile_x, tile_y, tile_z, raster_url, query_args)

    return tile, mask, stac_data
