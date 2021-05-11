#!/usr/bin/python3

from __future__ import absolute_import
import logging
import os
import uuid
from pathlib import Path
import xml.etree.ElementTree as ET
import click
import yaml
from osgeo import osr

def get_geo_ref_points(root):
    nrows = int(root.findall('./*/Tile_Geocoding/Size[@resolution="10"]/NROWS')[0].text)
    ncols = int(root.findall('./*/Tile_Geocoding/Size[@resolution="10"]/NCOLS')[0].text)

    ulx = int(root.findall('./*/Tile_Geocoding/Geoposition[@resolution="10"]/ULX')[0].text)
    uly = int(root.findall('./*/Tile_Geocoding/Geoposition[@resolution="10"]/ULY')[0].text)

    xdim = int(root.findall('./*/Tile_Geocoding/Geoposition[@resolution="10"]/XDIM')[0].text)
    ydim = int(root.findall('./*/Tile_Geocoding/Geoposition[@resolution="10"]/YDIM')[0].text)

    return {
        'ul': {'x': ulx, 'y': uly},
        'ur': {'x': ulx + ncols * abs(xdim), 'y': uly},
        'll': {'x': ulx, 'y': uly - nrows * abs(ydim)},
        'lr': {'x': ulx + ncols * abs(xdim), 'y': uly - nrows * abs(ydim)},
    }


def get_coords(geo_ref_points, spatial_ref):
    t = osr.CoordinateTransformation(spatial_ref, spatial_ref.CloneGeogCS())

    def transform(p):
        lon, lat, z = t.TransformPoint(p['x'], p['y'])
        return {'lon': lon, 'lat': lat}

    return {key: transform(p) for key, p in geo_ref_points.items()}


def prepare_dataset(path):
    root = ET.parse(str(path)).getroot()
    level = ('Level-2A')
    product_type = ('S2MSI2A')
    ct_time = root.findall('.//GENERATION_TIME')[0].text.split('T')[0] + " " + root.findall('.//GENERATION_TIME')[0].text.split('T')[1].split('Z')[0]

    root = ET.parse(str(path)).getroot()
    single_granule_archive = True
    items = []
    for granule in root.findall('.//Granule'):
     identifier = granule.get('granuleIdentifier')
    for imid in root.findall(".//Granule/"):
     items.append(imid.text)
    granules = {identifier : items}


    grouped_images = []
    documents = []
    for granule_id, images in granules.items():
        #print(images)
        images_ten_list = []
        images_twenty_list = []
        images_sixty_list = []
        images_classification = []
        img_data_path = str(path.parent.joinpath('GRANULE', granule_id, 'IMG_DATA'))

        gran_path = str(path.parent.joinpath('GRANULE', granule_id, granule_id[:-7].replace('MSI', 'MTD') + '.xml'))
        if not Path(gran_path).exists():
            gran_path = str(path.parent.joinpath(images[0]))
            gran_path = str(Path(gran_path).parents[2].joinpath('MTD_TL.xml'))
        root = ET.parse(gran_path).getroot()

        if not Path(img_data_path).exists():
            img_data_path = str(Path(path).parent)

        if single_granule_archive is False:
            img_data_path = img_data_path + str(Path('GRANULE').joinpath(granule_id, 'IMG_DATA'))

        root = ET.parse(gran_path).getroot()
        sensing_time = root.findall('./*/SENSING_TIME')[0].text.split('T')[0] + " " + root.findall('./*/SENSING_TIME')[0].text.split('T')[1].split('.')[0]

        for image in images:
            classification_list = ['SCL']
            ten_list = ['B02_10m', 'B03_10m', 'B04_10m', 'B08_10m']
            twenty_list = ['B05_20m', 'B06_20m', 'B07_20m', 'B11_20m', 'B12_20m', 'B8A_20m']
            sixty_list = ['B01_60m', 'B09_60m']


            for item in classification_list:
                if item in image:
                    if '20m' in image:
                        images_classification.append(os.path.join(str(path.parent), image + ".jp2"))

            for item in ten_list:
                if item in image:
                    images_ten_list.append(os.path.join(str(path.parent), image + ".jp2"))
                    grouped_images.append(os.path.join(str(path.parent), image + ".jp2"))
            for item in twenty_list:
                if item in image:
                    images_twenty_list.append(os.path.join(str(path.parent), image + ".jp2"))
                    grouped_images.append(os.path.join(str(path.parent), image + ".jp2"))
            for item in sixty_list:
                if item in image:
                    images_sixty_list.append(os.path.join(str(path.parent), image + ".jp2"))
                    grouped_images.append(os.path.join(str(path.parent), image + ".jp2"))

        station = root.findall('./*/Archiving_Info/ARCHIVING_CENTRE')[0].text

        cs_code = root.findall('./*/Tile_Geocoding/HORIZONTAL_CS_CODE')[0].text
        spatial_ref = osr.SpatialReference()

        spatial_ref.SetFromUserInput(cs_code)

        spectral_dict = {image[-11:-4]: {'path': str(Path(image)), 'layer': 1, } for image in grouped_images}
        scl_dict = {'SCL_20m': {'path': str(Path(classification)), 'layer': 1, } for classification in
                    images_classification}
        spectral_dict.update(scl_dict)

        geo_ref_points = get_geo_ref_points(root)

        documents.append({
            'id': str(uuid.uuid4()),
            'processing_level': level.replace('Level-', 'L'),
            'product_type': product_type,
            'creation_dt': ct_time,
            'platform': {'code': 'SENTINEL_2'},
            'instrument': {'name': 'MSI'},
            'acquisition': {'groundstation': {'code': station}},
            'extent': {
                'from_dt': sensing_time,
                'to_dt': sensing_time,
                'center_dt': sensing_time,
                'coord': get_coords(geo_ref_points, spatial_ref),
            },
            'format': {'name': 'JPEG2000'},
            'grid_spatial': {
                'projection': {
                    'geo_ref_points': geo_ref_points,
                    'spatial_reference': spatial_ref.ExportToWkt(),
                }
            },
        'image': {
                'bands': spectral_dict
            },

            'lineage': {'source_datasets': {}},
        })
    return documents



@click.command(
    help="Prepare Sentinel-2 Level 2 data from multiple sources for ingestion into the Data Cube. "
         "eg. 'python sen2cor_prepare.py <input>.SAFE --output <outfile>.yaml', in the terminal"
         "for preparing multiple datsets, use '*' as wildcard, e.g. 'S*' for all datasets satarting with 'S'")
@click.argument('datasets',
                type=click.Path(exists=True, readable=True, writable=False),
                nargs=-1)
@click.option('--output', help="Write datasets into this directory",
              type=click.Path(exists=False, writable=True, dir_okay=True))

def main(datasets, output):
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.INFO)

    for dataset in datasets:

        path = Path(dataset).absolute()
        if path.is_dir():
            for file in os.listdir(path):
                if file.endswith(".xml") and file.startswith("MTD"):
                    path = Path(os.path.join(path, file))
        if path.suffix != '.xml':
            raise RuntimeError('want xml')

        logging.info("Processing %s", path)

        documents = prepare_dataset(path)

        output_path = Path(output)
        if 'xml' in str(path):
            yaml_path = output_path.joinpath(path.parent.name + '.yaml')
        else:
            yaml_path = output_path.joinpath(path.name + '.yaml')

        if documents:
            logging.info("Writing %s dataset(s) into %s", len(documents), yaml_path)
            with open(yaml_path, 'w') as stream:
                yaml.dump_all(documents, stream)
        else:
            logging.info("No Datasets, tschuess!")


if __name__ == "__main__":
    main()

""" python3 prep_j2_to_yaml.py /media/pak44ck/4e59e129-3a08-43a9-9890-45d3981b0af6/data_processed/sen2cor_output/*.SAFE --output /media/pak44ck/4e59e129-3a08-43a9-9890-45d3981b0af6/datacube_utils/scene_yaml/ """