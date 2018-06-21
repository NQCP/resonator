"""
This module contains models for resonators that are operated in transmission
"""
from __future__ import absolute_import, division, print_function

import numpy as np
import lmfit


class TransmissionEqualCouplingsCalibrated(lmfit.model.Model):
    """
    This class models a resonator operated in transmission. It assumes that the coupling losses for both ports are equal
    and that the forward transmission data has been normalized.
    """
    def __init__(self, *args, **kwargs):
        def func(frequency, resonance_frequency, internal_loss, coupling_loss):
            detuning = frequency / resonance_frequency - 1
            return 1 / (1 + (internal_loss + 2j * detuning) / (2 * coupling_loss))
        super(TransmissionEqualCouplingsCalibrated, self).__init__(func=func, *args, **kwargs)

    def guess(self, data, frequency=None):
        """

        :param data: the complex S_{21} data array
        :param frequency: the frequencies corresponding to the data -- this is not an optional parameter
        :return: a Parameters object containing reasonable initial values.
        """
        resonance_frequency_guess = frequency[np.argmax(np.abs(data))]  # guess that the resonance is the highest point
        width = frequency.size // 10
        gaussian = np.exp(-np.linspace(-4, 4, width) ** 2)
        gaussian /= np.sum(gaussian)  # not necessary
        smoothed = np.convolve(gaussian, abs(data), mode='same')
        derivative = np.convolve(np.array([1, -1]), smoothed, mode='same')
        # Exclude the edges, which are affected by zero padding.
        linewidth = (frequency[np.argmin(derivative[width:-width])] -
                     frequency[np.argmax(derivative[width:-width])])
        internal_plus_coupling = linewidth / resonance_frequency_guess
        internal_over_coupling = 2 * (1 / np.max(np.abs(data)) - 1)
        internal_loss_guess = internal_plus_coupling * internal_over_coupling / (1 + internal_over_coupling)
        coupling_loss_guess = internal_plus_coupling / (1 + internal_over_coupling)
        params = self.make_params(resonance_frequency=resonance_frequency_guess, internal_loss=internal_loss_guess,
                                  coupling_loss=coupling_loss_guess)
        params['{}resonance_frequency'.format(self.prefix)].set(min=frequency.min(), max=frequency.max())
        params['{}internal_loss'.format(self.prefix)].set(min=1e-12, max=1)
        params['{}coupling_loss'.format(self.prefix)].set(min=1e-12, max=1)
        return params


def fit_transmission_equal_couplings_calibrated(frequency, data, errors=None):
    model = TransmissionEqualCouplingsCalibrated()
    initial = model.guess(data, frequency=frequency)
    if errors is None:
        weights = None
    else:
        weights = 1 / errors.real + 1j / errors.imag
    result = model.fit(data=data, frequency=frequency, weights=weights, params=initial)
    return result


class TransmissionKnownEqualCouplings(lmfit.model.Model):
    """
    This class models a resonator operated in transmission. It assumes that the coupling losses for both ports are equal
    and known, which allows the fit to solve for another parameter -- the baseline forward transmission.
    """

    def __init__(self, *args, **kwargs):
        def func(frequency, resonance_frequency, internal_loss, coupling_loss, baseline):
            detuning = frequency / resonance_frequency - 1
            return baseline / (1 + (internal_loss + 2j * detuning) / (2 * coupling_loss))
        super(TransmissionKnownEqualCouplings, self).__init__(func=func, *args, **kwargs)

    def guess(self, data, frequency=None, coupling_loss=None):
        """
        Return a lmfit.Parameters object containing reasonable initial values and limits. The frequency array and
        coupling_loss value must be given. The data may be referenced to planes other than the input and output of the
        resonator.

        :param data: the complex S_{21} data array
        :param frequency: the frequencies corresponding to the data -- this is not an optional parameter
        :param coupling_loss: the coupling loss for both ports -- this is not an optional parameter
        :return: lmfit.Parameters
        """
        resonance_frequency_guess = frequency[np.argmax(np.abs(data))]  # guess that the resonance is the highest point
        baseline_guess = np.max(np.abs(data))
        width = frequency.size // 10
        gaussian = np.exp(-np.linspace(-4, 4, width) ** 2)
        gaussian /= np.sum(gaussian)  # not necessary
        smoothed = np.convolve(gaussian, abs(data), mode='same')
        derivative = np.convolve(np.array([1, -1]), smoothed, mode='same')
        # Exclude the edges, which are affected by zero padding.
        linewidth = (frequency[np.argmin(derivative[width:-width])] -
                     frequency[np.argmax(derivative[width:-width])])
        internal_plus_coupling = linewidth / resonance_frequency_guess
        internal_loss_guess = internal_plus_coupling - coupling_loss
        params = self.make_params(resonance_frequency=resonance_frequency_guess, internal_loss=internal_loss_guess,
                                  coupling_loss=coupling_loss, baseline=baseline_guess)
        params['{}resonance_frequency'.format(self.prefix)].set(min=frequency.min(), max=frequency.max())
        params['{}internal_loss'.format(self.prefix)].set(min=1e-12, max=1)
        params['{}coupling_loss'.format(self.prefix)].set(vary=False)
        return params


def fit_transmission_known_equal_couplings(frequency, data, coupling_loss, errors=None):
    model = TransmissionKnownEqualCouplings()
    initial = model.guess(data, frequency=frequency, coupling_loss=coupling_loss)
    if errors is None:
        weights = None
    else:
        weights = 1 / errors.real + 1j / errors.imag
    result = model.fit(data=data, frequency=frequency, weights=weights, params=initial)
    return result


