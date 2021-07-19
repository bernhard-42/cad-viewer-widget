import { DOMWidgetModel, DOMWidgetView, serialize_state } from '@jupyter-widgets/base';
import { extend } from 'lodash';
import { Viewer, Display, Timer } from 'three-cad-viewer'
import { decode } from './serializer.js'
import * as THREE from 'three';

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
        tracks: null,
        result: null
    })
});

function serialize(obj) {
    try {
        var result = JSON.stringify(obj);
        return result
    } catch (error) {
        console.error(error)
        return "Error"
    }
}

function deserialize(str) {
    return JSON.parse(str)
}

export var CadViewerView = DOMWidgetView.extend({

    render: function () {
        this.createDisplay();
        this.model.on('change:shapes', this.addShapes, this);
        this.model.on('change:tracks', this.value_changed, this);

        this.listenTo(this.model, 'msg:custom', this.onCustomMessage.bind(this));
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

        this.viewer = new Viewer(this.display, this.options.needsAnimationLoop, this.options);
        this.viewer._measure = measure

        timer.split("viewer");

        this.viewer.render(this.shapes, this.states);
        timer.split("renderer");

        timer.stop()

        window.cadViewer = this.viewer;
        window.three = THREE
    },

    addTracks: function () {
        this.tracks = this.model.get('tracks');
    },

    onCustomMessage: function (msg, buffers) {
        console.log(
            "New message with msgType:", msg.type,
            "msgId:", msg.id,
            ", object:", msg.object,
            ", name:", msg.name,
            ", args:", msg.args,
            ", type:", msg.threeType,
            ", update:", msg.update,
            ", buffers:", buffers,
        );

        if (msg.object)
            var path = msg.object.split(".");
        var objName = path.pop()

        var parent = null;
        try {
            parent = this;
            path.forEach((o) => parent = parent[o])
        } catch (error) {
            console.error(error)
        }
        // console.log("parent:", parent, "object:", objName);

        var result = null;
        if (msg.name == null) {
            result = parent[objName];
        } else {
            var args = null;
            try {
                args = deserialize(msg.args);
                if (msg.threeType) {
                    args = new THREE[msg.threeType](...args);
                }
            } catch (error) {
                console.error(error)
            }
            // console.log("args:", args)

            try {
                if (msg.name === "=") {
                    result = parent[objName] = args;
                } else {
                    if (msg.threeType) {
                        result = parent[objName][msg.name](args)
                    } else {
                        result = parent[objName][msg.name](...args)
                    }
                }

                if (msg.update) {
                    this.viewer.camera.updateProjectionMatrix()
                    this.viewer.controls.update();
                    this.viewer.update(true, false);
                }

                // const returnMsg = {
                //     type: 'cad_viewer_method_result',
                //     id: msg.id,
                //     result: serialize(result),
                // }

                // console.log("sending msg with id:", msg.id, "result:", result)

                // this.model.send(returnMsg, this.callbacks(), null);

            } catch (error) {
                console.log(error)
            }
        }
        try {
            this.model.set('result', serialize({ "msg_id": msg.id, "result": result }));
            this.model.save_changes();
        } catch (error) {
            console.log(error)
        }
    }
});

