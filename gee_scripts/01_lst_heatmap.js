// 1. Reference your uploaded asset
var aoi = BBMP_Wards_Shapefile.geometry();
Map.centerObject(aoi, 11);

// 2. Load and Process Landsat 8 LST (2024-2025)
var dataset = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    .filterBounds(aoi)
    .filterDate('2024-01-01', '2025-11-30')
    .filter(ee.Filter.lt('CLOUD_COVER', 10));

function applyScaleFactors(image) {
  var thermal = image.select('ST_B10').multiply(0.00341802).add(149.0);
  return image.addBands(thermal.subtract(273.15).rename('LST_C'));
}

var lstImage = dataset.map(applyScaleFactors).median().clip(aoi);

// 3. Visualization
var thermalViz = {
  min: 25, 
  max: 42, 
  palette: ['blue', 'cyan', 'green', 'yellow', 'orange', 'red', 'darkred']
};

Map.addLayer(lstImage.select('LST_C'), thermalViz, 'Urban Heat Map (LULC Boundary)');
Map.addLayer(BBMP_Wards_Shapefile, {color: 'black', width: 1}, 'LULC Zones', false);

// 4. Analysis: Calculate Mean Temperature per LULC Class
// Replace 'class_name' with the column name in your shapefile that defines land use
var zoneStats = lstImage.select('LST_C').reduceRegions({
  collection: BBMP_Wards_Shapefile,
  reducer: ee.Reducer.mean(),
  scale: 30
});

print('Temperature Statistics by Zone:', zoneStats);
 
// 5. Create a Chart: Temperature per Zone
print(ui.Chart.feature.byFeature(zoneStats, 'class_name', 'mean') // Change 'class_name' to your column
  .setChartType('ColumnChart')
  .setOptions({
    title: 'Average Temperature by Land Use Zone',
    vAxis: {title: 'Temperature (°C)'},
    hAxis: {title: 'Zone'}
  }));
  
// 6. Export the LST Map to Google Drive
Export.image.toDrive({
  image: lstImage.select('LST_C'),
  description: 'Bengaluru_LST_2024_2025',
  scale: 30, // Landsat resolution is 30m
  region: aoi,
  fileFormat: 'GeoTIFF',
  crs: 'EPSG:4326', // Standard coordinate system for QGIS
  maxPixels: 1e13
});

// 7. Optional: Export the Statistics (Zonal Means) as a CSV
Export.table.toDrive({
  collection: zoneStats,
  description: 'BBMP_Ward_Temperature_Stats',
  fileFormat: 'CSV'
});