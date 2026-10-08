
import json
from app.geo_utils import process_file_measurements

def test_process_file_measurements_kml(tmp_path):
    # Create a dummy KML file for testing geometry extraction
    kml_content = """<?xml version="1.0" encoding="utf-8" ?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document id="root_doc">
<Schema name="sample" id="sample">
    <SimpleField name="Name" type="string"></SimpleField>
    <SimpleField name="Description" type="string"></SimpleField>
</Schema>
<Folder><name>sample</name>
  <Placemark>
    <name>Test Polygon</name>
    <ExtendedData><SchemaData schemaUrl="#sample">
        <SimpleData name="Name">Test Polygon</SimpleData>
        <SimpleData name="Description">A simple square polygon</SimpleData>
    </SchemaData></ExtendedData>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>-122.084,37.422,0 -122.086,37.422,0 -122.086,37.420,0 -122.084,37.420,0 -122.084,37.422,0</coordinates></LinearRing></outerBoundaryIs></Polygon>
  </Placemark>
</Folder>
</Document></kml>"""
    
    kml_file = tmp_path / "test.kml"
    kml_file.write_text(kml_content)
    
    features, crs = process_file_measurements(str(kml_file), "test.kml")
    
    assert len(features) == 1
    feature = features[0]
    
    assert feature["geom_type"] == "Polygon"
    assert feature["area"] is not None
    assert feature["area"] > 0
    assert feature["length"] is None
    
    props = json.loads(feature["properties"])
    assert props["Name"] == "Test Polygon"
