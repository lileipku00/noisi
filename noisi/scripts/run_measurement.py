import os
import numpy as np
import pandas as pd
from math import log, pi
import click
import copy
import json
from scipy.signal import hilbert
from glob import glob
from obspy import read, Trace
from obspy.geodetics import gps2dist_azimuth
import matplotlib.pyplot as plt
#ToDo plot if requested.
from noisi.scripts import measurements as rm
#from noisi.scripts import adjnt_functs as af
from noisi.util.windows import get_window, my_centered, snratio
from noisi.util.corr_pairs import get_synthetics_filename
# Get and return measurement as a table or something.


def get_station_info(stats):

    sta1 = '{}.{}.{}.{}'.format(stats.network,stats.station,stats.location,
    stats.channel)
    sta2 = '{}.{}.{}.{}'.format(stats.sac.kuser0.strip(),stats.sac.kevnm.strip(),
    stats.sac.kuser1.strip(),stats.sac.kuser2.strip())
    lat1 = stats.sac.stla
    lon1 = stats.sac.stlo
    lat2 = stats.sac.evla
    lon2 = stats.sac.evlo
    dist = stats.sac.dist
    az,baz = gps2dist_azimuth(lat1,lon1,lat2,lon2)[1:]
    
    
    return([sta1,sta2,lat1,lon1,lat2,lon2,dist,az,baz])







def measurement(source_config,mtype,step,ignore_network,bandpass,step_test,params):
    
    """
    Get measurements on noise correlation data and synthetics. 
    params: window parameters (only needed if mtype is ln_energy_ratio or enery_diff)
    """
    step_n = 'step_{}'.format(int(step))
    
    
    step_dir = os.path.join(source_config['source_path'],
    step_n)
    
    if step_test:
        corr_dir = os.path.join(step_dir,'obs_slt')
    else:
        corr_dir = os.path.join(source_config['source_path'],
    'observed_correlations')


    files = [f for f in os.listdir(corr_dir) ]

    files = [os.path.join(corr_dir,f) for f in files]
    
    synth_dir = os.path.join(step_dir,'corr')
    
    
    columns = ['sta1','sta2','lat1','lon1','lat2','lon2','dist','az','baz',
    'syn','obs','l2_norm','snr','snr_a','nstack']
    measurements = pd.DataFrame(columns=columns)
    
    _options_ac = copy.deepcopy(params)
    _options_ac['causal_side'] = not(params['causal_side'])
    
    
    if files == []:
        msg = 'No input found!'
        raise ValueError(msg)
    
    i = 0
    with click.progressbar(files,label='Taking measurements...') as bar:
        
        for f in bar:
            
            try: 
                tr_o = read(f)[0]
            except:
                print('\nCould not read data: '+os.path.basename(f))
                i+=1
                continue
            try:
                synth_filename = get_synthetics_filename(os.path.basename(f),
                    synth_dir,ignore_network=ignore_network)
                if synth_filename is None:
                    continue
                #sfile = glob(os.path.join(synth_dir,synth_filename))[0]
                #print(synth_filename)
                tr_s = read(synth_filename)[0]
            except:
                print('\nCould not read synthetics: ' + synth_filename)
                i+=1
                continue

            if bandpass is not None:
                tr_o.filter('bandpass',freqmin=bandpass[0],
                    freqmax=bandpass[1],corners=bandpass[2],
                    zerophase=True)
                tr_s.filter('bandpass',freqmin=bandpass[0],
                    freqmax=bandpass[1],corners=bandpass[2],
                    zerophase=True)
              
            tr_s.stats.sac = tr_o.stats.sac.copy() #ToDo: Give the stats to this thing before!
            tr_s.data = my_centered(tr_s.data,tr_o.stats.npts)    
            # Get all the necessary information
            info = get_station_info(tr_o.stats)
           
            # Take the measurement
            func = rm.get_measure_func(mtype)
            try:
                
                msr_o = func(tr_o,params)
                msr_s = func(tr_s,params)

            except:
                print("** Could not take measurement")
                print(f)
                continue
            
            # timeseries-like measurements:
            if mtype in ['envelope','windowed_envelope','waveform',\
            'windowed_waveform']:
                l2_so = np.trapz(0.5*(msr_s-msr_o)**2) * tr_o.stats.delta
                msr = np.nan
                snr = np.nan
                snr_a = np.nan
            # single value measurements:
            else:
                l2_so = 0.5*(msr_s-msr_o)**2
                msr = msr_o
                snr = snratio(tr_o,params)
                snr_a = snratio(tr_o,_options_ac)

            
            info.extend([msr_s,msr,l2_so,snr,snr_a,tr_o.stats.sac.user0])
            measurements.loc[i] = info

            # step index
            i+=1
    
    return measurements
    #filename = '{}.measurement.csv'.format(mtype)
    #measurements.to_csv(os.path.join(step_dir,filename),index=None)

def run_measurement(source_configfile,measr_configfile,
    step,ignore_network,step_test):


    # get parameters    
    source_config=json.load(open(source_configfile))
    all_measr_config=json.load(open(measr_configfile))
    step_dir = os.path.join(source_config['source_path'],"step_{}".format(step))


    for i in range(len(all_measr_config)):

        measr_config = all_measr_config[i]

        mtype = measr_config['mtype']
        bandpass = measr_config['bandpass']
        
        # This is a bit stupid and could be much easier, if the parameter dictionary
        # is directly passed to measurement function.
        # TODo all available misfits --  what parameters do they need (if any.)
        #if measr_config['mtype'] in ['ln_energy_ratio','energy_diff']:
        #    
    #
        #    g_speed                         =    measr_config['g_speed']
        #    window_params                   =    {}
        #    window_params['hw']             =    measr_config['hw']
        #    window_params['sep_noise']      =    measr_config['sep_noise']
        #    window_params['win_overlap']    =    measr_config['win_overlap']
        #    window_params['wtype']          =    measr_config['wtype']
        #    window_params['causal_side']    =    measr_config['causal']
        #    window_params['plot']           =    measr_config['window_plot_measurements']
    
        msr = measurement(source_config,mtype,step,ignore_network,bandpass=bandpass,
            step_test=step_test,params=measr_config)

        filename = '{}.measurement.{}.csv'.format(mtype,i)
        msr.to_csv(os.path.join(step_dir,filename),index=None)
    