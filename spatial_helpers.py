# spatial_helpers.py
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon, LineString

def json_to_polygon(coord_list):
    """
    Converts a list of dicts [{'lat': y, 'lng': x}, ...] into a PostGIS Polygon.
    """
    if not coord_list or len(coord_list) < 3:
        return None
    
    # Extract coordinates as (longitude, latitude)
    points = [(point['lng'], point['lat']) for point in coord_list]
    
    # PostGIS Polygons must be explicitly closed (first and last point must be identical)
    if points[0] != points[-1]:
        points.append(points[0])
        
    return from_shape(Polygon(points), srid=4326)

def json_to_linestring(coord_list):
    """
    Converts a list of dicts [{'lat': y, 'lng': x}, ...] into a PostGIS LineString.
    """
    if not coord_list or len(coord_list) < 2:
        return None
        
    points = [(point['lng'], point['lat']) for point in coord_list]
    return from_shape(LineString(points), srid=4326)