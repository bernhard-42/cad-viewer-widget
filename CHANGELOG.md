# Changelog

Up to 4.1.5 the release notes are the commit log.

## unreleased

- **Features**
    - **three-cad-viewer 5.2.0** (was 5.1.3)
        - A rotate drag that starts on the model turns the camera around the point under the cursor, one that starts on the background around the centre of the visible objects. The wheel, trackpad pinch and middle-button drag zoom towards the cursor. Both are on by default. The camera target moves with the pivot; Reset and Recenter put it back
        - A double-click picks what the hover highlights: it follows the topology filter (All / Vertex / Edge / Face / Solid), and the bounding box wraps the picked face or edge. A vertex gets a marker, and the info panel names the picked element and shows a vertex's coordinates. A second double-click on the same element removes the box
        - `lastPick` has the new fields `component`, the full path of what was picked, and `point`, the world coordinates of the double-clicked point, and it is sent on every double-click
    - The traitlets and `show` arguments `cursor_pivot` and `zoom_to_cursor` switch rotating around and zooming towards the cursor off separately
    - The traitlet `shape_filter` sets the topology filter (`"none"`, `"vertex"`, `"edge"`, `"face"`, `"solid"`) through `set_viewer_config(shape_filter=...)`; the user's own changes come back into it, and every new model resets it to `"none"`

- **Changes**
    - `js/package.json` requires `ocp-viewer-core` 1.2.0 (was 1.1.0), whose peer range is three-cad-viewer `>=5.2.0 <5.3.0`
    - A double-click with the filter on All and the cursor on or near an edge picks the edge (vertices come before edges, edges before faces), where it always picked the whole object. Hide (`meta`) and isolate (`shift`) still act on the whole object, and they ignore the filter (three-cad-viewer 5.2.0)
    - With `cursor_pivot` on, `shift` + `meta` + double-click on the model no longer sets the camera target, since every rotation already turns around the point under the cursor. With `cursor_pivot=False` it sets the target to the clicked point (three-cad-viewer 5.2.0)
    - `lastPick.boundingBox` and `lastPick.boundingSphere` describe the picked face, edge or vertex, no longer its object; a vertex has a box of size zero. With the filter on Solid, for hide and isolate, for objects that are faces, edges or vertices themselves, and for clicks in the tree they are the object's box as before (three-cad-viewer 5.2.0)
    - Geometry types in the status line and the properties panel read `B-spline surface` instead of `bspline` or `BSplineSurface`, and `Surface of revolution` instead of `surface of revolution` (three-cad-viewer 5.2.0)
    - A selection copied with the select tool keeps the indices for one object and one kind, e.g. `6,16,7,17`; with several objects or kinds it is one labelled line per object and kind, `# <object path> <kind>` followed by its indices (ocp-viewer-core 1.2.0)

- **Fixes**
    - Toolbar tooltips and the grid menu are no longer cut off at the toolbar's bottom edge in Safari and other WebKit browsers ([three-cad-viewer#47](https://github.com/bernhard-42/three-cad-viewer/pull/47), three-cad-viewer 5.2.0)
    - Object names containing `<`, `"` or `\` are shown literally, and their tree rows keep working (three-cad-viewer 5.2.0)
    - The view no longer jumps at the first rotation after a `quaternion` that is not exactly unit length, such as a rounded one, nor again after every Reset (three-cad-viewer 5.2.0)
    - Switching the Studio background from a solid color back to Environment draws the environment again (three-cad-viewer 5.2.0)
    - The help names the filter key for all object types correctly, `a`, and shows scrollbars only when it doesn't fit (three-cad-viewer 5.2.0)
    - The topology filter keys `a` / `v` / `e` / `f` / `s` and the select tool's Escape and Backspace act only when the viewer has focus: Cmd-V, or a `v` typed elsewhere such as in a notebook cell, no longer sets the filter to Vertex, and Backspace in a text field no longer removes a selected element (three-cad-viewer 5.2.0)
    - The measurement panel stays fully inside the viewer when it reopens at its previous position after a new model, a smaller viewer or a larger result (three-cad-viewer 5.2.0)

## v4.2.0 (2026-10-13)

- **Features**
    - **three-cad-viewer 5.1.3** (was 5.0.6)
        - Hovering a row of the tree highlights that object, or everything below a group: the faces of solids and faces, the edges of objects that have only edges, the vertices of objects that have only vertices ([#218](https://github.com/bernhard-42/vscode-ocp-cad-viewer/issues/218))
        - Ctrl/Cmd-C over the model copies the point under the mouse to the clipboard as `x, y, z` (4 decimals), and the status line shows `copied: x, y, z`. It follows the topology filter (All / Vertex / Edge / Face / Solid) and needs no click into the viewer first; it is off in explode mode, with a z-scale other than 1, and while an animation has moved the parts (Play or the time slider; Stop turns it back on, Pause does not) ([#243](https://github.com/bernhard-42/vscode-ocp-cad-viewer/issues/243))
        - Clip caps are hatched: neighbouring solids alternate the direction and spacing of the lines, which stay fixed to the clip plane while the view moves
        - Clip caps are outlined in the edge color while the Clip tab is active, also where caps of touching solids meet and, seen from behind, along the cut contour on the faces. The outline is drawn once the camera has been still for 150 ms

- **Changes**
    - Bundles ocp-viewer-core JavaScript 1.1.0 (was 1.0.4), which requires three-cad-viewer 5.1 (peer range `>=5.1.0 <5.2.0`)
    - `check_traits.py` knows `python_enumeration`, a key of ocp-viewer-core 1.1 that only ocp-tessellate reads and the widget never receives, so it needs no traitlet

- **Fixes**
    - A loaded animation no longer keeps the viewer redrawing the scene on every display frame until it is cleared - also while paused, stopped or never started - which cost constant CPU and GPU time in an idle viewer (three-cad-viewer 5.1.3, [three-cad-viewer #44](https://github.com/bernhard-42/three-cad-viewer/issues/44)). Resuming after a pause no longer jumps ahead by the time spent paused
    - In Safari and other WebKit-based browsers, graphics memory no longer grows to about 25 times the model's size, which let a few large shows crash the page (three-cad-viewer 5.0.7)
    - Clearing or replacing a model no longer leaks the orientation marker's graphics resources (three-cad-viewer 5.0.7)
