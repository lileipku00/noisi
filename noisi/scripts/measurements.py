import numpy as np
from scipy.signal import hilbert
from math import pi, log
from noisi.util.windows import get_window
from noisi.util.plot import plot_window
#def window(wtype,n,i0,i1):
#    win = np.zeros(n)
#    
#    if wtype == None:
#        win += 1.
#    elif wtype == 'boxcar':
#        win[i0:i1] += 1
#    elif wtype == 'hann':
#        win[i0:i1] += np.hanning(i1-i0)
#    return win
#        
#
#def window_checks(i0,i1,i2,i3,n,win_overlap):
#    
#    
#    if n % 2 == 0:
#        print('Correlation length must be 2*n+1, otherwise arbitrary middle \
#sample. This correlation has length 2*n.')
#        return(False)
#    
#    
#    # Check if this will overlap with acausal side
#    if i0 < n/2 - 1 and win_overlap:
#        print('Windows of causal and acausal side overlap. Set win_overlap==False to \
#skip these correlations.')
#        warn(msg)
#        
#    elif i0 < n/2 - 1 and not win_overlap: 
#        print 'Windows overlap, skipping...'
#        return(False)
#        
#    # Out of bounds?
#    if i2 < 0 or i3 > n:
#        print('No windows found. (Noise window not covered by data)')
#        return(False)
#        
#    return(True)
#
#def get_window(stats,g_speed,params):
#    """
#    Obtain a window centered at distance * g_speed
#    stats: obspy Stats object
#    params: dictionary containing 'hw' halfwidth in seconds, 'sep_noise' separation of noise window in multiples of halfwidth,
#    'wtype' window type (None,boxcar, hanning), 'overlap' may signal windows overlap (Boolean)
#    """
#    
#    # Properties of trace
#    s_0 = int((stats.npts-1)/2)
#    dist = stats.sac.dist
#    Fs = stats.sampling_rate
#    n = stats.npts
#    
#    # Find indices for window bounds
#    ind_lo = int((dist/g_speed-params['hw'])*Fs) + s_0
#    ind_hi = int((dist/g_speed+params['hw'])*Fs) + s_0
#    ind_lo_n = ind_hi + int(params['sep_noise']*params['hw']*Fs)
#    ind_hi_n = ind_lo + int(2*params['hw']*Fs)
#    
#    
#    # Checks..overlap, out of bounds
#    scs = window_checks(ind_lo,ind_hi,ind_lo_n,ind_hi_n,n,params['win_overlap'])
#    
#    # Fill signal window
#    win_signal = window(params['wtype'],n,ind_lo,ind_hi)
#    # Fill noise window
#    win_noise = window(params['wtype'],n,ind_lo_n,ind_hi_n)
# 
# 
#    return win_signal, win_noise, scs

    
def envelope(correlation,plot=False):
    
    envelope = correlation.data**2 + np.imag(hilbert(correlation.data))**2
    
    return envelope

def windowed_envelope(correlation,plot=False):
    pass    


def windowed_waveform(correlation,g_speed,window_params):
    window = get_window(correlation.stats,g_speed,window_params)
    win = window[0]
    if window[2]:
        win_caus = (correlation.data * win)
        win_acaus = (correlation.data * win[::-1])
        msr = win_caus+win_acaus
    else:
        msr = win-win+np.nan
    return msr


def energy(correlation,g_speed,window_params):
    
    window = get_window(correlation.stats,g_speed,window_params)
    msr = [np.nan,np.nan]
    #if window_params['causal_side']:
    win = window[0]
    #else:
    #    win = window[0][::-1]
    if window[2]:
        
        # causal 
        E = np.trapz((correlation.data * win)**2)
        msr[0] = E
        if window_params['plot']:
            plot_window(correlation,win,E)

        # acausal 
        win = win[::-1]
        E = np.trapz((correlation.data * win)**2)
        msr[1] = E
        if window_params['plot']:
            plot_window(correlation,win,E)

    return np.array(msr)
    
def log_en_ratio(correlation,g_speed,window_params):
    delta = correlation.stats.delta
    window = get_window(correlation.stats,g_speed,window_params)
    win = window[0]
    if window[2]:
        E_plus = np.trapz((correlation.data * win)**2) * delta
        E_minus = np.trapz((correlation.data * win[::-1])**2) * delta
        msr = log(E_plus/(E_minus+np.finfo(E_minus).tiny))
        if window_params['plot']:
            plot_window(correlation,win,msr)
    else:
        msr = np.nan
    return msr

# This is a bit problematic cause here the misfit already needs
# to be returned (for practical reasons) -- ToDo think about 
# how to organize this better
def inst_mf(corr_obs,corr_syn,g_speed,window_params):
    window = get_window(corr_obs.stats,g_speed,window_params)
    win = window[0]

    if window[2]:
        

        sig1 = corr_obs.data * (win + win[::-1])
        sig2 = corr_syn.data * (win + win[::-1])
    # phase misfit .. try instantaneous phase
    # hilbert gets the analytic signal (only the name is confusing)
        a1 = hilbert(sig1)
        a2 = hilbert(sig2)
    
        cc = a1*np.conjugate(a2)

        boxc = np.clip((win + win[::-1]),0,1)
        dphase = 0.5*np.trapz(np.angle(cc * boxc)**2)

        if window_params['plot']:
            plot_window(corr_obs,win,dphase)
    else:
        dphase = np.nan

    return dphase

def get_measure_func(mtype):
    
    if mtype == 'ln_energy_ratio':
        func = log_en_ratio
    elif mtype == 'energy_diff':
        func = energy
    elif mtype == 'square_envelope':
        func = envelope
    elif mtype == 'windowed_waveform_diff':
        func = windowed_waveform
    elif mtype == 'inst_phase':
        func = inst_mf
    else:
        msg = 'Measurement functional %s not currently implemented.' %mtype
        raise ValueError(msg)
    return func


