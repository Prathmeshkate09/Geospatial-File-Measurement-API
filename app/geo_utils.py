import os
import zipfile
import shutil
import geopandas as gpd
import json

def extract_zip(zip_path: str, extract_to: str):
    """Extracts a zip file to the specified directory."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def find_shapefile(directory: str) -> str:
    """Finds the main .shp file in a directory."""
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".shp"):
                return os.path.join(root, file)
    return None

def process_file_measurements(file_path: str, original_filename: str):
    """
    Reads a geospatial file, extracts features, and calculates measurements.
    Handles Shapefiles (zipped) and KML.
    Returns: (features_list, crs_string)
    """
    temp_dir = None
    read_path = file_path

    # If it's a zip (assumed Shapefile), extract it first
    if original_filename.lower().endswith('.zip'):
        temp_dir = file_path + "_extracted"
        extract_zip(file_path, temp_dir)
        read_path = find_shapefile(temp_dir)
        if not read_path:
            raise ValueError("No .shp file found in the zip archive.")
    
    # Setup fiona KML driver if it's KML
    if original_filename.lower().endswith('.kml'):
        import fiona
        fiona.drvsupport.supported_drivers['KML'] = 'rw'
    
    # Read the data using GeoPandas
    try:
        gdf = gpd.read_file(read_path)
    except Exception as e:
        raise ValueError(f"Failed to read geospatial file: {str(e)}")
        
    # Drop Z dimension to avoid PostGIS 3D insertion errors for 2D columns
    import shapely
    if 'geometry' in gdf and gdf.geometry is not None:
        gdf.geometry = shapely.force_2d(gdf.geometry)

    original_crs = str(gdf.crs) if gdf.crs else "UNKNOWN"
    
    # We need a geographic CRS to store in DB as EPSG:4326.
    # But for calculation, we need a projected CRS.
    
    # Keep a copy for db storage in EPSG:4326
    gdf_4326 = gdf.copy()
    if gdf_4326.crs is not None and gdf_4326.crs.to_epsg() != 4326:
        gdf_4326 = gdf_4326.to_crs(epsg=4326)
    elif gdf_4326.crs is None:
        # Assume 4326 if none provided, standard fallback
        gdf_4326.set_crs(epsg=4326, inplace=True)

    # For measurement calculations, we transform to an appropriate projected CRS.
    # geopandas provides `estimate_utm_crs()` which picks the best UTM zone
    # based on the bounds of the geometries.
    if gdf.crs and gdf.crs.is_geographic:
        try:
            projected_crs = gdf.estimate_utm_crs()
            gdf_projected = gdf.to_crs(projected_crs)
        except Exception:
            # Fallback if UTM estimation fails (e.g. global dataset): Web Mercator or World Mollweide
            gdf_projected = gdf.to_crs("ESRI:54009") # Mollweide for area
    elif gdf.crs is None:
        # Assume it's already 4326 to estimate UTM
        gdf.set_crs(epsg=4326, inplace=True)
        try:
            projected_crs = gdf.estimate_utm_crs()
            gdf_projected = gdf.to_crs(projected_crs)
        except Exception:
             gdf_projected = gdf
    else:
        # Already projected
        gdf_projected = gdf

    features = []
    
    for index, row in gdf_projected.iterrows():
        geom = row.geometry
        if geom is None:
            continue
            
        geom_type = geom.geom_type
        area = None
        length = None
        
        # Calculate measurements based on geometry type
        if geom_type in ['Polygon', 'MultiPolygon']:
            area = float(geom.area)
        elif geom_type in ['LineString', 'MultiLineString']:
            length = float(geom.length)
        
        
        # Original geometry for DB (in 4326)
        geom_4326_wkt = gdf_4326.iloc[index].geometry.wkt if gdf_4326.iloc[index].geometry else None

        # Extract properties
        props = row.drop('geometry').to_dict()

        features.append({
            "feature_index": index,
            "geom_type": geom_type,
            "area": area,
            "length": length,
            "geometry_wkt": geom_4326_wkt,
            "properties": json.dumps(props)
        })

    # Cleanup extracted temp dir
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        
    return features, original_crs
