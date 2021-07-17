import { DOMWidgetModel, DOMWidgetView } from '@jupyter-widgets/base';
import { extend } from 'lodash';
import { Viewer, Display, Timer } from 'three-cad-viewer'
import { decode } from './serializer.js'


export var CadViewerModel = DOMWidgetModel.extend({
    defaults: extend(DOMWidgetModel.prototype.defaults(), {
        _model_name: 'CadViewerModel',
        _view_name: 'CadViewerView',
        _model_module: 'cad-viewer-widget',
        _view_module: 'cad-viewer-widget',
        _model_module_version: '0.1.0',
        _view_module_version: '0.1.0',

        options: null,
        shapes: null,
        tracks: null
    })
});

export var CadViewerView = DOMWidgetView.extend({

    render: function () {
        this.createDisplay();
        this.model.on('change:shapes', this.addShapes, this);
        this.model.on('change:tracks', this.value_changed, this);
    },

    createDisplay: function () {
        this.options = this.model.get('options');
        const container = document.createElement('div');
        this.el.appendChild(container)
        this.display = new Display(container, this.options);
        this.display.setAnimationControl(false);
    },

    addShapes: function () {
        const shapes = this.model.get('shapes');
        this.shapes = decode(shapes.shapes);
        this.states = shapes.states;
        this.options = shapes.options;

        const measure = this.options.measure;
        delete this.options.measure;

        const timer = new Timer("addShapes", measure);

        const viewer = new Viewer(this.display, this.options.needsAnimationLoop, this.options);
        viewer._measure = measure

        timer.split("viewer");

        viewer.render(this.shapes, this.states);
        timer.split("renderer");

        timer.stop()

        window.cadViewer = viewer;
    },

    addTracks: function () {
        this.tracks = this.model.get('tracks');
    }
});