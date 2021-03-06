import gevent.monkey

gevent.monkey.patch_all()

import os
import ujson

from gevent.pool import Pool
from io import BytesIO
from PIL import Image
from urllib.request import urlopen, Request
from tqdm import tqdm

POOL_SIZE = 10
BASE_URL = "https://isic-archive.com/api/v1"

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
ISIC_ARCHIVE_INPUTS_PATH = os.path.join(BASE_PATH, "data", "isic_archive", "inputs")
ISIC_ARCHIVE_TARGETS_PATH = os.path.join(BASE_PATH, "data", "isic_archive", "targets")

if not os.path.exists(ISIC_ARCHIVE_INPUTS_PATH):
    os.makedirs(ISIC_ARCHIVE_INPUTS_PATH)

if not os.path.exists(ISIC_ARCHIVE_TARGETS_PATH):
    os.makedirs(ISIC_ARCHIVE_TARGETS_PATH)


def get_image_ids(limit, offset):
    endpoint = "image"
    url = f"{BASE_URL}/{endpoint}?limit={limit}&offset={offset}"

    request = Request(url)
    response = urlopen(request)
    content = ujson.loads(response.read())

    return content


def get_all_image_ids():
    batch_size = 1000
    offset = 0

    image_ids = []
    while True:
        print(f"Getting image IDs - Offset: {offset}")
        batch_image_ids = get_image_ids(batch_size, offset)
        image_ids.extend(batch_image_ids)
        offset += batch_size

        if len(batch_image_ids) < 1000:
            break

    return image_ids


def get_segmentation_ids_for_image(image_id):
    endpoint = "segmentation"
    url = f"{BASE_URL}/{endpoint}?imageId={image_id}"

    request = Request(url)
    response = urlopen(request)
    content = ujson.loads(response.read())

    return content


def download_image(image_id, save_to=None):
    endpoint = f"image/{image_id}/download"
    url = f"{BASE_URL}/{endpoint}"

    request = Request(url)
    try:
        response = urlopen(request)
    except Exception as e:
        print(f"{e.__class__.__name__} raised while downloading image from {url}")
        return
    img_bytes = BytesIO(response.read())
    img = Image.open(img_bytes)

    if save_to is not None:
        img.save(save_to)

    return img


def download_mask(image_id, save_to=None):
    endpoint = f"segmentation/{image_id}/mask"
    url = f"{BASE_URL}/{endpoint}"

    request = Request(url)
    try:
        response = urlopen(request)
    except Exception as e:
        print(f"{e.__class__.__name__} raised while downloading image mask from {url}")
        return
    img_bytes = BytesIO(response.read())
    img = Image.open(img_bytes)

    if save_to is not None:
        img.save(save_to)

    return img


def download_all(image_id, image_name, progress_bar=None):
    fpath = os.path.join(ISIC_ARCHIVE_INPUTS_PATH, f"{image_name}.jpg")
    if not os.path.isfile(fpath):
        download_image(image_id, fpath)

    segmentations = get_segmentation_ids_for_image(image_id)
    for i, segmentation in enumerate(segmentations):
        fpath = os.path.join(ISIC_ARCHIVE_TARGETS_PATH, f"{image_name}_segmentation_{i}.png")
        if not os.path.isfile(fpath):
            download_mask(segmentation["_id"], fpath)

    if progress_bar is not None:
        progress_bar.update(n=1)


def asynchronous():
    image_data = get_all_image_ids()

    print(f"Downloading {len(image_data)} lesion images from ISIC Archive")

    pool = Pool(POOL_SIZE)
    progress_bar = tqdm(image_data)
    [pool.spawn(download_all, image["_id"], image["name"], progress_bar) for image in image_data]


if __name__ == "__main__":
    asynchronous()
