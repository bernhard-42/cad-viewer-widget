"""Check this widget's traitlets against ocp-viewer-core's config vocabulary.

ipywidgets needs every synced trait declared, with its type, on both sides. So
the Python list here cannot be generated from anything - and that is exactly why
it needs checking: a key added to `ocp_viewer_core.keys` and not declared here is
a setting the user can pass and this viewer silently never hears about, which is
how the zebra and studio families arrived one release late.

The check is one question in two directions: every config key either has a
traitlet or is listed below with a reason, and every traitlet is either a config
key or is listed below with a reason. Nothing is allowed to be merely absent.

Run with `make check`. Exits non-zero on the first surprise in either direction.
"""

#
# Copyright 2026 Bernhard Walter
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import ast
import pathlib
import sys

from ocp_viewer_core import keys

WIDGET = pathlib.Path(__file__).parent / "cad_viewer_widget" / "widget.py"
CLASS = "CadViewerWidget"

# Config keys with no traitlet, and why. Every one of these is consumed before
# the wire or applied by a call rather than by a trait - none of them is a
# setting the widget could hold if it wanted to.
NO_TRAIT = {
    "angular_tolerance": "tessellation: consumed by ocp_tessellate, never sent",
    "deviation": "tessellation: consumed by ocp_tessellate, never sent",
    "edge_accuracy": "tessellation: consumed by ocp_tessellate, never sent",
    "default_color": "tessellation: baked into the mesh before it is sent",
    "default_facecolor": "tessellation: baked into the mesh before it is sent",
    "default_thickedgecolor": "tessellation: baked into the mesh before it is sent",
    "default_vertexcolor": "tessellation: baked into the mesh before it is sent",
    "helper_scale": "tessellation: sizes the helpers the tessellator emits",
    "render_joints": "tessellation: decides what the tessellator emits",
    "render_mates": "tessellation: decides what the tessellator emits",
    # The other end of the `normal_len` trait below, and not a rename: the
    # tessellator turns this boolean into a length -
    # `max_accuracy / deviation * 4 if render_normals else 0` - so the config
    # key and the trait are one setting in two shapes, which is why the key
    # mapping cannot express it.
    "render_normals": "sent as the `normal_len` trait, computed by the tessellator",
    "show_parent": "Python-side: decides what `show` collects",
    "show_locals": "Python-side: decides what `show` collects",
    "analysis_tool": (
        "applied by a call after the render, not by a trait - "
        "jupyter_cadquery's send_data runs viewer.display.setTool"
    ),
}

# Traitlets that are not config keys, and why.
NOT_A_CONFIG_KEY = {
    # ipywidgets plumbing and this widget's own model
    "id": "widget: identifies this viewer to the measurement backend",
    "initialize": "widget: gates the view's first render",
    "disposed": "widget: lifecycle",
    "result": "widget: JSON result passed back from JavaScript",
    "image_id": "widget: target img tag for pin-as-png",
    "shapes": "widget: the model itself, not a setting for it",
    "tracks": "widget: animation tracks",
    "state_updates": "widget: incremental tree-state updates",
    "measure": "widget: the measurement result handed back",
    "measure_callback": "widget: a Callable, not synced",
    "animation_speed": "widget: animation playback speed",
    "aspect_ratio": "widget: sizes a cell viewer",
    # The sidecar keywords. In the show superset because every host accepts
    # them, but not in the config vocabulary, because only this host has a
    # sidecar to name, place and pin.
    "title": "host: names the sidecar",
    "anchor": "host: places the sidecar",
    "pinning": "host: whether this surface offers pin-as-png",
    # The return path. These are three-cad-viewer's notification names rather
    # than config keys - nothing sets them, the viewer reports them - so their
    # authority is the renderer and not this table. See ViewerState's
    # `getAllNotifiable`.
    "activeTool": "notification: reported by the viewer, never set",
    "lastPick": "notification: reported by the viewer, never set",
    "selectedShapeIDs": "notification: reported by the viewer, never set",
    # Renderer-shaped settings with no config key of the same shape.
    "normal_len": "config `render_normals`, as the length the tessellator computed",
    "new_tree_behavior": "renderer option with no Python config key",
}


def traitlets():
    """The synced traits declared on the widget class, name -> trait type."""
    tree = ast.parse(WIDGET.read_text(encoding="utf-8"))
    cls = next(
        n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == CLASS
    )
    found = {}
    for node in cls.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        kind = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        for target in node.targets:
            # `_model_name` and friends are ipywidgets' own handshake, not this
            # widget's vocabulary.
            if isinstance(target, ast.Name) and not target.id.startswith("_"):
                found[target.id] = kind
    return found


def renamed():
    """Traits the widget spells with the renderer's name for the same setting.

    Derived from `keys.ALL` rather than listed: a trait whose name is some
    config key's *JavaScript* name is that config key under another spelling.
    Taking it from the mapping means a renamed key cannot be missed here.
    """
    by_js = {
        js: py for py, js in keys.ALL.items() if js is not None and js != py
    }
    return {name: by_js[name] for name in traitlets() if name in by_js}


def main():
    traits = traitlets()
    aliases = renamed()
    # A trait that spells a config key the renderer's way counts as that key.
    covered = {aliases.get(name, name) for name in traits}
    vocabulary = set(keys.ALL)

    missing = sorted(vocabulary - covered - set(NO_TRAIT))
    extra = sorted(
        name
        for name in traits
        if name not in vocabulary
        and name not in aliases
        and name not in NOT_A_CONFIG_KEY
    )
    # Four ways an exception can go stale, and all four matter: the thing it
    # excuses can gain a trait, lose a trait, enter the vocabulary or leave it.
    stale_no_trait = sorted(
        (set(NO_TRAIT) & covered) | (set(NO_TRAIT) - vocabulary)
    )
    stale_extra = sorted(
        name
        for name in NOT_A_CONFIG_KEY
        if name not in traits or aliases.get(name, name) in vocabulary
    )

    print(f"traitlets: {len(traits)}   config keys: {len(vocabulary)}")
    print(f"  covered directly or by a rename: {len(covered & vocabulary)}")
    if aliases:
        print("\n  spelled with the renderer's name rather than the config key's:")
        for name, key in sorted(aliases.items()):
            print(f"    {name:<24} = config `{key}`")

    # Listed rather than counted, and this is the point of the exercise: a
    # number says how many exceptions there are, and the list says whether each
    # is still one. They are meant to be read on every run.
    width = max(len(k) for k in (*NO_TRAIT, *NOT_A_CONFIG_KEY))
    print(f"\n  config keys with no traitlet ({len(NO_TRAIT)}):")
    for key, why in sorted(NO_TRAIT.items()):
        print(f"    {key:<{width}}  {why}")
    print(f"\n  traitlets that are not config keys ({len(NOT_A_CONFIG_KEY)}):")
    for name, why in sorted(NOT_A_CONFIG_KEY.items()):
        print(f"    {name:<{width}}  {why}")

    problems = 0
    if missing:
        problems += len(missing)
        print(f"\nconfig keys with no traitlet and no reason ({len(missing)}):")
        for key in missing:
            print(f"    {key}  ->  add a traitlet, or a reason to NO_TRAIT")
    if extra:
        problems += len(extra)
        print(f"\ntraitlets that are not config keys and have no reason ({len(extra)}):")
        for name in extra:
            print(f"    {name} ({traits[name]})  ->  add a reason to NOT_A_CONFIG_KEY")

    # An exception that is no longer needed is as much a defect as a missing
    # one: it says something is absent that is now present, and the next reader
    # believes it.
    if stale_no_trait:
        problems += len(stale_no_trait)
        print(f"\nNO_TRAIT entries that are no longer true ({len(stale_no_trait)}):")
        for key in stale_no_trait:
            why = "is not a config key" if key not in vocabulary else "now has a traitlet"
            print(f"    {key} {why}  ->  remove it from NO_TRAIT")
    if stale_extra:
        problems += len(stale_extra)
        print(
            f"\nNOT_A_CONFIG_KEY entries that are no longer true "
            f"({len(stale_extra)}):"
        )
        for name in stale_extra:
            why = "is a config key" if name in traits else "is not a traitlet"
            print(f"    {name} {why}  ->  remove it from NOT_A_CONFIG_KEY")

    if problems:
        print(f"\n{problems} problem(s)")
        return 1

    print("\nthe traitlets and the config vocabulary agree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
