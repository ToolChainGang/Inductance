# Inductance Library

A python library for scanning through coil parameters.

1. [The Coil object](#the-coil-object)
2. [Coil calculation errors](#coil-calculation-errors)
3. [Interpolating turns](#interpolating-turns)
4. [Generating CSV output](#generating-csv-output)
5. [A note on maximizing Q](#a-note-on-maximizing-q)

## The Coil object

The fundamental library object is "Coil" which contains the coil design parameters (Diameter, Length,
turns, and so on), the calculated parameters (Q, total wire length, self-resonance frequency, and so on),
and any error information.

You generate an initial Coil object using your design parameters.

Once you have a coil object, the Calculate() function will fill in the rest of the parameters, and the PrintCSV()
function will print out the coil parameters in CSV format.

Something like this:

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
#                    =0 annealed copper
#                    =1 hard-drawn copper
#                    =2 silver
#                    =3 aluminium
#

TestCoil = Coil(CoilDiam,Turns,Length,dWire,freq,plating)

TestCoil.Calculate()

if TestCoil.error_code != 0
    return

if TestCoil.Q_eff < 2800:
    print("Q too small!")
    return

TestCoil.PrintCSV("mm")     # Could also be "in" "ft" or "m"

````

All the calculated parameters one would need are available as members of the Coil() structure:

Parameter   | Object Variable
---|---
Coil Diameter   | TestCoil.D
Coil length     | TestCoil.L
Q (plot)        | TestCoil.Q
Q (calculated)  | TestCoil.Q_eff
N turns         | TestCoil.N
L (inductance)  | TestCoil.L_eff_s
Wire Length     | TestCoil.l_w_phys
Self resonance  | TestCoil.f_res
Coil pitch      | TestCoil.p
Error Code      | TestCoil.error_code
Error Msg       | TestCoil.error_msg     

Note that you can, of course, modify the base parameters and redo the calculations. This is
how the scanning applications work: they start by initializing a Coil() object with basic
parameters, then loop over the parameter of interest.

Something like this:

````
PrintCount = 0
TestCoil.l = lMin - lInc

while TestCoil.l <= lMax:

    TestCoil.l += lInc

    TestCoil.Calculate()

    #
    # Don't print unused entries
    #
    if TestCoil.error_code != 0:
        continue

    #
    # Print an occasional column header, so a human editing the output can
    #   easily see the columns when the full header is offscreen.
    #
    if (PrintCount % 30) == 0:
        TestCoil.PrintCSVColumnHeader(ShowLengthIn);

    TestCoil.PrintCSV("in")

    PrintCount += 1

````


## Coil calculation errors

When an error is encountered, the library will set an error code along with
the corresponding error message. You can print the message or test the error
code as needed.

For example, if the specified number of turns will not fit into the
coil length, or if the self-resonant frequency is lower than the frequency
of use, a coil that solves the initiial conditions is physically
impossible. The system will set an error code and an error message.

The possible errors and their codes are:

Error | Message/Meaning
---|---
1   | An error occurred when solving the dispersion function.
2   | No lumped circuit equivalent is available.
3   | An error occurred when solving for the self-resonant frequency.
4   | Range of turns insufficient to get to specified inductance.
5   | A 5 turn coil is out of range of the algorithm
6   | Resonant frequency less than frequency of interest.
7   | Length insufficient for at least 5 turns


### Calculated Q versus Plotted Q

The library returns two values of Q: calculated, and plottable.

Calculated Q is the numeric value of Q as calculated by the library.

Plottable Q is the numeric Q value if no error is encountered, and NaN for errors.

The plottable Q can be used directly with GnuPlot, since GnuPlot will ignore
NaN as a data value. This will put blanks or gaps in the plotted graph for 
error values, which shows the user only the areas of valid calculation.

## Interpolating turns

The Coil() object can also calculate the number of turns needed to reach a user-specified inductance.

Simply supply all the coil parameters *except* number of turns and call InterpolateTurns with the
inductance needed.


````
####################################################################################################################
#
# InterpolateTurns - Interpolate the number of turns needed to attain a specified inductance
#
# Inputs:   Inductance to attain
#
# Output:   self.N          is set to the number of turns needed to attain the inductance
#           self.error_code is non-zero on calculation error
#           self.error_msg  is a text explanation of the error (or "", if no error occurred)
#
# NOTE: A calculation error usually implies that the requested inductance cannot be physically
#         realized. For example, when the number of turns times the wire diameter exceeds the
#         coil length.
#

TestCoil.InterpolateTurns(LTarget)
````

And here is an example of this feature in practice:

````
PrintCount = 0

TestCoil.l = lMin - lInc
while TestCoil.l <= lMax:

    TestCoil.l += lInc

    TestCoil.InterpolateTurns(LTarget)

    #
    # Don't print unused entries
    #
    if TestCoil.error_code != 0:
        continue

    #
    # Print an occasional column header, so a human editing the output can
    #   easily see the columns when the full header is offscreen.
    #
    if (PrintCount % 30) == 0:
        TestCoil.PrintCSVColumnHeader(ShowLengthIn);

    TestCoil.PrintCSV(ShowLengthIn)

    PrintCount += 1
````




## Generating CSV output

The Coil() object also 

PrintCSV("mm"):

PrintCSVHeader(self,Units="mm",ExtraLine1="",ExtraLine2=""):

PrintCSVColumnHeader(self,Units="mm"):


## A note on maximizing Q

Very high Q RF coils are apparently impossible: some experimenters with excellent setups have
suggested that the maximum Q you can achieve physically is about 1000. (Compare with 50,000
Q variable capacitors that you can purchase). Just about anything – including the presence
of conductive material anywhere in the vicinity of the coil – will tamp down on the Q.

A Q of 200 is a reasonable goal, and 800 might be doable in special circumstances.
