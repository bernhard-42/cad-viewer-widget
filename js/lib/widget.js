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

        shapes: null,
        states: null,
        options: null,
        tracks: null,
    })
});

export var CadViewerView = DOMWidgetView.extend({

    render: function () {
        this.value_changed();

        const needsAnimationLoop = this.options.needsAnimationLoop;
        const measure = this.options.measure;

        if ((this.shapes == null) || (this.states == null)) {
            return
        }

        const timer = new Timer("index", measure);

        timer.split("loaded");

        const theme = "light";
        const displayOptions = {
            theme: theme,
            ortho: true,
            normalLen: 0,
            cadWidth: 800,
            height: 600,
            treeWidth: 240,
            normalLen: 0,
            ambientIntensity: 0.9,
            directIntensity: 0.12,
        }

        const container = document.createElement('div');
        this.el.appendChild(container)

        const display = new Display(container, theme);
        console.log("display", display)
        timer.split("display");

        const viewer = new Viewer(display, needsAnimationLoop, displayOptions);

        viewer._measure = measure;

        timer.split("viewer");

        viewer.render(this.shapes, this.states);
        timer.split("renderer");
        timer.stop()
        console.log(viewer)
        this.model.on('change:value', this.value_changed, this);
    },

    value_changed: function () {
        this.shapes = decode(this.model.get('shapes'), false);
        this.states = this.model.get('states');
        this.options = this.model.get('options');

        console.log("shapes", this.shapes)
        console.log("states", this.states)
        console.log("options", this.options)
    }
});