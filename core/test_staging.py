
in_fc = '\\\\Mac\\stor\\Projects\\TransectExtraction\\Fisherman2014\\Fisherman2014.gdb\\extTrans'
sort_lines = os.path.join(arcpy.env.scratchGDB, 'sort_lines')
out_trans =  os.path.join(arcpy.env.workspace, 'extTrans_sorttest')
# Loop through sort_lines ordered by field 'sort'
# For each line, copy the transect FC and remove all transects that do not intersect the given sort line.
# Sort the subsetted transects.
# Append each one to the


def SelectivelyDeleteFeatures(targetFC, selectionFC):
    for row in arcpy.da.SearchCursor(selectionFC, ['SHAPE@']):
        geom = row[0]
        with arcpy.da.UpdateCursor(targetFC, ['SHAPE@']) as cursor:
            for trow in cursor:
                tgeom = trow[0]
                if tgeom.disjoint(geom):
                    cursor.deleteRow()
    return(targetFC)


# Doesn't work... yet.
for row in dist_df.itertuples():
    if abs(dist_df[row[0]-1] - row[1]) > 300:
        print("CAUTION: Large change in Dist2Inlet values between transects {} and {}".format(row[0]-1, row[0]))
