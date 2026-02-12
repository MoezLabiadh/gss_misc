"""
Function to export a GeoDataFrame to KML format using simplekml.
Supports Points, MultiPoints, Lines, MultiLines, Polygons, and MultiPolygons.
Enables control over styling and optional label visibility.
"""

import os
import geopandas as gpd
import simplekml


def esri_to_gdf(aoi):
    """Returns a Geopandas file (gdf) based on 
       an ESRI format vector (shp or featureclass/gdb)"""
    
    if '.shp' in aoi: 
        gdf = gpd.read_file(aoi)
    
    elif '.gdb' in aoi:
        l = aoi.split('.gdb')
        gdb = l[0] + '.gdb'
        fc = os.path.basename(aoi)
        gdf = gpd.read_file(filename=gdb, layer=fc)
        
    else:
        raise Exception('Format not recognized. Please provide a shp or featureclass (gdb)!')
    
    return gdf


def export_kml(gdf, output_path, label_col=None, show_labels=True,
               line_color=simplekml.Color.red, line_width=1.5,
               poly_fill=0, poly_color=None,
               label_color=simplekml.Color.white, label_scale=1,
               point_icon_scale=1, point_icon_color=simplekml.Color.red):
    """
    Export a GeoDataFrame to KML format.

    Parameters
    ----------
    gdf : GeoDataFrame
        Input geodataframe (will be reprojected to EPSG:4326 if needed).
    output_path : str
        Output KML file path.
    label_col : str, optional
        Column name to use for labels. If None, no labels are added.
    show_labels : bool
        Whether to display labels. Default True.
    line_color : simplekml.Color
        Color for lines and polygon outlines. Default red.
    line_width : float
        Width of lines and polygon outlines. Default 1.5.
    poly_fill : int
        0 = no fill, 1 = fill. Default 0.
    poly_color : simplekml.Color, optional
        Fill color for polygons. Default None (transparent).
    label_color : simplekml.Color
        Label text color. Default white.
    label_scale : float
        Label text scale. Default 1.
    point_icon_scale : float
        Scale of point icons. Default 1. Set to 0 to hide icons.
    point_icon_color : simplekml.Color
        Color of point icons. Default red.
    """
    
    # Reproject to WGS84 if needed
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    kml = simplekml.Kml()

    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None:
            continue

        label = str(row[label_col]) if label_col and label_col in gdf.columns else ""
        geom_type = geom.geom_type

        # ---- POINTS ----
        if geom_type == "Point":
            pt = kml.newpoint(name=label if show_labels else "", 
                              coords=[(geom.x, geom.y)])
            pt.style.iconstyle.scale = point_icon_scale
            pt.style.iconstyle.color = point_icon_color
            pt.style.labelstyle.scale = label_scale if show_labels and label else 0
            pt.style.labelstyle.color = label_color

        elif geom_type == "MultiPoint":
            multi = kml.newmultigeometry(name=label if show_labels else "")
            for point in geom.geoms:
                pt = multi.newpoint(coords=[(point.x, point.y)])
            multi.style.iconstyle.scale = point_icon_scale
            multi.style.iconstyle.color = point_icon_color
            multi.style.labelstyle.scale = label_scale if show_labels and label else 0
            multi.style.labelstyle.color = label_color

        # ---- LINES ----
        elif geom_type == "LineString":
            ls = kml.newlinestring(name=label if show_labels else "",
                                   coords=[(x, y) for x, y in geom.coords])
            ls.style.linestyle.color = line_color
            ls.style.linestyle.width = line_width
            ls.style.labelstyle.scale = label_scale if show_labels and label else 0
            ls.style.labelstyle.color = label_color

        elif geom_type == "MultiLineString":
            multi = kml.newmultigeometry(name=label if show_labels else "")
            for line in geom.geoms:
                multi.newlinestring(coords=[(x, y) for x, y in line.coords])
            multi.style.linestyle.color = line_color
            multi.style.linestyle.width = line_width
            multi.style.labelstyle.scale = label_scale if show_labels and label else 0
            multi.style.labelstyle.color = label_color

        # ---- POLYGONS ----
        elif geom_type == "Polygon":
            pol = kml.newpolygon()
            pol.outerboundaryis = [(x, y) for x, y in geom.exterior.coords]
            for interior in geom.interiors:
                pol.innerboundaryis = [(x, y) for x, y in interior.coords]
            _style_polygon(pol, line_color, line_width, poly_fill, poly_color)

        elif geom_type == "MultiPolygon":
            multi = kml.newmultigeometry()
            for polygon in geom.geoms:
                pol = multi.newpolygon()
                pol.outerboundaryis = [(x, y) for x, y in polygon.exterior.coords]
                for interior in polygon.interiors:
                    pol.innerboundaryis = [(x, y) for x, y in interior.coords]
            _style_polygon(multi, line_color, line_width, poly_fill, poly_color)

        else:
            print(f"Warning: Unsupported geometry type '{geom_type}' skipped.")
            continue

        # ---- CENTROID LABELS FOR POLYGONS ----
        if geom_type in ("Polygon", "MultiPolygon") and show_labels and label:
            centroid = geom.centroid
            pt = kml.newpoint(name=label, coords=[(centroid.x, centroid.y)])
            pt.style.iconstyle.scale = 0
            pt.style.labelstyle.scale = label_scale
            pt.style.labelstyle.color = label_color

    kml.save(output_path)
    print(f"KML saved to: {output_path}")


def _style_polygon(kml_geom, line_color, line_width, poly_fill, poly_color):
    """Apply consistent styling to a polygon or multigeometry."""
    kml_geom.style.linestyle.color = line_color
    kml_geom.style.linestyle.width = line_width
    kml_geom.style.polystyle.fill = poly_fill
    if poly_fill and poly_color:
        kml_geom.style.polystyle.color = poly_color
    kml_geom.style.labelstyle.scale = 0  # labels handled by centroid points