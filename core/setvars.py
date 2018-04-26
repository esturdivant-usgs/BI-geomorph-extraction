'''
Configuration file for DeepDive Transect Extraction (CoastalVarExtractor module)
Author: Emily Sturdivant
email: esturdivant@usgs.gov;

Designed to be imported by either prepper.ipynb or extractor.py.
'''
import os
import sys
import arcpy
import getpass
from core.configmap import *
import core.functions_warcpy as fwa

############ Inputs #########################
# site = 'Fisherman'
# year = '2014'
# proj_dir = r'\\Mac\volume\dir\{}'.format(site+year)

try:
    site = input("site (options: {}): ".format(', '.join(sitemap.keys())))
    year = input("year (options: 2010, 2012, 2014): ")
    # proj_dir = input("Path to project directory (e.g. \\\Mac\volume\dir\FireIsland2014): ")
    proj_dir = getpass.getpass("Path to project directory (e.g. \\\Mac\volume\dir\FireIsland2014): ")
    if not os.path.isdir(proj_dir):
        proj_dir = getpass.getpass("Invalid pathname. Try again: ")
    if not os.path.isdir(proj_dir):
        sys.exit("'{}' not recognized as folder. Operation cancelled so you can get the project folder squared away.".format(proj_dir))
except:
    if len(proj_dir) < 1:
        print("Looks like we can't prompt for user input so you'll need to manually enter values into the module.")
        raise

# get values from sitemap in configmap.py
sitevals = sitemap[site]
yabbr = str(year)[2:4]
home = os.path.join(proj_dir, '{}{}.gdb'.format(sitevals['site'], year))
scratch_dir = os.path.join(proj_dir, 'scratch')
if not os.path.exists(scratch_dir):
    os.makedirs(scratch_dir)

######## Set-up environments ###############################################
arcpy.env.workspace = home
arcpy.env.scratchWorkspace = proj_dir
arcpy.env.overwriteOutput = True 						# Overwrite output?
arcpy.CheckOutExtension("Spatial") 						# Checkout Spatial Analysis extension

########### Default Values ##########################
if sitevals['region'] == 'Massachusetts' or sitevals['region'] == 'RhodeIsland' or sitevals['region'] == 'Maine':
    proj_code = 26919 # "NAD 1983 UTM Zone 19N"
else:
    proj_code = 26918 # "NAD 1983 UTM Zone 18N"
# Spatial references
nad83 = arcpy.SpatialReference(4269)
utmSR = arcpy.SpatialReference(proj_code)

if sitevals['site'] == 'Monomoy':
    maxDH = 3
else:
    maxDH = 2.5

sitevals['MTL'] = MTL = (sitevals['MHW'] + sitevals['MLW'])/2

############## Output filenames/paths ###############################
# OUTPUTS
trans_name = '{}{}_trans'.format(sitevals['code'], yabbr)
pts_name = '{}{}_pts'.format(sitevals['code'], yabbr)
rst_transID = os.path.join(home, "{}_rstTransID".format(sitevals['site']))
bw_rst="{}{}_ubw".format(sitevals['code'], yabbr)
pts_presort = os.path.join(arcpy.env.scratchGDB, 'transPts_unsorted')

if not __name__ == '__main__':
    print("setvars.py initialized variables.")
    print("SITE: {site}\nMHW: {MHW}\nMLW: {MLW}".format(**sitevals))
    print("Max dune crest height: {}\nProjection code: {}\n".format(maxDH, proj_code))
