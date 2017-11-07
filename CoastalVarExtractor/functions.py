# Transect Extraction module
# possible categories: preprocess, create, calculate

import time
import os
import collections
import pandas as pd
import numpy as np
from operator import add

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
    df2 = pd.DataFrame({'DistSegDH': np.hypot(df.seg_x - df.DH_x, df.seg_y - df.DH_y),
                        'DistSegDL': np.hypot(df.seg_x - df.DL_x, df.seg_y - df.DL_y),
                        'DistSegArm': np.hypot(df.seg_x - df.Arm_x, df.seg_y - df.Arm_y),
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
    df = calc_pt_distances(df)
    df = calc_trans_distances(df)
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
