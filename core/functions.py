# Transect Extraction module
# possible categories: preprocess, create, calculate

import time
import os
import collections
import pandas as pd
import numpy as np
from operator import add
import matplotlib.pyplot as plt
import matplotlib
matplotlib.style.use('ggplot')

def print_duration(start, suppress=False):
    duration = time.clock() - start
    hours, remainder = divmod(duration, 3600)
    minutes, seconds = divmod(remainder, 60)
    duration_str = '{:.0f}:{:.0f}:{:.1f} seconds'.format(hours, minutes, seconds)
    if not suppress:
        print('Duration: {}'.format(duration_str))
        return
    return(duration_str)

def newcoord(coords, dist):
    # From: gis.stackexchange.com/questions/71645/extending-line-by-specified-distance-in-arcgis-for-desktop
    # Computes new coordinates x3,y3 at a specified distance along the
    # prolongation of the line from x1,y1 to x2,y2
    (x1,y1),(x2,y2) = coords
    dx = x2 - x1 # change in x
    dy = y2 - y1 # change in y
    linelen =np.hypot(dx, dy) # distance between xy1 and xy2
    x3 = x2 + dx/linelen * dist
    y3 = y2 + dy/linelen * dist
    return x3, y3

def check_id_fld(df, id_fld, fill=-99999):
    # determine whether index or id_fld is the correct index field; make index the correct index field with the correct name
    # compare index to id_fld
    # check whether nulls or duplicated exist in ID field
    bad_idx = any([df.index.duplicated().any(), df.index.isnull().any(), any(df.index==fill)])
    if id_fld in df.columns:
        # Evaluate df.id_fld:
        bad_id_col = any([df.duplicated(id_fld).any(), df[id_fld].isnull().values.any(), any(df[id_fld]==fill)])
        if bad_id_col and bad_idx:
            raise IndexError('There are errors in both the index and the identified ID column.')
        elif bad_id_col and not bad_idx:
            if not df.index.name == id_fld:
                raise IndexError("There are errors in the identified ID column, but not in the index. However, we can't be sure that the index is correct because the name does not match the ID.")
        elif not bad_id_col and bad_idx:
            df.index = df[id_fld]
        elif not bad_id_col and not bad_idx:
            if (df.index == df[id_fld]).all(): # if the index is already equal to the id_fld
                df.index.name = id_fld
            else:
                print('Neither index nor designated ID column have errors, but they are not equal. We will assume that the ID column is correct and convert it to the index.')
                df.index = df[id_fld]
        else:
            print('Unforeseen situation. Check the code.')
        df.drop(id_fld, axis=1, inplace=True)
    elif bad_idx:
        raise IndexError('There are errors in the index and the identified ID column does not exist.')
    else:
        df.index.name = id_fld
    return(df)

def join_columns_id_check(df1, df2, id_fld='ID', how='outer', fill=-99999):
    # If both DFs should be joined on index field, must remove duplicate names
    # If one should be joined on index and the other not, must remove one of the
    if not 'SplitSort' in df1.columns:
        df1 = check_id_fld(df1, id_fld)
    df2 = check_id_fld(df2, id_fld)
    df1 = df1.drop(df1.axes[1].intersection(df2.axes[1]), axis=1, errors='ignore') # remove matching columns from target dataframe
    df1 = df1.join(df2, how=how)
    return(df1)

def join_columns(df1, df2, id_fld='ID', how='outer'):
    # If both DFs should be joined on index field, must remove duplicate names
    # If one should be joined on index and the other not, must remove one of the
    if id_fld in df2.columns:
        if not df2.index.name == id_fld and not df2.duplicated(id_fld).any(): # if the ID field has already become the index, delete the ID field.
            df2.index = df2[id_fld] # set id_fld to index of join dataframe
        # elif df2.index.duplicated().any():
    df2.drop(id_fld, axis=1, inplace=True, errors='ignore') # remove id_fld from join dataframe
    df1 = df1.drop(df1.axes[1].intersection(df2.axes[1]), axis=1, errors='ignore') # remove matching columns from target dataframe
    if not id_fld in df2.columns:
        if id_fld in df1.columns:
            df1 = df1.join(df2, on=id_fld, how=how) # join df2 to df1
        elif not id_fld in df1.columns:
            df1 = df1.join(df2, how=how)
    else:
        raise IndexError("ID field '{}' is still a column in join DF.")
    return(df1)

def adjust2mhw(df, MHW, fldlist=['DH_z', 'DL_z', 'Arm_z'], fill=-99999):
    # Add elevation fields with values adjusted to MHW, stored in '[fieldname]mhw'
    # If fill values present in df, replace with nan to perform adjustment and then replace
    if (df == fill).any().any():
        input_fill = True
        df.replace(fill, np.nan, inplace=True)
    for f in fldlist:
        df = df.drop(f+'mhw', axis=1, errors='ignore')
        df[f+'mhw'] = df[f].subtract(MHW)
    if input_fill:
        df.fillna(fill, inplace=True)
    return(df)

def sort_pts(df, tID_fld='sort_ID', pID_fld='SplitSort'):
    # Calculate pt distance from shore; use that to sort pts and create pID_fld
    # 1. set X and Y fields
    if 'SHAPE@X' in df.columns:
        df.drop(['seg_x', 'seg_y'], axis=1, inplace=True, errors='ignore')
        df.rename(index=str, columns={'SHAPE@X':'seg_x', 'SHAPE@Y':'seg_y'}, inplace=True)
    # 2. calculate pt distance to MHW
    df.reset_index(drop=True, inplace=True)
    dist_seg = np.hypot(df.seg_x - df.SL_x, df.seg_y - df.SL_y)
    df = join_columns(df, pd.DataFrame({'Dist_Seg': dist_seg}, index=df.index))
    # 3. Sort and create pID_fld (SplitSort)
    df = df.sort_values(by=[tID_fld, 'Dist_Seg']).reset_index(drop=True)
    df.index.rename(pID_fld, inplace=True)
    try:
        df.reset_index(drop=False, inplace=True) # ValueError: cannot insert SplitSort, already exists
    except ValueError:
        df.drop(pID_fld, axis=1, errors='ignore', inplace=True)
        df.reset_index(drop=False, inplace=True)
        print("{} already existed in dataframe, but it was replaced.".format(pID_fld))
        pass
    return(df)

def calc_trans_distances(df, MHW=''):
    df2 = pd.DataFrame({'DistDH': np.hypot(df.SL_x - df.DH_x, df.SL_y - df.DH_y),
                        'DistDL': np.hypot(df.SL_x - df.DL_x, df.SL_y - df.DL_y),
                        'DistArm': np.hypot(df.SL_x - df.Arm_x, df.SL_y - df.Arm_y)},
                        index=df.index)
    df = join_columns(df, df2)
    if len(MHW):
        df = adjust2mhw(df, MHW)
    return(df)

def calc_pt_distances(df):
    df2 = pd.DataFrame({'DistSegDH': df.Dist_Seg - df.DistDH,
                        'DistSegDL': df.Dist_Seg - df.DistDL,
                        'DistSegArm': df.Dist_Seg - df.DistArm,
                        'Dist_MHWbay': df.WidthPart - df.Dist_Seg
                        }, index=df.index)
    df = join_columns(df, df2)
    return(df)

def prep_points(df, tID_fld, pID_fld, MHW, fill=-99999, old2newflds={}):
    # Preprocess transect points (after running FCtoDF(transPts, xy=True))
    # Replace fills with NaNs
    df.replace(fill, np.nan, inplace=True)
    # Rename columns
    if len(old2newflds):
        df.rename(index=str, columns=old2newflds, inplace=True)
    # Calculate pt distance from shore; use that to sort pts and create pID_fld (SplitSort)
    df = sort_pts(df, tID_fld, pID_fld)
    # Calculate pt distance from dunes and bayside shore
    # df = adjust2mhw(df, MHW)
    df = calc_trans_distances(df)
    df = calc_pt_distances(df)
    return(df)

def aggregate_z(df, MHW, id_fld, zfld, fill):
    # Aggregate ptZmhw to max and mean and join to transects
    input_fill=False
    if (df == fill).any().any():
        input_fill = True
        df.replace(fill, np.nan, inplace=True)
    df = (df.drop(zfld+'mhw', axis=1, errors='ignore')
            .join(df[zfld].subtract(MHW), rsuffix='mhw'))
    # get mean only if > 80% of points have elevation
    meanf = lambda x: x.mean() if float(x.count())/x.size > 0.8 else np.nan
    # zmhw = df.groupby(id_fld)[zfld+'mhw'].agg({'mean_Zmhw':meanf,
    #                                            'max_Zmhw':np.max})
    zmhw = df.groupby(id_fld)[zfld+'mhw'].agg([meanf,max]).rename(columns={'<lambda>':'mean_Zmhw','max':'max_Zmhw'})
    df = join_columns(df, zmhw, id_fld)
    if input_fill:
        df.fillna(fill, inplace=True)
    return(df, zmhw)

def get_beachplot_values(pts_set):
    tran = pts_set.iloc[0]

    # Get maximum Z values
    idmaxz = pts_set['ptZmhw'].idxmax()
    maxz = pts_set['ptZmhw'].loc[idmaxz]
    mz_xy = pts_set[['seg_x', 'seg_y']].loc[idmaxz]
    mz_dist = np.hypot(mz_xy.seg_x - tran.SL_x, mz_xy.seg_y- tran.SL_y)

    # Get beach end and beach top
    if not np.isnan(tran.DistDH):
        bend = tran.DistDH
        btop = tran.DH_z
    elif not np.isnan(mz_dist):
        bend = mz_dist
        btop = maxz
    else:
        bend = 200
        btop = 4

    # Return
    return(tran, idmaxz, maxz, mz_xy, mz_dist, bend, btop)

def plot_island_profile(ax, pts_set, MHW, MTL):
    # Get prep values
    tran, idmaxz, maxz, mz_xy, mz_dist, bend, btop = get_beachplot_values(pts_set)
    maxz = maxz+MHW
    btop = btop+MHW

    # Axes limits
    xllim = -tran.WidthFull*0.038
    xulim = tran.WidthFull + tran.WidthFull*0.038
    yllim = MTL-0.2
    yulim = maxz++1.25

    # Subplot Labels
    ax.set_xlabel('Distance from shore (m)', fontsize = 12)
    ax.set_ylabel('Elevation (m)', fontsize = 12)
    ax.set_title('Island cross-section, transect {:.0f}'.format(tran.sort_ID))

    # Plot line
    # ax.plot(pts_set['Dist_Seg'], pts_set['ptZmhw']+MHW, color='gray', linestyle='-', linewidth = 1)
    ax.fill_between(pts_set['Dist_Seg'], pts_set['ptZmhw']+MHW, y2=yllim, facecolor='grey', alpha=0.5)
    plt.annotate('Elevation', xy=(tran.WidthFull-50, float(pts_set['ptZmhw'].tail(1))+0.6), color='gray')
    ax.axvspan(xmin=pts_set['Dist_Seg'].max(), xmax=xulim, color='grey', alpha=0.1)
    plt.annotate('ELEVATION UNKNOWN', xy=(np.mean([pts_set['Dist_Seg'].max(), tran.WidthFull]), np.mean([maxz, MTL])), color='gray')

    # #Island widths
    plt.plot([0, tran.WidthPart],[MHW+0.2, MHW+0.2], color='green', linestyle='-', linewidth = 2, alpha=0.5)
    plt.annotate('WidthPart: {:.1f}'.format(tran.WidthPart), xy=(tran.WidthFull*0.83, MHW+0.24), color='green')
    plt.plot([0, tran.WidthFull],[MHW+0.06, MHW+0.06], color='green', linestyle='-', linewidth = 2, alpha=0.5)
    plt.annotate('WidthFull: {:.1f}'.format(tran.WidthFull), xy=(tran.WidthFull*0.83, MHW-0.12), color='green')

    # #Beach points
    plt.scatter(tran.DistDL, tran.DL_z, color='orange')
    plt.scatter(tran.DistDH, tran.DH_z, color='red')
    plt.scatter(tran.DistArm, tran.Arm_z, color='black')

    # #Upper beach width and height
    plt.plot([MHW, tran.uBW],[MHW, MHW], color='orange', linestyle='-', linewidth = 1.5)
    plt.plot([tran.uBW, tran.uBW],[MHW, MHW + tran.uBH], color='orange', linestyle='-', linewidth = 1.5, marker='|')

    # #ax.axis('scaled')
    ax.set_xlim([xllim, xulim])
    ax.set_ylim([yllim, yulim])
    # ax.axhline(y=MTL, ls='dotted', color='black')
    ax.axhspan(ymin=-0.5, ymax=MTL, xmin=xllim, xmax=xulim, alpha=0.2, color='blue')
    plt.annotate('MTL', xy=(-tran.WidthFull*0.02, MTL-0.15), color='blue')
    # ax.axhline(y=MHW, ls='dotted', color='black')
    ax.axhspan(ymin=-0.5, ymax=MHW, xmin=xllim, xmax=xulim, alpha=0.2, color='blue')
    plt.annotate('MHW', xy=(-tran.WidthFull*0.02, MHW-0.15), color='blue', alpha=0.7)

def plot_beach_profile(ax, pts_set, MHW, MTL, maxDH):
    # Get prep values
    tran, idmaxz, maxz, mz_xy, mz_dist, bend, btop = get_beachplot_values(pts_set)
    maxz = maxz+MHW
    btop = btop+MHW
    maxDH = maxDH+MHW

    # Axes limits
    xllim = -5
    xulim = bend+bend*0.11
    yllim = MTL-0.2
    yulim = maxz+0.25 if maxz > maxDH else maxDH

    # Subplot Labels
    ax.set_xlabel('Distance from seaward MHW (m)', fontsize = 12)
    ax.set_ylabel('Elevation (m NAVD88)', fontsize = 12)
    ax.set_title('Beach cross-section, transect {:.0f}'.format(tran.sort_ID))

    # Plot line
    # ax.plot(pts_set['Dist_Seg'], pts_set['ptZmhw']+MHW, color='gray', linestyle='-', linewidth = 1, marker='.')
    ax.fill_between(pts_set['Dist_Seg'], pts_set['ptZmhw']+MHW, y2=yllim, facecolor='grey', alpha=0.5)
    plt.annotate('Elevation', xy=(bend+bend*0.025, btop), color='gray')

    # Beach points
    plt.scatter(tran.DistDL, tran.DL_z, s=80, color='orange')
    plt.annotate('dlo', xy=(tran.DistDL-tran.DistDL*0.05, tran.DL_z+tran.DL_z*0.08), color='orange')
    plt.scatter(tran.DistDH, tran.DH_z, s=80, color='red')
    plt.annotate('dhi', xy=(tran.DistDH-bend*0.02, tran.DH_z+btop*0.03), color='red')
    plt.scatter(tran.DistArm, tran.Arm_z, s=80, color='black')
    plt.annotate('armor', xy=(tran.DistArm-20, tran.Arm_z+0.5), color='black')

    # Upper beach width and height
    uBW = tran.uBW
    uBH = tran.uBH
    plt.plot([MHW, uBW],[MHW, MHW], color='orange', linestyle='-', linewidth = 1.5)
    plt.annotate('uBW: {:.1f}'.format(uBW), xy=(uBW*0.83, MHW+0.05), color='orange')
    plt.plot([uBW, uBW],[MHW, MHW + uBH], color='orange', linestyle='-', linewidth = 1.5, marker='|')
    plt.annotate('uBH: {:.1f}'.format(uBH), xy=(uBW+bend*0.03, MHW + uBH*0.5), color='orange')

    # Axis/context
    ax.set_xlim([-5, bend+bend*0.11])
    ax.set_ylim([yllim, yulim])
    ax.minorticks_on()
    ax.axhspan(ymin=-0.5, ymax=MTL, xmin=xllim, xmax=xulim, alpha=0.2, color='blue')
    plt.annotate('MTL', xy=(-4, MTL-0.12), color='blue')
    ax.axhspan(ymin=-0.5, ymax=MHW, xmin=xllim, xmax=xulim, alpha=0.2, color='blue')
    plt.annotate('MHW', xy=(-4, MHW-0.12), color='blue', alpha=0.7)
    ax.axhline(y=maxDH, ls='dotted', color='black')
    plt.annotate('maxDH', xy=(5, maxDH), xytext=(-4, maxDH-0.12), color='black')
