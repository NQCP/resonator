"""
This module contains models and fitters for resonators that are operated in the reflection configuration.
"""
from __future__ import absolute_import, division, print_function

import numpy as np

from . import background, base, guess, linear, kerr, kerr_nlLoss


class AbstractReflection(base.ResonatorModel):
    """
    This is abstract class that models a resonator operated in reflection.
    """

    # This is the value of the scattering data far from resonance.
    reference_point = -1 + 0j

    # See kerr.kerr_detuning_shift
    io_coupling_coefficient = 1


# Linear models and fitters

class LinearReflection(AbstractReflection):
    """
    This class models a linear resonator operated in reflection.
    """

    def __init__(self, *args, **kwds):
        """
        :param args: arguments passed directly to lmfit.model.Model.__init__().
        :param kwds: keywords passed directly to lmfit.model.Model.__init__().
        """

        def linear_reflection(frequency, resonance_frequency, coupling_loss, internal_loss):
            detuning = frequency / resonance_frequency - 1
            return -1 + (2 / (1 + (internal_loss + 2j * detuning) / coupling_loss))

        super(LinearReflection, self).__init__(func=linear_reflection, *args, **kwds)

    def guess(self, data=None, frequency=None, **kwds):
        resonance_frequency, coupling_loss, internal_loss = guess.guess_smooth(frequency=frequency, data=data)
        params = self.make_params()
        params['resonance_frequency'].set(value=resonance_frequency, min=frequency.min(), max=frequency.max())
        params['coupling_loss'].set(value=coupling_loss, min=1e-12, max=1)
        params['internal_loss'].set(value=internal_loss, min=1e-12, max=1)
        return params


class LinearReflectionFitter(linear.LinearResonatorFitter):
    """
    This class fits data from a linear resonator operated in reflection.
    """

    def __init__(self, frequency, data, background_model=None, errors=None, **kwds):
        if background_model is None:
            background_model = background.MagnitudePhase()
        super(LinearReflectionFitter, self).__init__(frequency=frequency, data=data,
                                                     foreground_model=LinearReflection(),
                                                     background_model=background_model, errors=errors, **kwds)

    def invert(self, scattering_data):
        z = self.coupling_loss * (2 / (1 + scattering_data) - 1)
        detuning = z.imag / 2
        internal_loss = z.real
        return detuning, internal_loss


class KnownLinearReflectionFitter(LinearReflectionFitter):
    """
    This class fits data from a linear resonator operated in reflection.
    """

    def __init__(self, frequency, data, background_frequency, background_data, errors=None, **kwds):
        # Compensate for the pi phase shift present in the reflected background data.
        background_model = background.Known(measurement_frequency=background_frequency,
                                            measurement_data=background_data / LinearReflection.reference_point)
        super(LinearReflectionFitter, self).__init__(frequency=frequency, data=data, background_model=background_model,
                                                     errors=errors, **kwds)


# Kerr models and fitters

class KerrReflection(AbstractReflection):
    """
    This class models a resonator operated in reflection with a Kerr-type nonlinearity.
    """

    def __init__(self, choose, *args, **kwds):
        """
        :param choose: a numpy ufunc; see `nonlinear.Kerr.kerr_detuning_shift`.
        :param args: arguments passed directly to `lmfit.model.Model.__init__`.
        :param kwds: keywords passed directly to `lmfit.model.Model.__init__`.
        """

        def kerr_reflection(frequency, resonance_frequency, coupling_loss, internal_loss, kerr_input):
            detuning = frequency / resonance_frequency - 1
            shift = kerr.kerr_detuning_shift(detuning=detuning, coupling_loss=coupling_loss,
                                             internal_loss=internal_loss, kerr_input=kerr_input,
                                             io_coupling_coefficient=self.io_coupling_coefficient,
                                             choose=choose)
            return -1 + (2 / (1 + (internal_loss + 2j * (detuning - shift)) / coupling_loss))

        super(KerrReflection, self).__init__(func=kerr_reflection, *args, **kwds)

    def guess(self, data=None, frequency=None, **kwds):
        resonance_frequency, coupling_loss, internal_loss = guess.guess_smooth(frequency=frequency, data=data)
        params = self.make_params()
        params['resonance_frequency'].set(value=resonance_frequency, min=frequency.min(), max=frequency.max())
        params['coupling_loss'].set(value=coupling_loss, min=1e-12, max=1)
        params['internal_loss'].set(value=internal_loss, min=1e-12, max=1)
        params['kerr_input'].set(value=0)
        return params

    @classmethod
    def absolute_kerr_input_at_bifurcation(cls, coupling_loss, internal_loss):
        return kerr.absolute_kerr_input_at_bifurcation(coupling_loss=coupling_loss, internal_loss=internal_loss,
                                                       io_coupling_coefficient=cls.io_coupling_coefficient)


class KerrReflectionFitter(kerr.KerrFitter):
    """
    This class fits data from a resonator operated in reflection with a Kerr-type nonlinearity.
    """

    def __init__(self, frequency, data, choose=np.max, background_model=None, errors=None, **fit_kwds):
        if background_model is None:
            background_model = background.MagnitudePhase()
        super(KerrReflectionFitter, self).__init__(frequency=frequency, data=data, choose=choose,
                                                   foreground_model=KerrReflection(choose=choose),
                                                   background_model=background_model, errors=errors, **fit_kwds)

    # ToDo: math
    def invert(self, scattering_data):
        pass


class KerrNlLossReflection(AbstractReflection):
    """
    This class models a resonator operated in reflection with a Kerr-type nonlinearity with non linear losses
    """

    def __init__(self, choose, *args, **kwds):
        """
        :param choose: a numpy ufunc; see `nonlinear.Kerr.kerr_detuning_shift`.
        :param args: arguments passed directly to `lmfit.model.Model.__init__`.
        :param kwds: keywords passed directly to `lmfit.model.Model.__init__`.
        """

        def kerr_reflection(frequency, resonance_frequency, coupling_loss, internal_loss, nl_int_loss_over_2K, kerr_input):
            detuning = frequency / resonance_frequency - 1
            shift = kerr_nlLoss.kerr_detuning_shift(detuning=detuning, coupling_loss=coupling_loss,
                                             internal_loss=internal_loss, nl_int_loss_over_2K = nl_int_loss_over_2K,
                                             kerr_input=kerr_input,
                                             io_coupling_coefficient=self.io_coupling_coefficient,
                                             choose=choose)
            return -1 + (2 / (1 + (internal_loss + 2 * nl_int_loss_over_2K * np.abs(shift) + 2j * (detuning - shift)) / coupling_loss))

        super(KerrNlLossReflection, self).__init__(func=kerr_reflection, *args, **kwds)

    def guess(self, data=None, frequency=None, **kwds):
        resonance_frequency, coupling_loss, internal_loss = guess.guess_smooth(frequency=frequency, data=data)
        params = self.make_params()
        params['resonance_frequency'].set(value=resonance_frequency, min=frequency.min(), max=frequency.max())
        params['coupling_loss'].set(value=coupling_loss, min=1e-12, max=1)
        params['internal_loss'].set(value=internal_loss, min=1e-12, max=1)
        params['nl_int_loss_over_2K'].set(value=0, min=0)
        params['kerr_input'].set(value=0)
        return params

    @classmethod
    def absolute_kerr_input_at_bifurcation(cls, coupling_loss, internal_loss):
        return kerr_nlLoss.absolute_kerr_input_at_bifurcation(coupling_loss=coupling_loss, internal_loss=internal_loss,
                                                       io_coupling_coefficient=cls.io_coupling_coefficient)


class KerrNlLossReflectionFitter(kerr_nlLoss.KerrNlLossFitter):
    """
    This class fits data from a resonator operated in reflection with a Kerr-type nonlinearity.
    """

    def __init__(self, frequency, data, choose=np.max, background_model=None, errors=None, **fit_kwds):
        if background_model is None:
            background_model = background.MagnitudePhase()
        super(KerrNlLossReflectionFitter, self).__init__(frequency=frequency, data=data, choose=choose,
                                                   foreground_model=KerrNlLossReflection(choose=choose),
                                                   background_model=background_model, errors=errors, **fit_kwds)

    # ToDo: math
    def invert(self, scattering_data):
        pass
