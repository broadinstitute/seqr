var sliders = {

  freqInverse: function(position) {
    if (position == 1) return 0;
    else if (position == 2) return Number(.0001).toExponential();
    else if (position == 3) return Number(.0005).toExponential();
    else if (position == 4) return Number(.001).toExponential();
    else if (position == 5) return Number(.005).toExponential();
    else if (position == 6) return .01;
    else if (position == 7) return .05;
    else if (position == 8) return .1;
    else return 1;
  },
};