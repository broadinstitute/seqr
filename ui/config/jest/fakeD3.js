'use strict';

// This project's jest config maps every module whose name contains "d3" (see the
// moduleNameMapper entry in package.json) to this single file - that includes every d3-* package
// (d3-array, d3-axis, d3-drag, d3-hierarchy, d3-random, d3-scale, d3-scale-chromatic,
// d3-selection, d3-shape, d3-zoom, ...) as well as "shared/components/graph/d3Utils" (its name
// contains "d3Utils"). That's necessary because:
//   - this project's jest tests run with testEnvironment: 'node', so there is no real DOM for the
//     real d3-selection to manipulate;
//   - real d3 packages have no reasonable fake behavior to fall back to when there's nothing to
//     render into.
// Since every one of those specifiers resolves to this one physical module, it must export
// everything any component in the app imports from any d3-* package or from d3Utils - add to it
// as new d3 imports are introduced elsewhere in the app.
//
// FakeD3Selection is a minimal stand-in for a d3 selection: enough of the chained selection API
// to record the attributes/styles/text/html a component computes per bound datum, so tests can
// assert on what would have been drawn.
class FakeD3Selection {

  constructor(boundData = [undefined]) {
    this.boundData = boundData;
  }

  append(tag) {
    const child = new FakeD3Selection(this.boundData);
    child.tag = tag;
    FakeD3Selection.appended.push(child);
    return child;
  }

  selectAll() {
    return new FakeD3Selection(this.boundData);
  }

  data(arr) { // eslint-disable-line class-methods-use-this
    return new FakeD3Selection(arr);
  }

  datum(value) { // eslint-disable-line class-methods-use-this
    return new FakeD3Selection([value]);
  }

  enter() {
    return this;
  }

  attr(name, val) {
    this.attrs = this.attrs || {};
    this.attrs[name] = this.boundData.map((d, i) => (typeof val === 'function' ? val(d, i) : val));
    return this;
  }

  style(name, val) {
    this.styles = this.styles || {};
    this.styles[name] = this.boundData.map((d, i) => (typeof val === 'function' ? val(d, i) : val));
    return this;
  }

  text(val) {
    this.texts = this.boundData.map((d, i) => (typeof val === 'function' ? val(d, i) : val));
    return this;
  }

  html(val) {
    this.htmls = this.boundData.map((d, i) => (typeof val === 'function' ? val(d, i) : val));
    return this;
  }

  remove() {
    FakeD3Selection.removeCallCount += 1;
    return this;
  }

  // Chain-only no-ops: these d3-selection methods matter for real rendering (filtering/sorting/
  // merging/animating a selection) but not for asserting on the attrs/styles/text this fake
  // records, so they're kept as pass-throughs rather than modeled.
  filter() { return this; }

  sort() { return this; }

  join() { return this; }

  merge() { return this; }

  exit() { return new FakeD3Selection([]); }

  transition() { return this; }

  duration() { return this; }

  delay() { return this; }

  classed() { return this; }

  call() { return this; }

  on() { return this; }

}

FakeD3Selection.appended = [];
FakeD3Selection.removeCallCount = 0;

FakeD3Selection.reset = () => {
  FakeD3Selection.appended = [];
  FakeD3Selection.removeCallCount = 0;
};

FakeD3Selection.getAppended = tag => FakeD3Selection.appended.filter(el => el.tag === tag);

// A minimal stand-in for d3Utils's real Tooltip helper, built on FakeD3Selection so it behaves the
// same way in tests.
class FakeTooltip {

  constructor(containerElement) {
    this.tooltip = containerElement.append('div');
    containerElement.on('mouseout', () => this.hide());
  }

  show(html, left, top) {
    return this.tooltip.html(html).style('display', 'inline').style('left', `${left}px`).style('top', `${top}px`);
  }

  hide() {
    return this.tooltip.style('display', 'none');
  }

}

// A chainable no-op stand-in for d3 generator/builder objects (d3-axis's axisBottom/axisLeft,
// d3-shape's area): the real ones support arbitrary builder-style calls (.tickSizeOuter(),
// .ticks(), .x0(), .y(), ...) and are themselves callable as generator functions. Nothing in this
// fake needs to inspect what they'd actually draw, so any property access or call just returns
// the same chainable stand-in.
const makeChainable = () => {
  const chainable = new Proxy(() => chainable, {
    get: (target, prop) => (prop in target ? target[prop] : () => chainable),
  });
  return chainable;
};

// A chainable stand-in for a d3 scale that behaves as the identity function: real scale math
// (linear/log/band/sequential interpolation) is d3's own responsibility and isn't meaningful
// without real pixel dimensions, so components under test should be asserted against the raw
// data values a scale was given, not against interpolated pixel positions.
const makeIdentityScale = () => {
  const scale = new Proxy((v => v), {
    get: (target, prop) => {
      if (prop === 'bandwidth') return () => 0;
      return prop in target ? target[prop] : () => scale;
    },
  });
  return scale;
};

const sorted = arr => [...arr].sort((a, b) => a - b);
const mapped = (arr, accessor) => (accessor ? arr.map(accessor) : arr);

module.exports = {
  FakeD3Selection,

  // d3-selection
  select: () => new FakeD3Selection(),

  // shared/components/graph/d3Utils
  initializeD3: containerElement => containerElement.append('svg'),
  Tooltip: FakeTooltip,

  // d3-array
  extent: (arr, accessor) => [Math.min(...mapped(arr, accessor)), Math.max(...mapped(arr, accessor))],
  max: (arr, accessor) => Math.max(...mapped(arr, accessor)),
  min: (arr, accessor) => Math.min(...mapped(arr, accessor)),
  mean: (arr, accessor) => {
    const values = mapped(arr, accessor);
    return values.reduce((sum, v) => sum + v, 0) / values.length;
  },
  median: (arr, accessor) => {
    const s = sorted(mapped(arr, accessor));
    const mid = Math.floor(s.length / 2);
    return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
  },
  deviation: (arr, accessor) => {
    const values = mapped(arr, accessor);
    const m = values.reduce((sum, v) => sum + v, 0) / values.length;
    return Math.sqrt(values.reduce((sum, v) => sum + ((v - m) ** 2), 0) / (values.length - 1));
  },
  quantile: (arr, p, accessor) => {
    const s = sorted(mapped(arr, accessor));
    const pos = (s.length - 1) * p;
    const base = Math.floor(pos);
    const rest = pos - base;
    return s[base + 1] !== undefined ? s[base] + (rest * (s[base + 1] - s[base])) : s[base];
  },

  // d3-scale / d3-scale-chromatic
  scaleLinear: makeIdentityScale,
  scaleLog: makeIdentityScale,
  scaleBand: makeIdentityScale,
  scaleSequential: makeIdentityScale,
  interpolatePurples: v => v,

  // d3-random
  randomNormal: (mu = 0) => () => mu,

  // d3-shape
  area: makeChainable,

  // d3-axis
  axisBottom: makeChainable,
  axisLeft: makeChainable,
};
