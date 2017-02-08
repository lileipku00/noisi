import os
import numpy as np
from math import log, pi
import click
import json
from scipy.signal import hilbert
from glob import glob
from obspy import read, Trace
from obspy.geodetics import gps2dist_azimuth

from noisi.scripts import adjnt_functs as af
from noisi.util.corr_pairs import get_synthetics_filename
from noisi.util.windows import get_window, my_centered, snratio


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
    az = gps2dist_azimuth(lat1,lon1,lat2,lon2)[2]
    
    
    return([sta1,sta2,lat1,lon1,lat2,lon2,dist,az])

def get_essential_sacmeta(sac):

    newsacdict={}
    #==============================================================================
    #- Essential metadata  
    #==============================================================================
     
    newsacdict['user0']   =   sac['user0'] 
    newsacdict['b']       =   sac['b']     
    newsacdict['e']       =   sac['e']     
    newsacdict['stla']    =   sac['stla']  
    newsacdict['stlo']    =   sac['stlo']  
    newsacdict['evla']    =   sac['evla']  
    newsacdict['evlo']    =   sac['evlo']  
    newsacdict['dist']    =   sac['dist']  
    newsacdict['az']      =   sac['az']    
    newsacdict['baz']     =   sac['baz']   
    newsacdict['kuser0']  =   sac['kuser0']
    newsacdict['kuser1']  =   sac['kuser1']
    newsacdict['kuser2']  =   sac['kuser2']
    newsacdict['kevnm']   =   sac['kevnm']

    return newsacdict

# def get_synthetics_filename(obs_filename,dir,ignore_network,synth_location='',
#     fileformat='sac',synth_channel_basename='MX'):

#     inf = obs_filename.split('--')

#     if len(inf) == 1:
#         # old station name format
#         inf = obs_filename.split('.')
#         net1 = inf[0]
#         sta1 = inf[1]
#         cha1 = inf[3]
#         net2 = inf[4]
#         sta2 = inf[5]
#         cha2 = inf[7]
#     elif len(inf) == 2:
#         # new station name format
#         inf1 = inf[0].split('.')
#         inf2 = inf[1].split('.')
#         net1 = inf1[0]
#         sta1 = inf1[1]
#         net2 = inf2[0]
#         sta2 = inf2[1]
#         cha1 = inf1[3]
#         cha2 = inf2[3]


#     cha1 = synth_channel_basename + cha1[-1]
#     cha2 = synth_channel_basename + cha2[-1]

#     if ignore_network:
#         synth_filename = '*.{}.{}.{}--*.{}.{}.{}.{}'.format(sta1,synth_location,
#         cha1,sta2,synth_location,cha2,fileformat)
#     else:
#         synth_filename = '{}.{}.{}.{}--{}.{}.{}.{}.{}'.format(net1,sta1,synth_location,
#         cha1,net2,sta2,synth_location,cha2,fileformat)
    
#     try: 
#         sfilename = glob(os.path.join(dir,synth_filename))[0]
#         return(sfilename)
#     except IndexError:
#         print('No synthetic file found at:')
#         print(synth_filename)
#         return None


def adjointsrcs(f,f_syn,m_params):
    
    """
    Get 'adjoint source' from noise correlation data and synthetics. 
    options: g_speed,window_params (only needed if mtype is ln_energy_ratio or enery_diff)
    """
    
    
    # files = [f for f in os.listdir(os.path.join(source_config['source_path'],
    # 'observed_correlations')) ]
    # files = [os.path.join(source_config['source_path'],
    # 'observed_correlations',f) for f in files]
    
   
    # step_n = 'step_{}'.format(int(step))
    # synth_dir = os.path.join(source_config['source_path'],
    # step_n,'corr')
    # adj_dir = os.path.join(source_config['source_path'],
    # step_n,'adjt')
    
    
   
    # if files == []:
    #     msg = 'No input found!'
    #     raise ValueError(msg)
    
    #i = 0
    #with click.progressbar(files,label='Determining adjoint sources...') as bar:
        
        #for f in bar:


            
    try: 
        tr_o = read(f)[0]
    except:
        print('\nCould not read data: '+os.path.basename(f))
        return [],success
        #i+=1
        #continue
    # try:
    #     synth_filename = get_synthetics_filename(os.path.basename(f),synth_dir,
    #         ignore_network=ignore_network)
    #     if synth_filename is None:
    #         continue
    #     #sname = glob(os.path.join(synth_dir,synth_filename))[0]
    #     print(synth_filename)
    try:
        tr_s = read(f_syn)[0]
        
    except:
        print('\nCould not read synthetics: '+os.path.basename(f))
        return [],success
        #i+=1
        #continue

    # Add essential metadata
    #tr_s.stats.sac = get_essential_sacmeta(tr_o.stats.sac)

    # Check sampling rates. 
    if round(tr_s.stats.sampling_rate,6) != round(tr_o.stats.sampling_rate,6):
        print("Sampling Rates (Hz)")
        print(tr_s.stats.sampling_rate)
        print(tr_o.stats.sampling_rate)
        msg = 'Sampling rates of data and synthetics must match.'
        raise ValueError(msg)

    # Waveforms must have same nr of samples.
    tr_s.data = my_centered(tr_s.data,tr_o.stats.npts)    
   
   
    # Get the adjoint source

    func = af.get_adj_func(m_params['mtype'])
    data, success = func(tr_o,tr_s,m_params)

    return data, success
            #if not success:
                #continue
            #else:
                # save


           
            #adj_src = Trace(data=data)

            

            #adj_src.stats.sampling_rate = tr_s.stats.sampling_rate
            #adj_src.stats.sac = tr_s.stats.sac.copy()
            # Save the adjoint source
            #file_adj_src = os.path.join(adj_dir,os.path.basename(synth_filename))
            #adj_src.write(file_adj_src,format='SAC')
            
           
              
            # step index
            #i+=1
    #




def run_adjointsrcs(source_configfile,measr_configfile,step,ignore_network):
    
    # config
    source_config=json.load(open(source_configfile))
    measr_config=json.load(open(measr_configfile))
    
    # directories
    step_n = 'step_{}'.format(int(step))
    synth_dir = os.path.join(source_config['source_path'],
    step_n,'corr')
    adj_dir = os.path.join(source_config['source_path'],
    step_n,'adjt')
    
    
    # measurement parameters of several measurements
    #measurements = []
    #for m in measr_config:
    #    m_params = {}
    #    m_params['mtype'] = m['mtype']

        # TODo all available misfits 
        #if mtype in ['ln_energy_ratio','energy_diff']:
        #    m_params['g_speed'] = measr_config['g_speed']
        #    m_params['hw'] = measr_config['window_params_hw']
        #    m_params['sep_noise'] = measr_config['window_params_sep_noise']
        #    m_params['win_overlap'] = measr_config['window_params_win_overlap']
        #    m_params['wtype'] = measr_config['window_params_wtype']
        #    m_params['causal_side'] = measr_config['window_params_causal']
        #    m_params['plot'] = False # To avoid plotting the same thing twice
            # ToDo think of a better solution here.
    
        # else:
        #     raise NotImplementedError('Measurement type not available.')

      #  measurements.append(m_params)
    

# ToDo: Why is this so ugly?
    files = [f for f in os.listdir(os.path.join(source_config['source_path'],
    'observed_correlations')) ]
    files = [os.path.join(source_config['source_path'],
    'observed_correlations',f) for f in files]
    
    if files == []:
        msg = 'No input found!'
        raise ValueError(msg)


    for f in files:

        synth_filename = get_synthetics_filename(os.path.basename(f),synth_dir,
            ignore_network=ignore_network)
        if synth_filename is None:
            continue
        #sname = glob(os.path.join(synth_dir,synth_filename))[0]
        
        adjt = []

        for m in measr_config:

            adjt_part, success = adjointsrcs(f,f_syn,m)
            if success:
                adjt.append(adjt_part)
            else:
                adjt.append(None)

        if None in adjt:
            continue

        else:
            adjt = np.array(adjt)

            fname = os.path.join(adj_dir,
                os.splitext(os.path.basename(synth_filename))[0],'.npy')
            np.save(fname,adjt)
    
        
        
        
