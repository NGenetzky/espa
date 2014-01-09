
'''
License:
  "NASA Open Source Agreement 1.3"

Description:
  Utility module for ESPA project.
  This is a shared module to hold simple utility functions.

History:
  Original implementation by David V. Hill, USGS/EROS
  Updated Jan/2014 by Ron Dilley, USGS/EROS
'''

import datetime
import calendar
import subprocess

from frange import frange


def stripZeros(value):
    '''
    Description:
      Removes all leading zeros from a string
    '''

    while value.startswith('0'):
        value = value[1:len(value)]
    return value


def getPath(scene_name):
    '''
    Description:
      Returns the path of a given scene
    '''
    return stripZeros(scene_name[3:6])


def getRow(scene_name):
    '''
    Description:
      Returns the row of a given scene
    '''
    return stripZeros(scene_name[6:9])


def getYear(scene_name):
    '''
    Description:
      Returns the year of a given scene
    '''
    return scene_name[9:13]


def getDoy(scene_name):
    '''
    Description:
      Returns the day of year for a given scene
    '''
    return scene_name[13:16]


def getSensor(scene_name):
    '''
    Description:
      Returns the sensor of a given scene
    '''

    if scene_name[0:3].lower() =='lt5' or scene_name[0:3].lower() == 'lt4':
        # Landsat TM
        return 'LT'
    elif scene_name[0:3].lower() == 'le7':
        # Landsat ETM+
        return 'LE'
    elif scene_name[0:3].lower() == 'mod':
        # MODIS Terra
        return 'MOD'
    elif scene_name[0:3].lower() == 'myd':
        # MODIS Aqua
        return 'MYD'
    return ''


def getSensorCode(scene_name):
    '''
    Description:
      Returns the raw sensor code of a given scene
    '''
    return scene_name[0:3]


def getStation(scene_name):
    '''
    Description:
      Returns the ground stations and version for a given scene
    '''
    return scene_name[16:21]


def getModisShortName(scene_name):
    '''
    Description:
      Returns the MODIS short name portion of the scene
    '''
    return scene_name.split('.')[0]


def getModisVersion(scene_name):
    '''
    Description:
      Returns the MODIS version portion of the scene
    '''
    return scene_name.split('.')[3]


def getModisHorizontalVertical(scene_name):
    '''
    Description:
      Returns the MODIS horizontal and vertical specifiers of the scene
    '''

    element =  scene_name.split('.')[2]
    return (element[0:3], element[3:])


def getModisSceneDate(scene_name):
    '''
    Description:
      Returns the MODIS scene data portion of the scene
    '''

    date_element = scene_name.split('.')[4]
    # Return the (year, doy)
    return (date_element[0:4], date_element[4:7])


def getModisArchiveDate(scene_name):
    '''
    Description:
      Returns the MODIS archive date portion of the scene
    '''
    date_element = scene_name.split('.')[1]

    year = date_element[1:5]
    doy = date_element[5:]

    # Convert DOY to month and day
    month = 1
    day = int(doy)
    while month < 13:
        month_days = calendar.monthrange(int(year), month)[1]
        if day <= month_days:
            return '%s.%s.%s' % (year.zfill(4), str(month).zfill(2),
                                 str(day).zfill(2))
        day -= month_days
        month += 1

    raise ValueError("Year %s does not have %s days" % (year, doy))


def getPoints(startX, stopX, startY, stopY, step):
    '''
    Description:
      Generates a list of points that lie within the specified bounding box at
      the given step (float)
    '''
    
    retVal = []
    for x in frange(startY, stopY, step):
        for y in frange(startX, stopX, step):
            retVal.append(("%f,%f") % (round(x,6), round(y,6)))
    retVal.append(("%f,%f") % (round(startY,6), round(startX,6)))
    retVal.append(("%f,%f") % (round(stopY,6), round(stopX,6)))
    return retVal


def buildMatrix(yx1, yx2, yx3, yx4):
    '''
    Description:
      Builds a matrix of points that lie within yx1, yx2, yx3, and yx4 where
      yxN is a latitude,longitude pair
    '''
    
    y1,x1 = yx1.split(',')
    y2,x2 = yx2.split(',')
    y3,x3 = yx3.split(',')
    y4,x4 = yx4.split(',')
    
    xlist = [float(x1),float(x2),float(x3),float(x4)]
    ylist = [float(y1),float(y2),float(y3),float(y4)]
    xmin = min(xlist)
    xmax = max(xlist)
    ymin = min(ylist)
    ymax = max(ylist)

    # The last value determines how many points will be created for the matrix.
    # For a typical landsat scene .05 (of latitude/longitude) gives us about
    # 1700 points per scene.  If it's not sufficient make this a smaller number
    # and rebuild the index
    result = getPoints(xmin, xmax, ymin, ymax, 0.05)
    return result

