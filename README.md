# Geospatial File Measurement API

This is a production-ready backend service built with **FastAPI** that accepts geospatial files (Shapefile zip archives and KMLs), extracts their features, and calculates geometric measurements (Area for Polygons, Length for LineStrings).

## Architecture & Design Decisions

### Tech Stack
*   **FastAPI**: Used for the web framework due to its high performance, native async support, and excellent auto-generated Swagger documentation.
*   **PostgreSQL + PostGIS**: The database choice for production geospatial applications. It allows for robust storage of geometries.
*   **Celery + Redis**: Chosen to handle file processing asynchronously. Geospatial files can be large and CPU-intensive to parse and project. Performing this in the main request thread would lead to timeouts.
*   **GeoPandas / PyProj**: Used for reading the shapefiles/KMLs and performing CRS transformations.
*   **Docker**: Encapsulates the complex system-level dependencies required by GDAL and GEOS, making the application perfectly reproducible.

### CRS Handling Strategy
Handling Coordinate Reference Systems (CRS) correctly is critical. Geographic CRSs (like `EPSG:4326` using Latitude/Longitude) cannot be used to accurately calculate distance or area in meters. 

When a file is uploaded, the application:
1. Reads the features using `GeoPandas`.
2. Estimates an appropriate projected UTM zone for the specific bounds of the geometries using `estimate_utm_crs()`.
3. Projects the geometries to this local Cartesian coordinate system.
4. Calculates accurate area and length measurements.
5. Saves the geometries back in their original format to the database for standardization.

## Setup Instructions

### Prerequisites
*   Docker
*   Docker Compose

### Running the Application

1.  Clone this repository.
2.  In the root directory, run:
    ```bash
    docker-compose up --build
    ```
3.  The API will be available at `http://localhost:8000`.
4.  The interactive API documentation (Swagger UI) is available at `http://localhost:8000/docs`.

## API Endpoints

### 1. Upload File
`POST /api/files/`
Accepts a `.zip` (containing a Shapefile) or `.kml` file.

**Example Response (202 Accepted):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "my_shapefile.zip",
  "status": "PENDING",
  "feature_count": null,
  "crs": null
}
```

### 2. Get File Information
`GET /api/files/{id}/`
Returns the status (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) and metadata.

**Example Response (200 OK):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "filename": "my_shapefile.zip",
  "status": "COMPLETED",
  "feature_count": 120,
  "crs": "EPSG:4326"
}
```

### 3. Get Measurements
`GET /api/files/{id}/measurements/`
Returns the features and their calculated measurements.

**Example Response (200 OK):**
```json
[
  {
    "feature_index": 0,
    "geom_type": "Polygon",
    "area": 1450234.55,
    "length": null
  },
  {
    "feature_index": 1,
    "geom_type": "LineString",
    "area": null,
    "length": 5600.2
  }
]
```

## Learnings and Future Scope

### Learnings
* Integrating `GeoPandas` inside a Celery task requires careful environment setup in Docker to ensure `fiona` has access to the correct GDAL C-libraries.
* Calculating the optimal local CRS dynamically using `estimate_utm_crs()` provides a highly robust way to measure globally distributed geometries without hardcoding projections.

### Future Scope
* **Authentication**: Add JWT token authentication to secure the endpoints.
* **Storage**: Integrate AWS S3 or Google Cloud Storage to store uploaded files instead of the local Docker volume.
* **Batch Processing**: For extremely large files (e.g. 5GB+), the `GeoPandas` load might exceed memory. Future versions could stream the file using `fiona` directly, parsing and writing to the database in chunks.
