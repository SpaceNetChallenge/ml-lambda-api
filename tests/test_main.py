import os
import pytest
## Note, for mac osx compatability import something from shapely.geometry before importing fiona or geopandas
## https://github.com/Toblerity/Shapely/issues/553  * Import shapely before rasterio or fioana
import logging
import requests
from PIL import Image
from io import BytesIO
from urllib.parse import urljoin
import numpy as np


api_endpoint = os.getenv('ML_LAMBDA_API_Endpoint')
if api_endpoint is None:
    raise NameError("ML_LAMBDA_API_Endpoint_Endpoint environement variable is undefined")



stac_item__url_mlexport = 'https://spacenet-stac.s3.amazonaws.com/ml-exports/task_id_1234/TernausV2_Segmentation.json'
zoom=17
x_coord=23576
y_coord=51385



PREFIX = os.path.join(os.path.dirname(__file__), 'fixtures')

logging.basicConfig(format='%(levelname)s:%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)


def test_import():
    print("Import Success")

def test_stac_bounds():

    api_location = urljoin(api_endpoint, 'stac/bounds?url={stac_item_url}'.format(stac_item_url=stac_item__url_mlexport))

    r = requests.get(api_location)
    data = r.json()

    assert r.status_code == 200
    assert r.headers['Content-Type'] == 'application/json'
    assert data['geometry']['type'] == "Polygon"

def test_stac_bounds():

    api_location = urljoin(api_endpoint, 'stac/bounds?url={stac_item_url}'.format(stac_item_url=stac_item__url_mlexport))

    r = requests.get(api_location)

    data = r.json()

    assert r.status_code == 200
    assert r.headers['Content-Type'] == 'application/json'
    assert data['geometry']['type'] == "Polygon"


def test_stac_tiles():


    api_location = urljoin(api_endpoint, 'stac/tiles/{z}/{x}/{y}.jpg?url={stac_item_url}'.format(z=zoom,
                                                                                                x=x_coord,
                                                                                                y=y_coord,
                                                                                                stac_item_url=stac_item__url_mlexport))


    r = requests.get(api_location)

    if r.status_code==200:
        data = np.asarray(Image.open(BytesIO(r.content)))
    else:
        raise NameError("ML_LAMBDA_API_Endpoint_Endpoint stac_tile bad response")


    assert r.status_code == 200
    assert data.shape == (512, 512, 3)

def test_stac_tiles_out_of_bounds():


    api_location = urljoin(api_endpoint, 'stac/tiles/{z}/{x}/{y}.jpg?url={stac_item_url}'.format(z=zoom,
                                                                                                 x=x_coord,
                                                                                                 y=0,
                                                                                                 stac_item_url=stac_item__url_mlexport))

    r = requests.get(api_location)

    assert r.status_code == 500


def test_stac_summary():
    api_location = urljoin(api_endpoint, 'stac/summary/{z}/{x}/{y}.jpg?url={stac_item_url}'.format(z=zoom,
                                                                                                 x=x_coord,
                                                                                                 y=y_coord,
                                                                                                 stac_item_url=stac_item__url_mlexport))

    r = requests.get(api_location)

    if r.status_code == 200:
        data = r.json()
    else:
        raise NameError("ML_LAMBDA_API_Endpoint_Endpoint summary bad response")

    assert r.status_code == 200
    assert "pixel_count" in data
    assert "object_count" in data
    assert "object_list" in data


def test_stac_summary_out_of_bounds():

    api_location = urljoin(api_endpoint, 'stac/summary/{z}/{x}/{y}.jpg?url={stac_item_url}'.format(z=zoom,
                                                                                                   x=x_coord,
                                                                                                   y=0,
                                                                                                   stac_item_url=stac_item__url_mlexport))

    r = requests.get(api_location)

    assert r.status_code == 500










