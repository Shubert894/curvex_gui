import numpy as np
import scipy.signal as ss
from scipy.ndimage import gaussian_filter


def standardize(a):
    mean = np.mean(a)
    std = np.std(a)
    return (a-mean)/std

def normalize(a):
    a = np.array(a)
    diff = a.max() - a.min()
    if diff == 0:
        return a
    else:
        return (a - a.min())/diff

def get_power(a, sf, minF = 1, maxF = 45):
    freqScale, power = ss.periodogram(a, sf, window='tukey', scaling='density')
    argMaxF = np.argmin(np.abs(freqScale-maxF))
    argMinF = np.argmin(np.abs(freqScale-minF))
    freqScale = freqScale[argMinF:argMaxF]
    power = power[argMinF:argMaxF]
    power = gaussian_filter(power, sigma=1)
    return freqScale, power

def filter_data(sig, sf = 512):
    sig = np.array(sig)
    sig[np.abs(sig)>2500] = 0
    n = 10
    Wn = [1/(sf//2),45/(sf//2)]
    b = ss.firwin(n, Wn, pass_zero='bandpass')
    return ss.filtfilt(b, 1, sig)
