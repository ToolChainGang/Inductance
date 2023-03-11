# encoding: utf-8
#
# DESCRIPTION
#    This calculator employs the n = 0 sheath helix waveguide mode
#    to determine the RF inductance of a single‑layer helical round‑wire air‑core coil.
#
#    Unlike quasistatic inductance calculators, this RF inductance calculator allows for
#    more accurate inductance predictions at high frequencies
#    by including the transmission line effects apparent with longer coils.
#
#    Furthermore, the calculator closely follows the National Institute of Standards and Technology (NIST)
#    methodology for applying round wire and non-uniformity correction factors and
#    takes into account both the proximity effect and the skin effect.
#
#
# USAGE
#    See: https://hamwaves.com/inductance/en/index.html
#
#
# COPYRIGHT
#    Copyright (C) 2007-2018  Serge Y. Stroobandt
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
# CONTACT
#    xdg-open mailto:$(echo c2VyZ2VAc3Ryb29iYW5kdC5jb20K |base64 -d)
#
#
# TODO
#    - Replace fzero by Brent's method: 
#        + https://en.wikipedia.org/wiki/Brent's_method
#        + http://people.sc.fsu.edu/~jburkardt/py_src/brent/brent.html
#        + http://people.sc.fsu.edu/~jburkardt/py_src/brent/zero.py
#        + http://www.netlib.org/go/zeroin.f
#    - Z_c inf (400, 200, 420, 1, 1)
#    - f_res (400, 200, 420, 1, .1) improve seeded guesses?
#    - Try fzero for finding f_res.
#    - more precise self-resonant frequency
#
# CHANGES BY PWalsh
#
#   - Converted to pure python
#
#   - Added class members error_code (numeric) and error_msg (text) to communicate
#       error conditions to calling programs
#

VERSION = 20181217

from math import atan, log, pi, sqrt, tan
from mathextra import cot, I0, I1, K0, K1
from fzero import fzero
import time

class Conductor:

    def __init__(self, description, rho, mu_r):
        self.description = description
        self.rho = rho
        self.mu_r = mu_r


class HeaderIndices:

    def __init__(self, header, value):
        '''An object containing a value and its two nearest indices on a table header.'''
        self.value = value

        index2 = 0
        while(value >= header[index2] and index2 < len(header)-1):
            index2 += 1
        self.index2 = index2

        index1 = 0
        if(index2 > 0):
            index1 = index2 - 1
        self.index1 = index1


class Phi_p_d:
    pass    # Used to store interpolation results


### GLOBALS ###


c_0  = 299792458.0
mu_0 = pi * 4E-7
Z_0  = mu_0 * c_0


# plating conductivity and permeability
plating = []
plating.append(Conductor('annealed copper'  , 17.241, 0.99999044))
plating.append(Conductor('hard-drawn copper', 17.71 , 0.99999044))
plating.append(Conductor('silver'           , 15.9  , 0.9999738 ))
plating.append(Conductor('aluminium'        , 28.24 , 1.00002212))


# MEDHURST'S EMPERICAL DATA

# Medhurst matrix lookup rows are l/D.
l_D_header = [0, 0.2, 0.4, 0.6, 0.8, 1, 2, 4, 6, 8, 10, 1E31]

# Medhurst matrix lookup columns are p/d.
p_d_header = [1, 1.111, 1.25, 1.429, 1.667, 2, 2.5, 3.333, 5, 10, 1E31]

# Medhurst matrix
medhurst = []

# l/D ↓          p/d →
medhurst.append([5.31, 3.73, 2.74, 2.12, 1.74, 1.44, 1.20, 1.16, 1.07, 1.02, 1.00])
medhurst.append([5.45, 3.84, 2.83, 2.20, 1.77, 1.48, 1.29, 1.19, 1.08, 1.02, 1.00])
medhurst.append([5.65, 3.99, 2.97, 2.28, 1.83, 1.54, 1.33, 1.21, 1.08, 1.03, 1.00])
medhurst.append([5.80, 4.11, 3.10, 2.38, 1.89, 1.60, 1.38, 1.22, 1.10, 1.03, 1.00])
medhurst.append([5.80, 4.17, 3.20, 2.44, 1.92, 1.64, 1.42, 1.23, 1.10, 1.03, 1.00])
medhurst.append([5.55, 4.10, 3.17, 2.47, 1.94, 1.67, 1.45, 1.24, 1.10, 1.03, 1.00])
medhurst.append([4.10, 3.36, 2.74, 2.32, 1.98, 1.74, 1.50, 1.28, 1.13, 1.04, 1.00])
medhurst.append([3.54, 3.05, 2.60, 2.27, 2.01, 1.78, 1.54, 1.32, 1.15, 1.04, 1.00])
medhurst.append([3.31, 2.92, 2.60, 2.29, 2.03, 1.80, 1.56, 1.34, 1.16, 1.04, 1.00])
medhurst.append([3.20, 2.90, 2.62, 2.34, 2.08, 1.81, 1.57, 1.34, 1.165, 1.04, 1.00])
medhurst.append([3.23, 2.93, 2.65, 2.27, 2.10, 1.83, 1.58, 1.35, 1.17, 1.04, 1.00])
medhurst.append([3.41, 3.11, 2.815, 2.51, 2.22, 1.93, 1.65, 1.395, 1.19, 1.05, 1.00])


### FUNCTIONS ###

########################################################################################################################
#
# Coil - Generate a new "CoilInfo" struct containing the initial parameters
#
# __init__: D,            Diameter of coil
#           N,            Number of turns
#           l,            Length of coil
#           d,            Diameter of wire
#           f,            Frequency of interest
#           plating,      Index into wire plating table
#
class Coil():

    def __init__(self, D,N,l,d,f,plating=0):
        self.D = D             # Diameter of coil
        self.N = N             # Number of turns
        self.l = l             # Length of coil
        self.d = d             # Diameter of wire
        self.f = f             # Frequency of interest
        self.plating = plating # Index into wire plating table

        self.beta = 0
        self.C_p = 0
        self.D_eff = 0
        self.delta_i = 0
        self.f_res = 0
        self.k_L = 0
        self.k_m = 0
        self.k_s = 0
        self.L_eff_s = 0
        self.L_s = 0
        self.l_w_eff = 0
        self.l_w_phys = 0
        self.mu_r_w = 0
        self.p = 0
        self.Phi = 0
        self.psi = 0
        self.Q_eff = 0
        self.R_eff_s = 0
        self.rho = 0
        self.R_s = 0
        self.txt = 0
        self.X_eff_s = 0
        self.Z_c = 0

        self.error_code = 0
        self.error_msg  = ""

        self.Calculate()

     #
     # __repr__ allows user to use pprint on this object
     #
    def __repr__(self):
        return "{}:".format(self.__class__.__name__) + " {\n" + ''.join("    %s: %s,\n" % item for item in vars(self).items()) + "    }\n"

    def lookup_Phi(self, l, D, p, d):
        l_D = HeaderIndices(l_D_header, l/D)
        p_d = HeaderIndices(p_d_header, p/d)

        # triple linear interpolation
        # h-h1 = (h2-h1) / (x2-x1) * (x-x1)
        # Phi_p_d_index1 = (Phi2 - Phi1) / (l_D.index2 - l_D.index1) * (l/D - l_D.index1) + Phi1
        Phi_p_d.index1  = medhurst[l_D.index2][p_d.index1] - medhurst[l_D.index1][p_d.index1]
        Phi_p_d.index1 /= l_D_header[l_D.index2] - l_D_header[l_D.index1]
        Phi_p_d.index1 *= l/D - l_D_header[l_D.index1]
        Phi_p_d.index1 += medhurst[l_D.index1][p_d.index1]

        Phi_p_d.index2  = medhurst[l_D.index2][p_d.index2] - medhurst[l_D.index1][p_d.index2]
        Phi_p_d.index2 /= l_D_header[l_D.index2] - l_D_header[l_D.index1]
        Phi_p_d.index2 *= l/D - l_D_header[l_D.index1]
        Phi_p_d.index2 += medhurst[l_D.index1][p_d.index2]

        Phi  = Phi_p_d.index2 - Phi_p_d.index1
        Phi /= p_d_header[p_d.index2] - p_d_header[p_d.index1]
        Phi *= p/d - p_d_header[p_d.index1]
        Phi += Phi_p_d.index1
        return Phi


    def find_f_res(self):
        # Secant method root finding algorithm
        # Loosely based upon http://www.see.ed.ac.uk/~jwp/JavaScript/programming/chop2.html

        x_1 = c_0 / l_w_eff / 40.0
        x_2 = x_1 * 100.0
        max_tries = 40

        for tries in range(-1, max_tries+1):    # <= max

            if tries == -1:
                x = x_1
            if tries == 0:
                x = x_2
            if tries > 0:
                x = (x_1 + x_2) / 2.0

            # First, solve the sheath helix dispersion function for tau at frequency x.
            omega = 2.0 * pi * x
            k_0 = omega / c_0

            F = lambda tau: K1(tau*a) * I1(tau*a) / K0(tau*a) / I0(tau*a) - (tau / k_0 * tan(psi))**2

            tau_1 = k_0 * cot(psi)**2 - k_0**2    # an estimate
            tau_2 = k_0                           # another estimate
            zero = fzero(F, tau_1, tau_2)
            if zero['error_code'] == 2:
                alert('****An error occurred when solving for the resonant frequency.\n'
                    + 'However, all shown results are useable.\n\n'
                    + zero['error_msg'])
                document['f_res'] = ''
            tau = zero['zero']

            # Then, check for resonance.
            # β² = k_0² + τ²
            # βℓ → π/2
            fx = sqrt(k_0**2 + tau**2) * l - pi/2.0

            if tries == -1:
                fx_1 = fx
            if tries == 0:
                fx_2 = fx
            if tries <= 0:
                continue

            if fx * fx_1 > 0:
                fx_1 = fx
                x_1 = x
            else:
                fx_2 = fx
                x_2 = x

        return x


    ########################################################################################################################
    #
    # CoilInfo.Calculate - Calculate coil parameters from initial conditions
    #
    # __init__: D,            Diameter of coil
    #           N,            Number of turns
    #           l,            Length of coil
    #           d,            Diameter of wire
    #           f,            Frequency of interest
    #           plating,      Index into wire plating table
    #
    # Output:   Generate all the rest of the struct parameters
    #
    def Calculate(self):

        self.summary    = ""
        self.error_code = 0
        self.error_msg  = ""

        try:
            plating_nr = int(self.plating)
            rho = plating[plating_nr].rho * 1E-9
            mu_r_w = plating[plating_nr].mu_r
            self.rho = rho * 1E9
            self.mu_r_w = mu_r_w

            N = float(self.N)
            global l
            l = float(self.l) * 1E-3
            p = l / N
            self.p = round(p * 1E3, 2)

            D = float(self.D) * 1E-3
            d = float(self.d) * 1E-3
            Phi = self.lookup_Phi(l, D, p, d)
            self.Phi = round(Phi, 2)

            D_eff = D - d * (1.0 - 1.0/sqrt(Phi))
            self.D_eff = round(D_eff * 1E3, 2)


            # Correction factors

            if l <= D_eff:    # The short coil expression gives a value that agrees better with the AGM result.
                k_L  = 1.0 + 0.383901 * (l/D_eff)**2 + 0.017108 * (l/D_eff)**4
                k_L /= 1.0 + 0.258952 * (l/D_eff)**2
                k_L *= log(4.0 * D_eff/l) - 0.5
                k_L += 0.093842 * (l/D_eff)**2 + 0.002029 * (l/D_eff)**4 - 0.000801 * (l/D_eff)**6
                k_L *= 2.0/pi * l/D_eff
            else:
                k_L  = 1.0 + 0.383901 * (D_eff/l)**2 + 0.017108 * (D_eff/l)**4
                k_L /= 1.0 + 0.258952 * (D_eff/l)**2
                k_L -= 4.0/3.0/pi * D_eff/l
            self.k_L = round(k_L, 6)

            k_s = 5.0/4.0 - log(2 * p/d)
            self.k_s = round(k_s, 6)

            c_9 = -log(2.0*pi) +3.0/2.0 +0.33084236 +1.0/120.0 -1.0/504.0 +0.0011925
            k_m  = log(2.0*pi) -3.0/2.0 -log(N)/6.0/N -0.33084236/N -1.0/(120.0*N**3) +1.0/(504.0*N**5) -0.0011925/N**7 + c_9/N**9
            self.k_m = round(k_m, 8)


            # Effective series AC resistance

            l_w_phys = sqrt((N * pi * D)**2 + l**2)
            self.l_w_phys = round(l_w_phys * 1E3, 1)

            global l_w_eff
            l_w_eff = sqrt((N * pi * D_eff)**2 + l**2)
            self.l_w_eff = round(l_w_eff * 1E3, 1)

            f = float(self.f) * 1E6
            delta_i = sqrt(rho /pi /f /mu_0 /mu_r_w)
            self.delta_i = round(delta_i * 1E6, 2)

            R_eff_s  = rho * l_w_eff
            R_eff_s /= pi * (d * delta_i - delta_i**2)
            R_eff_s *= Phi
            if(N > 1):
                R_eff_s *= (N-1.0) / N
            self.R_eff_s = round(R_eff_s, 3)


            # Corrected current-sheet geometrical formula

            mu_r_core = 1
            L_s  = pi * (D_eff * N)**2 /4.0 /l * k_L
            L_s -= D_eff * N * (k_s + k_m) / 2.0
            L_s *= mu_r_core * mu_0
            self.L_s = round(L_s * 1E6, 3)

            global psi
            psi = atan(p /pi /D_eff)
            self.psi = round(psi / pi * 180, 2)


            # Copy & paste text field
            t = time.time()
            self.summary += '# QOIL™ — https://hamwaves.com/qoil/ — v{}\n'.format(VERSION)
            self.summary += time.strftime('#   Coil design %Y-%m-%d %H:%M\n', time.localtime(t))

            offset = 28
            self.summary += '# \nINPUT\n'
            self.summary += '#   {:{offset}} D = {} mm\n'        .format('mean diameter of the coil', self.D, offset=offset)
            self.summary += '#   {:{offset}} N = {}\n'           .format('number of turns'          , self.N, offset=offset)
            self.summary += '#   {:{offset}} ℓ = {} mm\n'        .format('length of the coil'       , self.l, offset=offset)
            self.summary += '#   {:{offset}} d = {} mm\n'        .format('wire or tubing diameter'  , self.d, offset=offset)
            self.summary += '#   {:{offset}} f = {} MHz\n'       .format('design frequency'         , self.f, offset=offset)
            self.summary += '#   The (plating) material is {}.\n'.format(plating[plating_nr].description)

            self.summary += '# \nINTERMEDIATE RESULTS\n'
            self.summary += '#   {:{offset}} p = {} mm\n'        .format('winding pitch'            , self.p, offset=offset)
            self.summary += '#   {:{offset}} ℓ_w_phys = {} mm\n' .format('physical conductor length', self.l_w_phys, offset=offset)
            self.summary += '#   {:{offset}} ψ = {}°\n'          .format('effective pitch angle'    , self.psi, offset=offset)


            # Characteristic impedance of the sheath helix waveguide mode

            offset = 55
            try:
                omega = 2.0 * pi * f
                k_0 = omega / c_0
                global a
                a = D_eff / 2.0

                # Sheath helix dispersion function
                F = lambda tau: K1(tau*a) * I1(tau*a) / (K0(tau*a) * I0(tau*a)) - (tau / k_0 * tan(psi))**2

                tau_1 = k_0                  # smallest tau estimate
                tau_2 = k_0 * cot(psi)**2    # largest tau estimate
                zero = fzero(F, tau_1, tau_2)
                tau = zero['zero']
                beta = sqrt(k_0**2 + tau**2)
                self.beta = round(beta, 4)

                Z_c = 60.0 * beta / k_0 * I0(tau*a) * K0(tau*a)
                self.Z_c = round(Z_c, 1)


                # Effective equivalent circuit

                # Corrected sheath helix waveguide formula
                L_eff_s  = Z_c / omega * tan(beta * l) * k_L
                L_eff_s -= mu_0 * D_eff * N * (k_s + k_m) / 2.0
                self.L_eff_s = round(L_eff_s * 1E6, 3)

                X_eff_s = omega * L_eff_s
                self.X_eff_s = round(X_eff_s, 1)

                Q_eff = X_eff_s / R_eff_s
                self.Q_eff = int(Q_eff)


                # Effective circuit results in copy & paste text field
                self.summary += '# \nRESULTS\n'
                self.summary += '#   Effective equivalent circuit\n'
                self.summary += '#     {:{offset}} L_eff_s = {} μH\n'.format('effective series inductance @ design frequency'      , self.L_eff_s, offset=offset)
                self.summary += '#     {:{offset}} X_eff_s = {} Ω\n' .format('effective series reactance @ design frequency'       , self.X_eff_s, offset=offset)
                self.summary += '#     {:{offset}} R_eff_s = {} Ω\n' .format('effective series AC resistance @ design frequency'   , self.R_eff_s, offset=offset)
                self.summary += '#     {:{offset}} Q_eff   = {}\n'   .format('effective unloaded quality factor @ design frequency', self.Q_eff  , offset=offset)

            except:
                self.summary += '#   Lumped circuit equivalent\n'
                self.summary += '#     {:{offset}} L_s = {} μH\n'    .format('f-independent series inductance; geometrical formula', self.L_s    , offset=offset)
                self.summary += '# \n'
                self.summary += '# ****An error occurred when solving the dispersion function!\n'
                self.summary += '#     However, all shown results are useable.\n'

                self.beta    = 0
                self.Z_c     = 0
                self.L_eff_s = 0
                self.X_eff_s = 0
                self.Q_eff   = 0
                self.R_s     = 0
                self.C_p     = 0
                self.f_res   = 0

                self.error_code = 1
                self.error_msg  = 'An error occurred when solving the dispersion function.'


            try:
                # Lumped equivalent circuit

                R_p = (Q_eff**2 + 1) * R_eff_s
                X_L_s = omega * L_s

                # https://en.wikipedia.org/wiki/Quadratic_equation#Reduced_quadratic_equation
                P = R_p / (2.0 * X_L_s)
                Q_L = P + sqrt(P**2 - 1)

                R_s = X_L_s / Q_L
                self.R_s = round(R_s, 3)

                X_eff_p = (Q_eff**2 + 1.0) / Q_eff**2 * X_eff_s
                X_L_p = (Q_L**2 + 1.0) / Q_L**2 * X_L_s

                X_C_p = X_eff_p * X_L_p / (X_L_p - X_eff_p)
                C_p = -1.0 /omega /X_C_p
                self.C_p = round(C_p * 1E12, 1)


                # Lumped circuit results in copy & paste text field
                self.summary += '#   Lumped circuit equivalent\n'
                self.summary += '#     {:{offset}} L_s     = {} μH\n'.format('f-independent series inductance; geometrical formula', self.L_s, offset=offset)
                self.summary += '#     {:{offset}} R_s     = {} Ω\n' .format('series AC resistance @ design frequency'             , self.R_s, offset=offset)
                self.summary += '#     {:{offset}} C_p     = {} pF\n'.format('parallel stray capacitance @ design frequency'       , self.C_p, offset=offset)


            except:
                self.summary += '#   Lumped circuit equivalent\n'
                self.summary += '#     {:{offset}} L_s     = {} μH\n'.format('f-independent series inductance; geometrical formula', self.L_s, offset=offset)
                self.summary += '# \n'
                self.summary += '#     No lumped circuit equivalent is available!\n'
                self.summary += '#     However, all shown results are useable.\n'

                self.R_s   = 0
                self.C_p   = 0
                self.f_res = 0

                self.error_code = 2
                self.error_msg  = 'No lumped circuit equivalent is available.'


            offset = 57
            try:
                # Self‑resonant frequency

                f_res = self.find_f_res()
                self.f_res = round(f_res * 1E-6, 3)


                # Resonant frequency in copy & paste text field
                self.summary += '#   {:{offset}} f_res   = {} MHz\n'.format('Self-resonant frequency', self.f_res, offset=offset)


            except:
                self.summary += '\n'
                self.summary += '# **** An error occurred when solving for the self-resonant frequency!\n'
                self.summary += '#      However, all shown results are useable.\n'
                self.f_res   = 0
                self.error_code = 3
                self.error_msg  = 'An error occurred when solving for the self-resonant frequency.'


            self.summary += '# \nDONATE\n'
            self.summary += '#   If this calculator proved any useful to you,\n'
            self.summary += '#   please, consider making a one-off donation\n'
            self.summary += '#   towards keeping me and the server up and running.\n'
            self.summary += '#   Thank you!'


        except:
#            self.summary = ""    # COMMENT THIS LINE FOR TESTING PROGRESS
            self.summary += '# \n'
            self.summary += '# ****An error occurred when solving for the self-resonant frequency!\n'
            self.summary += '#     No results are available.\n'

            self.p        = 0
            self.Phi      = 0
            self.D_eff    = 0
            self.k_L      = 0
            self.k_s      = 0
            self.k_m      = 0
            self.l_w_phys = 0
            self.l_w_eff  = 0
            self.delta_i  = 0
            self.R_eff_s  = 0
            self.L_s      = 0
            self.psi      = 0
            self.beta     = 0
            self.Z_c      = 0
            self.L_eff_s  = 0
            self.X_eff_s  = 0
            self.Q_eff    = 0
            self.R_s      = 0
            self.C_p      = 0
            self.f_res    = 0

            self.error_code = 4
            self.error_msg  = 'An error occurred when solving for the self-resonant frequency.'


    ####################################################################################################################
    #
    # IDiff - Calculate new impedance and return difference from target impedance
    #
    # Inputs:   New Turns to calculate impedance for
    #
    # Output:   Difference from newly calculated impedance and target impedance
    #
    # Used by fzero() when interpolating the coil turns ("N") so that the proposed test
    #   coil matches the target impedance.
    #
    def IDiff(self,Turns):
        self.N = Turns
        self.Calculate()

#        print("==============")
#        print("Turns: ",Turns)
#        print("Ind  : ",self.L_eff_s)
#        print("Ret  : ",self.LTarget - self.L_eff_s)

        return self.LTarget - self.L_eff_s


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
    def InterpolateTurns(self,LTarget):
        self.LTarget = LTarget

        #
        # Before we interpolate N, we need to find a pair of starting N that is both physically
        #   realizable and brackets the target inductance.
        #
        # This is more difficult than it seems, because a lot of physically realizable N values
        #   push the calculations beyond reasonable - resulting in (for example) a negative inductance.
        #   Furthermore, the calculated values of impedance sometimes *oscillate* between positive
        #   and negative per turns, so choosing two N values which both return positive inductance may
        #   bracket a range of N for which the inductance is negative.
        #
        # Yuck. I don't have a really good solution yet. The following seems to work for my test cases.
        #


        #
        # Start by calculating a pitch of 2*d - this is usually valid and high Q.
        #
        NStart = self.l / (self.d*2)

        if NStart < 5:
            self.error_code = 7
            self.error_msg  = 'Length insufficient for at least 5 turns'
            return

        self.N = NStart
        self.Calculate()

        LStart = self.L_eff_s

        if LStart < 0:
            self.error_code = 8
            self.error_msg  = 'A 5 turn coil is out of range of the algorithm'
            return

        #
        # If the test inductance is smaller, interpolate to a larger number of turns,
        #   else interpolate to 5 turns.
        #
        NEnd = self.l / (self.d*1.05)

        if LStart > LTarget:
            NEnd = 5

#        #  DEBUG
#        self.N = NEnd
#        self.Calculate()
#        LEnd = self.L_eff_s
#        #  END_DEBUG

        Results = fzero(lambda Turns: self.IDiff(Turns), NStart, NEnd)

#        #  DEBUG
#        print("NStart=%g" % NStart + ", LStart=%g" % LStart)
#        print("NEnd  =%g" % NEnd   + ", LEnd  =%g" % LEnd  )
#        print("NInt  =%g" % self.N + ", LInt  =%g" % self.L_eff_s + ", Err =%d" % Results['error_code'])
#        if Results['error_code'] != 0:
#            print(Results['error_msg'])
#        #  END_DEBUG

        #
        # Caclulation error: No need to make further checks
        #
        if self.error_code != 0:
            return

        #
        # Error 4: Range of turns insufficient to get to specified inductance
        #
        if Results['error_code'] == 4:
            self.error_code = 5
            self.error_msg  = 'Range of turns insufficient to get to specified inductance.'
            return

        #
        # Ignore coils for which f_res < F (Which would make C_p negative, and other problems)
        #
        if self.f_res < self.f:
            self.error_code = 6
            self.error_msg  = 'Resonant frequency less than frequency of interest.'
            return

    ####################################################################################################################
    #
    # PrintCVSHeader - Print CVS output header
    #
    # Inputs:   "mm"    If length output should be in mm (default)
    #           "m"     If                            m
    #           "in"    If                            in
    #           "ft"    If                            ft
    #           ExtraLine1 of header info to be printed 
    #           ExtraLine2 of header info to be printed 
    #
    # Output:   The CSV header information is printed
    #
    def PrintCSVHeader(self,Units="mm",ExtraLine1="",ExtraLine2=""):

        LenHdr = "wLen(mm)"

        if Units == "m":
            LenHdr = "wLen(m)"

        if Units == "in":
            LenHdr = "wLen(in)"

        if Units == "ft":
            LenHdr = "wLen(ft)"

        print(time.strftime("# CoilScan %Y-%m-%d %H:%M", time.localtime(time.time())))
        print("#")
        print("# LTarget = %g, " % self.LTarget + "d = %g, " % self.d + "p = %d, " % self.p + "f = %g" % self.f)
        print("#")

        if ExtraLine1 != "":
            print(ExtraLine1)

        if ExtraLine2 != "":
            print(ExtraLine2)

        if ExtraLine1 != "" or ExtraLine2 != "":
            print("#")

    ####################################################################################################################
    #
    # PrintCSVColumnHeader - Print column headers for coil CSV line
    #
    # Inputs:   "mm"    If length output should be in mm (default)
    #           "m"     If                            m
    #           "in"    If                            in
    #           "ft"    If                            ft
    #
    # Output:   The single-line colum header is printed
    #
    def PrintCSVColumnHeader(self,Units="mm"):
        LenHdr = "wLen(mm)"

        if Units == "m":
            LenHdr = "wLen(m)"

        if Units == "in":
            LenHdr = "wLen(in)"

        if Units == "ft":
            LenHdr = "wLen(ft)"

        print("# D(mm),   l(mm), Q(plot),      Q,       N,    L(uH), " + LenHdr + ", Res(MHz), pitch(mm), Err, Cmd")

    ####################################################################################################################
    #
    # PrintCVS - Print coil as CVS entry
    #
    # Inputs:   "mm"    If length output should be in mm (default)
    #           "m"     If                            m
    #           "in"    If                            in
    #           "ft"    If                            ft
    #
    # Output:   The coil is printed as 1 CVS line
    #
    def PrintCSV(self,Units="mm"):

        Length = self.l_w_phys

        if Units == "m":
            Length /= 1000

        if Units == "in":
            Length /= 25.4

        if Units == "ft":
            Length = (Length/25.4)/12

        SummaryCMD  = "CoilCalc"
        SummaryCMD += " --D=%.3f" % round(self.D,2)
        SummaryCMD += " --l=%.3f" % round(self.l,2)
        SummaryCMD += " --N=%.3f" % round(self.N,2)
        SummaryCMD += " --d=%.3f" % round(self.d,2)
        SummaryCMD += " --f=%.3f" % round(self.f,3)

        #
        # Gnuplot will silently ignore data points containing "NaN", so for points that
        #   don't make sense we print NaN for Q. Actual Q is also the next column.
        #
        PlotQ = self.Q_eff

        if self.error_code != 0:
            PlotQ = float('nan')

        print('%7.2f, ' % round(self.D       , 2) +
              '%7.2f, ' % round(self.l       , 2) +
              '%7.0f, ' % round(PlotQ        , 2) +
              '%7.0f  ' % round(self.Q_eff   , 2) + 
              '%6.2f, ' % round(self.N       , 2) +
              '%8.2f, ' % round(self.L_eff_s , 2) + 
              '%8.2f, ' % round(Length       , 2) +
              '%8.2f, ' % round(self.f_res   , 2) + 
              '%9.2f, ' % round(self.p       , 2) + 
              '%3d, '   % self.error_code         +
              '"' + SummaryCMD + '"')
