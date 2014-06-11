var sliders = {
	
    freqInverse: function(position) {

        if (position == 1) return Number(.001).toExponential();
        else if (position == 2) return Number(.005).toExponential();
        else if (position == 3) return .01;
        else if (position == 4) return .05;
        else if (position == 5) return .1;
        else return 1;

    },

};