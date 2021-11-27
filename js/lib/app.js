var _shell = null;
var _cadViewers = {};
var _currentCadViewer = null;

export default {
  getCurrentCadViewer() {
    return _currentCadViewer;
  },

  getCadViewers() {
    return _cadViewers;
  },

  getCadViewer(title = null) {
    if (title == null) {
      return _currentCadViewer;
    } else {
      return _cadViewers[title];
    }
  },

  addCadViewer(viewer, title = null) {
    if (title == null) {
      _currentCadViewer = viewer;
    } else {
      _cadViewers[title] = viewer;
    }
  },

  removeCadViewer(title) {
    delete _cadViewers[title];
  },

  setShell(shell) {
    _shell = shell;
  },

  getShell() {
    return _shell;
  }
};
