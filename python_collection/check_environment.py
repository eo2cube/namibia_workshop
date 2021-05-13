import importlib

packages = ['geopandas', 'sklearn', 'contextily', 'folium', 'mgwr', 'pysal']

bad = []
for package in packages:
    try:
        importlib.import_module(package)
    except ImportError:
        bad.append("Can't import %s" % package)
else:
    if len(bad) > 0:
        print('The environment is not ready:)
        print('\n'.join(bad))
    else:
        try:
            import geopandas
            countries = geopandas.read_file("zip://./data/ne_110m_admin_0_countries.zip")
            print("Everything seems to be creamy!")
        except Exception as e:
            print("Countries shapefile cant be used, check environment!")
            print(e)

