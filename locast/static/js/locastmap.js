// TODO:
// Make a dictionary mapping names of vector layers to the layers themselves... i.e. paths: vectorLayer

LocastMap = function() {

var self = this;

self.map = null;

// stores wether a conversion is necessary or not based on
// if the displayproject and the projection are different
var proj_conversion = true;

self.projection = new OpenLayers.Projection('EPSG:900913');
self.displayProjection = new OpenLayers.Projection('EPSG:4326');

self.markerLayer = null;
self.vectorLayer = null;

// Turn on the map
self.init = function(div, options, controls, display_layers) {

    if ( ! display_layers ) {
        display_layers = ['GoogleStreets']
    }

    // Open layers options to send to the map
    var ol_options = {
        projection: self.projection,
        displayProjection: self.displayProjection,
        units: 'm',
        maxResolution: 156543.0339,
        maxExtent: new OpenLayers.Bounds(-20037508.34, -20037508.34, 20037508.34, 20037508.34)};

    self.map = new OpenLayers.Map(div, ol_options);

    self.markerLayer = new OpenLayers.Layer.Markers('Markers');

    self.vectorLayer = new OpenLayers.Layer.Vector('Drawn Elements');
    var s = OpenLayers.Util.applyDefaults({strokeWidth: 4},
        OpenLayers.Feature.Vector.style['default']);
    self.vectorLayer.style = s;

    var dl = null;
    var disp_layer_objects = [];
    for ( i in display_layers ) {
        dl = display_layers[i];
        
        if ( dl == 'GoogleStreets' ) {
            disp_layer_objects.push(new OpenLayers.Layer.Google('Google Streets', {
                sphericalMercator: true,
                maxZoomLevel: options['maxZoom'],
                minZoomLevel: options['minZoom']
            }));
        }

        else if ( dl == 'GoogleHybrid' ) {
            disp_layer_objects.push(new OpenLayers.Layer.Google('Google Hybrid', {
                type: G_HYBRID_MAP,
                sphericalMercator: true,
                maxZoomLevel: options['maxZoom'],
                minZoomLevel: options['minZoom']
            }));
        }
    }

    self.map.addLayers(disp_layer_objects);

    self.map.addLayers([self.vectorLayer, self.markerLayer]);

    // set up controls
    
   /*
    var panelControls = [
        new OpenLayers.Control.Navigation()
    ];
    */
    var panelControls = [];

    if ( controls ) {
        var c = null;
        var control = null;
        for ( i in controls ) {
            c = controls[i]

            if ( c == 'DrawFeature' ) {
                control = new OpenLayers.Control.DrawFeature(self.vectorLayer, OpenLayers.Handler.Point, {'displayClass': 'olControlDrawFeaturePoint'});
            }

            else if ( c == 'Navigation' ) {
                control = new OpenLayers.Control.Navigation();
            }

            panelControls.push(control);
        }
    }

    var toolbar = new OpenLayers.Control.Panel({
        displayClass: 'olControlEditingToolbar',
        defaultControl: panelControls[0] });

    toolbar.addControls(panelControls);
    self.map.addControl(toolbar);
    self.map.addControl(new OpenLayers.Control.LayerSwitcher());

    var map_center = options['center'];
    self.setCenter(map_center[0], map_center[1]);

    if ( options['defaultZoom'] ) {
        self.setZoom(options['defaultZoom']);
    }
}

//self.addVectorLayer = function()

// Markers

self.addMarker = function(x, y, icon) { 
    // icon should be like this
    // { 'url' : 'http://whatever',
    //   'height' : 32,
    //   'width'  : 32 }
    
    var ll = self.get_proj_ll(x,y);
    var ol_icon = null;

    if ( icon ) {
        var size = new OpenLayers.Size(icon.height, icon.width);
        ol_icon = new OpenLayers.Icon(icon.url, size);
        if ( icon.offset ) {
            ol_icon.offset = new OpenLayers.Pixel(icon.offset[0], icon.offset[1]);
        }
    }

    var marker = new OpenLayers.Marker(ll, ol_icon);
    self.markerLayer.addMarker(marker);

    return marker;
}

self.clearMarkers = function() {
    var m = null;
    for ( i in self.markerLayer.markers ) {
        m = self.markerLayer.markers[i];
        m.destroy();
    }
    self.markerLayer.clearMarkers();
}

self.clearVectors = function(features) {
    if ( ! features ) {
        features = self.vectorLayer.features;
    }
    self.vectorLayer.destroyFeatures(features);
}

//size : {'height' : 32, 'width': 32}
self.addPopup = function(x, y, size, html) {
    var ll = self.get_proj_ll(x,y); 
    
    var popup = new OpenLayers.Popup.FramedCloud(
        'popup',
        ll, 
        new OpenLayers.Size(size.height, size.width),
        html,
        null, true, null);

    self.map.addPopup(popup);
    return popup;
}

self.clearPopups = function() {

}

self.drawPath = function(coords) {
    var point = null;
    var points = []
    for (c in coords) {
        ll = coords[c];
        point = new OpenLayers.Geometry.Point(ll[0], ll[1]);
        if ( proj_conversion ) {
            point.transform(self.displayProjection, self.projection);
        }
        points.push(point);
    }

    var linestring = new OpenLayers.Geometry.LineString(points);
    var vector = new OpenLayers.Feature.Vector(linestring);
    self.vectorLayer.addFeatures([vector]);

    return vector
}

self.drawPoint = function(x, y) {
    var point = new OpenLayers.Geometry.Point(x,y);
    if ( proj_conversion ) {
        point.transform(self.displayProjection, self.projection);
    }
    var vector = new OpenLayers.Feature.Vector(point);
    self.vectorLayer.addFeatures([vector]);

    return vector;
}

self.drawPolygon = function(x, y, radius, sides) {
    var center = new OpenLayers.Geometry.Point(x,y);

    if ( proj_conversion )  {
        center.transform(self.displayProjection, self.projection);
    }
        
    var poly = OpenLayers.Geometry.Polygon.createRegularPolygon(
            center, radius, sides);

    var vector = new OpenLayers.Feature.Vector(poly);
    self.vectorLayer.addFeatures(vector);

    return vector;
}

self.setZoom = function(zoom) {
    self.map.zoomTo(zoom);
}

self.setCenter = function(x, y) {
    var center = self.get_proj_ll(x,y);
    self.map.setCenter(center);
}

self.getCenter = function() {
    var center = self.map.center.clone();
    if ( proj_conversion ) {
        center.transform(self.projection, self.displayProjection);
    }
    return [center.lon, center.lat] 
}

self.panTo = function(x, y) {
    var ll = self.get_proj_ll(x,y);
    self.map.panTo(ll);
}

// Helpers

self.getBounds = function(str) { 
    var bounds = self.map.calculateBounds();
    if ( proj_conversion ) {
        bounds.transform(self.projection, self.displayProjection);
    } 

    if ( str ) {
        var str = '';
        str += bounds.left + ',';
        str += bounds.bottom + ',';
        str += bounds.right + ',';
        str += bounds.top;  
        return str;
    }
    else {
        return bounds;
    }
}

self.get_ll = function(x, y) {
    return new OpenLayers.LonLat(x,y);
}

self.get_disp_ll = function(x, y) {
    var ll = self.get_ll(x, y);
    if ( proj_conversion ) {
        ll.transform(self.projection, self.displayProjection);
    }

    return ll;
}

self.get_proj_ll = function(x, y) {
    var ll = self.get_ll(x, y);
    if ( proj_conversion ) {
        ll.transform(self.displayProjection, self.projection);
    }

    return ll;
}

}

