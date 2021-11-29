var _shell = null;
var _sidecarViewers = {};
var _cellViewers = {};
var _currentCadViewer = null;

export default {
  getCadViewers() {
    return {
      sidecar: _sidecarViewers,
      cell: _cellViewers
    };
  },

  getSidecarViewer(title) {
    return _sidecarViewers[title];
  },

  addSidecarViewer(title, viewer) {
    _currentCadViewer = viewer;
    _sidecarViewers[title] = viewer;
  },

  getCurrentViewer() {
    return _currentCadViewer;
  },

  setCurrentViewer(viewer) {
    _currentCadViewer = viewer;
  },

  addCellViewer(id, viewer) {
    _currentCadViewer = viewer;
    _cellViewers[id] = viewer;
    console.log(`cad-viewer-widget: Cell viewer ${id} created`);
  },

  removeSidecarViewer(title) {
    delete _sidecarViewers[title];
  },

  cleanupCellViewers() {
    for (const [id, viewer] of Object.entries(_cellViewers)) {
      if (document.getElementById(id) == null) {
        viewer.dispose();
        delete _cellViewers[id];
        console.log(`cad-viewer-widget: Cell viewer "${id}" removed`);
      }
    }
  },

  removeCellViewer(id) {
    delete _cellViewers[id];
  },

  setShell(shell) {
    _shell = shell;
  },

  getShell() {
    return _shell;
  }
};
