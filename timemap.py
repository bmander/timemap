from datetime import datetime, timedelta
import time
import pyproj
from prender import processing

INFINITY = 1000000000000
HOUR_INDEX = 3

def cons(ary):
    for i in range(len(ary)-1):
        yield ary[i], ary[i+1]

class NMEAParser(object):
    @classmethod
    def parse(klass, filename):
        fp = open( filename )
        for sentance in fp:
            split_sentance = sentance.split(",")
            format = split_sentance[0]
            if format == "$GPRMC":
                yield GPRMC(split_sentance)
            elif format == "$GPGGA":
                yield GPGGA(split_sentance)
    
class GPRMC(object):
    
    def __init__(self, split_sentance, utc_offset=-8):
        if utc_offset>0:
            raise Exception( "This has never been tested in an area with a positive UTC. Wierd things will probably happen." )
        
        if len(split_sentance)==0 or split_sentance[0] != "$GPRMC":
            raise ValueError( "String does not begin with '$GPRMC', so it probably isn't a GPRMC sentence" )
                
        (self.format,
         self.utc,
         self.activeness,
         self.latitude, 
         self.northsouth, 
         self.longitude, 
         self.eastwest, 
         self.speed, 
         self.bearing, 
         self.date, 
         self.altitude, 
         self.magnetic_variation, 
         self.checksum) = split_sentance
         
        latitude_in=float(self.latitude)
        longitude_in=float(self.longitude)
        if self.northsouth == 'S':
            latitude_in = -latitude_in
        if self.eastwest == 'W':
            longitude_in = -longitude_in

        latitude_degrees = int(latitude_in/100)
        latitude_minutes = latitude_in - latitude_degrees*100
        
        longitude_degrees = int(longitude_in/100)
        longitude_minutes = longitude_in - longitude_degrees*100
        
        self.latitude = latitude_degrees + (latitude_minutes/60)
        self.longitude = longitude_degrees + (longitude_minutes/60)
        
        self.timeOfFix = datetime.strptime(self.utc.split(".")[0]+self.date,"%H%M%S%d%m%y")
        
        if self.timeOfFix.hour < abs(utc_offset):
            self.timeOfFix = self.timeOfFix + timedelta(days=0,seconds=3600*24)
            
        self.timestampOfFix = time.mktime( self.timeOfFix.timetuple() )
        
        self.altitude = float(self.altitude) if self.altitude else None
            
    def __repr__(self):
        if not hasattr(self, 'latitude') or not hasattr(self, 'longitude'):
            return "blank"
        
        return "GPRMC(%s, %s, %s)"%(self.longitude, self.latitude, self.timeOfFix)

class GPGGA(object):
    
    def __init__(self, split_sentance):
        
        if len(split_sentance)==0 or split_sentance[0] != "$GPGGA":
            raise ValueError( "String does not begin with '$GPGGA', so it probably isn't a GPGGA sentence" )
        
        (self.format,
         self.utc,
         self.latitude, 
         self.northsouth, 
         self.longitude, 
         self.eastwest, 
         self.quality, 
         self.number_of_satellites_in_use, 
         self.horizontal_dilution, 
         self.altitude, 
         self.above_sea_unit, 
         self.geoidal_separation, 
         self.geoidal_separation_unit, 
         self.data_age, 
         self.diff_ref_stationID) = split_sentance

        latitude_in=float(self.latitude)
        longitude_in=float(self.longitude)
        if self.northsouth == 'S':
            latitude_in = -latitude_in
        if self.eastwest == 'W':
            longitude_in = -longitude_in

        latitude_degrees = int(latitude_in/100)
        latitude_minutes = latitude_in - latitude_degrees*100
        
        longitude_degrees = int(longitude_in/100)
        longitude_minutes = longitude_in - longitude_degrees*100
        
        self.latitude = latitude_degrees + (latitude_minutes/60)
        self.longitude = longitude_degrees + (longitude_minutes/60)
        
        self.timeOfFix = time.strptime(self.utc.split(".")[0],"%H%M%S")
        self.altitude = float(self.altitude) if self.altitude else None
        
    def __repr__(self):
        if not hasattr(self, 'latitude') or not hasattr(self, 'longitude'):
            return "blank"
        
        return "GPGGA(%s, %s, %s)"%(self.longitude, self.latitude, self.utc)

def main(draw_waits=False,circlesize=100,circleoutline=4,speedthickness=8):
    p1 = pyproj.Proj(init='epsg:32148')
    
    ll, bb, rr, tt = INFINITY, INFINITY, -INFINITY, -INFINITY
    
    pointstrings = []
    for filename, color in [
                            #("/home/brandon/gps/2010-02-15/00001_20100213.nmea",(0,0,0)),
                            #("/home/brandon/gps/2010-02-15/00002_20100213.nmea",(0,0,0)),
                            ("/home/brandon/gps/2010-02-15/00003_20100214.nmea",(0,0,0)),
                            ("/home/brandon/gps/2010-02-15/00004_20100214.nmea",(0,0,0)),
                            #("/home/brandon/gps/2010-02-15/00005_20100215_part.nmea",(200,200,200)) \
                           ]:
        points = []
        for record in NMEAParser.parse( filename ):
            if record.__class__==GPRMC:
                x1, y1 = p1(record.longitude, record.latitude)
                t1 = record.timestampOfFix
                
                #print x1, y1, record.timestampOfFix
                
                ll = min(ll,x1)
                bb = min(bb,y1)
                rr = max(rr,x1)
                tt = max(tt,y1)
                
                points.append( (x1, y1, t1) )
        pointstrings.append( (points, color) )
            
    print ll, bb, rr, tt
        

    mr = processing.MapRenderer()
    mr.start(ll,bb,rr,tt,2000) #left,bottom,right,top,width
    mr.background(255,255,255)
    mr.smooth()
    mr.strokeWeight(1)
    mr.fill(255,255,255,0)
    
    waitstart = None
    for points, color in pointstrings:
        mr.stroke(*color)
        
        for (x1,y1,t1),(x2,y2,t2) in cons(points):
            
            speed = ((y2-y1)**2+(x2-x1)**2)**0.5/(t2-t1)
            
            mr.strokeWeight( speedthickness*speed )
            mr.line(x1,y1,x2,y2) #from lower-lefthand to upper-righthand
        
    
    mr.stroke(0,0,0)
    if draw_waits:
        mr.strokeWeight( circleoutline )
        mr.fill( 255,0,0,64 )
        
        for points, color in pointstrings:
            for (x1,y1,t1),(x2,y2,t2) in cons(points):
                
                speed = ((y2-y1)**2+(x2-x1)**2)**0.5/(t2-t1)
                
                if speed<1.5 and waitstart==None:
                    waitstart = t1
                    
                if speed>=1.5 and waitstart!=None:
                    wait = t2-waitstart
                    
                    # make a circle
                    if wait>=0:
                        print "waited for %s at %s"%(wait, t2)
                        circlediameter = circlesize*((wait)**0.5)
                        
                        mr.ellipse(x1, y1, circlediameter, circlediameter)
                    
                    waitstart = None
            
        
    mr.saveLocal("map.png")
    mr.stop()
    
if __name__=='__main__':
    main(draw_waits=True,circlesize=5,circleoutline=1,speedthickness=0.5)
