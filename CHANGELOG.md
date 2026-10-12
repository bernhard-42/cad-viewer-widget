# Changelog

Up to 4.1.5 the release notes are the commit log.

## Unreleased

- **Features**
    - **three-cad-viewer 5.1.3** (was 5.0.6)
        - Hovering a row of the tree highlights that object, or everything below a group: the faces of solids and faces, the edges of objects that have only edges, the vertices of objects that have only vertices
        - Ctrl/Cmd-C over the model copies the point under the mouse to the clipboard as `x, y, z` (4 decimals), and the status line shows `copied: x, y, z`. It follows the topology filter (All / Vertex / Edge / Face / Solid) and needs no click into the viewer first; it is off in explode mode, with a z-scale other than 1, and while an animation has moved the parts (Play or the time slider; Stop turns it back on, Pause does not)
        - Clip caps are hatched: neighbouring solids alternate the direction and spacing of the lines, which stay fixed to the clip plane while the view moves
        - Clip caps are outlined in the edge color while the Clip tab is active, also where caps of touching solids meet and, seen from behind, along the cut contour on the faces. The outline is drawn once the camera has been still for 150 ms

- **Changes**
    - Bundles ocp-viewer-core JavaScript 1.1.0 (was 1.0.4), which requires three-cad-viewer 5.1 (peer range `>=5.1.0 <5.2.0`)
    - `check_traits.py` knows `python_enumeration`, a key of ocp-viewer-core 1.1 that only ocp-tessellate reads and the widget never receives, so it needs no traitlet

- **Fixes**
    - A loaded animation no longer keeps the viewer redrawing the scene on every display frame until it is cleared - also while paused, stopped or never started - which cost constant CPU and GPU time in an idle viewer (three-cad-viewer 5.1.3, [three-cad-viewer #44](https://github.com/bernhard-42/three-cad-viewer/issues/44)). Resuming after a pause no longer jumps ahead by the time spent paused
    - In Safari and other WebKit-based browsers, graphics memory no longer grows to about 25 times the model's size, which let a few large shows crash the page (three-cad-viewer 5.0.7)
    - Clearing or replacing a model no longer leaks the orientation marker's graphics resources (three-cad-viewer 5.0.7)
