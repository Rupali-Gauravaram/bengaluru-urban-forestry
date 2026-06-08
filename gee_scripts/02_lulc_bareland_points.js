/**
 * BENGALURU POCKET FOREST PROJECT - FINAL STABLE VERSION
 * Fixes: Blank Training Values & NDVI Band Error
 */

// 1. Define Area of Interest
var roi = ee.FeatureCollection("FAO/GAUL_SIMPLIFIED_500m/2015/level2")
            .filter(ee.Filter.eq('ADM2_NAME', 'Bangalore Urban'));

Map.centerObject(roi, 11);

// 2. Fetch and Pre-process Sentinel-2 (Ensuring band names are preserved)
function maskS2clouds(image) {
  var qa = image.select('QA60');
  var mask = qa.bitwiseAnd(1 << 10).eq(0).and(qa.bitwiseAnd(1 << 11).eq(0));
  return image.updateMask(mask).divide(10000)
              .copyProperties(image, ["system:time_start"]);
}

var s2_collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
    .filterBounds(roi)
    .filterDate('2024-01-01', '2025-11-30')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 5))
    .map(maskS2clouds);

// Create median and cast to float to ensure bands like B8 exist for NDVI
var composite = s2_collection.median().clip(roi).toFloat();

// 3. Add Indices (NDVI and NDBI)
var ndvi = composite.normalizedDifference(['B8', 'B4']).rename('NDVI');
var ndbi = composite.normalizedDifference(['B11', 'B8']).rename('NDBI');
var final_composite = composite.addBands([ndvi, ndbi]);

var bands = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'NDVI', 'NDBI'];

// 4. FIX: Force-assign landcover values to your 600+ blank points
// This replaces the manual work you did in the UI
var urban_fixed = urban.map(function(f){ return f.set('landcover', 0)});
var vegetation_fixed = vegetation.map(function(f){ return f.set('landcover', 1)});
var water_fixed = water.map(function(f){ return f.set('landcover', 2)});
var bare_land_fixed = bare_land.map(function(f){ return f.set('landcover', 3)});

var trainingPoints = urban_fixed
  .merge(vegetation_fixed)
  .merge(water_fixed)
  .merge(bare_land_fixed);

// 5. Train Random Forest Classifier
var training = final_composite.select(bands).sampleRegions({
  collection: trainingPoints,
  properties: ['landcover'],
  scale: 10
});

var classifier = ee.Classifier.smileRandomForest(100).train({
  features: training,
  classProperty: 'landcover',
  inputProperties: bands
});

// 6. Apply Classification
var classified = final_composite.select(bands).classify(classifier);

// 7. Visuals
var palette = ['red', 'green', 'blue', 'yellow'];
Map.addLayer(composite, {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3}, 'Satellite View');
Map.addLayer(classified, {min: 0, max: 3, palette: palette}, 'LULC Map 2024-2025');

// 8. Export to Assets (Corrected based on your Project ID)
Export.image.toAsset({
  image: classified,
  description: 'Bengaluru_LULC_2024_2025',
  assetId: 'projects/ee-rgauravaram/assets/LULC_Final_Map',
  scale: 10,
  region: roi.geometry(),
  pyramidingPolicy: {'.default': 'mode'}, // Keeps classes sharp
  maxPixels: 1e13
});

// Convert the classified "Bare Land" pixels into vector points
var bareLandPoints = classified.updateMask(classified.eq(3))
  .sample({
    region: roi.geometry(),
    scale: 10,
    numPixels: 5000, // Adjust based on how many samples your ML model needs
    geometries: true
  });

// Export these points as a CSV file to Drive
Export.table.toDrive({
  collection: bareLandPoints,
  description: 'Bare_Land_Coordinates_for_ML',
  fileFormat: 'CSV'
});