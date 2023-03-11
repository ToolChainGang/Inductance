# Inductance Calculator

A python library for scanning through coil parameters.

## Background

<img src="Images/InductanceFormula.png" alt="Inductance formula" title="Standard inductance formula" width="40%"/>

The typical coil formula (the one you find on Wikipedia) is only accurate for audio frequencies,
it tops out at about 100 KHz.

At RF frequencies, a handful of competing issues come into play,
that are negligible at lower frequencies, to make your coil a different actual value.
Most inductance measuring devices work at 10 KHz or 100 KHz and track the geometric formula
shown above, so the engineer has no reason to believe the coil is not as designed.

For example, at higher frequencies the reactance from the inter-winding capacitance
becomes non-negligible and subtracts from the inductive reactance. The capacitive reactance
gets larger with higher frequencies, and at a high enough frequency the capacitive reactance
equals the inductive reactance and you have a self-resonant single component (with no
inductance).

So to summarize, at RF frequencies the rated inductance will be smaller than the design
inductance depending on frequency of use.

Any inductance formula that does not take frequency into consideration will be noticeably
wrong at RF.

Furthermore the geometric formula says nothing about the Q of a coil, so that designing
a coil with high Q is a complicated matter.

## This project

The complete formula for coil parameters is presented on 
[Serge Stroobandt's web page](https://hamwaves.com/inductance/en/index.html)
and takes everything into consideration, including frequency and wire plating.

This project contains the math behind that web site converted to a javascript
library for calculation, and some additional functions to “scan” across coil
parameters and print out the values that would be shown from that site.

Using a simple program loop and your initial design parameters you can scan through
different coil designs to maximize a parameter for your project.

For example, suppose you need a 25 uH coil with high Q. You can specify a wire diameter
and coil value then scan through all possible widths and lengths of coil: the program
will interpolate the number of turns needed to achieve the coil value at the width and
length, then print out the Q (and other information) for that coil. From this you can
choose a configuration that has a calculated high Q value. 

(Calculated Q values can be as high as 4,000, but see note below.)

You could do the same calculation and choose a coil with shortest wire, or the smallest
total volume, or whatever the designer needs.

## Usage

The 


## Library

The fundamental library object is "Coil" which contains the coil design parameters (Diameter, Length,
turns, and so on), the calculated parameters (Q, total wire length, inductance at frequency, and so on),
and any error information.

You can generate an initial Coil from your design parameters using the "Coil" function:

````
########################################################################################################################
#
# Coil(D,N,l,d,f,plating)
#
# Where:    D,            Diameter of coil
#           N,            Number of turns
#           l,            Length of coil
#           d,            Diameter of wire
#           f,            Frequency of interest
#           plating,      Index into wire plating table
#
````

Once you have a coil object, the Calculate() function will fill in the rest of the parameters, and the PrintCSV()
function will print out the coil parameters in CSV format.

````
TestCoil = Coil(DForm,3,lMin,d,f,p)
TestCoil.Calculate();
TestCoil.PrintCSV();
````

So to 






## Gnuplot

Generated CSV files can be directly plotted with Gnuplot, making it possible to see
trends and maxima/minima in the data.

````
gnuplot                 # Start gnuplot
> set xlabel "Dia"
> set ylabel "len"
> set zlabel "Q";  splot 'Data.csv' using 1:2:3         # Q is column 3
> set zlabel "C";  splot 'Data.csv' using 1:2:7         # C is column 7
> set zlabel "Ft"; splot 'Data.csv' using 1:2:8         # Wire len is column 8
````

Plot different 

````
> set zlabel "C";  splot 'Data.csv' using 1:2:7         # C is column 7
> set zlabel "Ft"; splot 'Data.csv' using 1:2:8         # Wire len is column 8
````

The project contains a couple of gnuplot files (extension ".gp") to get you started. To
run these:

````
> CoilScanL ...  >Data.csv            # Generate results, save as .CSV file
> gnuplot --persist DLPlot.gp
````

## A note on maximizing Q

Very high Q RF coils are apparently impossible: some experimenters with excellent setups have
suggested that the maximum Q you can achieve physically is about 1000. (Compare with 50,000
Q variable capacitors that you can purchase). Just about anything – including the presence
of conductive material anywhere in the vicinity of the coil – will tamp down on the Q.

A Q of 200 is a reasonable goal, and 800 might be doable in special circumstances.
