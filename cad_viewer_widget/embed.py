import json
from IPython.display import Javascript, HTML, display
from cad_viewer_widget.utils import serializer
from uuid import uuid4


def embed(
    shapes,
    states,
    cad_width=800,
    height=600,
    tree_width=240,
    theme="light",
    tools=True,
    tracks=None,
    ortho=True,
    control="trackball",
    axes=False,
    axes0=False,
    grid=None,
    ticks=10,
    normal_len=0,
    transparent=False,
    black_edges=False,
    edge_color="#707070",
    ambient_intensity=0.9,
    direct_intensity=0.12,
    position=None,
    quaternion=None,
    zoom=None,
    reset_camera=True,
    zoom_speed=1.0,
    pan_speed=1.0,
    rotate_speed=1.0,
):

    uid = str(uuid4())
    display(
        HTML(
            f"""
        <div id='cad_view_{uid}'></div>
        <script type="text/javascript">
           console.log("XXX");
        </script>
    """
        )
    )
    if grid is None:
        grid_js = "[false, false, false]"
    else:
        grid_js = json.dumps(grid)

    display(
        Javascript(
            f"""
    function render() {{
        const options = {{
            theme: "{theme}",
            ortho: {json.dumps(ortho)},
            control: "{control}",
            tools: {json.dumps(tools)},
            normalLen: {normal_len},
            cadWidth: {cad_width},
            height: {height},
            treeWidth: {tree_width},
            ticks: {ticks},
            normalLen: {normal_len},
            edgeColor: "{edge_color}",
            ambientIntensity: {ambient_intensity},
            directIntensity: {direct_intensity},
            transparent: {json.dumps(transparent)},
            blackEdges: {json.dumps(black_edges)},
            axes: {json.dumps(axes)},
            grid: {grid_js}, 
            rotateSpeed: {rotate_speed},
            panSpeed: {pan_speed},
            zoomSpeed: {zoom_speed}
        }};
        console.log(options)

        const container = document.getElementById("cad_view_{uid}");
        const display = new CadViewer.Display(container, options);
        display.setAnimationControl(false)
        
        const shapes = {shapes};
        const states = {states};
        const viewer = new CadViewer.Viewer(display, options);
        const tessAndTree = viewer.renderTessellatedShapes(shapes, states);
        viewer.render(
            ...tessAndTree, states,
            {json.dumps(position)},
            {json.dumps(quaternion)},
            {json.dumps(zoom)}
        )
    }}
    console.log("INIT")
    var viewerLib = document.createElement('script');
    viewerLib.type = 'text/javascript';
    viewerLib.src = 'https://unpkg.com/three-cad-viewer@1.1.1/dist/three-cad-viewer.js'

    if(window.CadViewer == null) {{
        console.log("Loading three-cad-viewer ...")
        viewerLib.onload = () => {{
            render()
        }}
        document.head.appendChild(viewerLib);
    }} else {{
       render()
    }}
    """
        )
    )