from decimal import Decimal
from typing import List, Tuple, Iterator, Dict
from urllib.request import urlopen
from enum import Enum

import json
import yaml

class OutputFormat(Enum):
    POLY = 1
    GPX = 2

class BorderSegment:
    def __init__(self, wayId:int, points: List[Tuple[Decimal, Decimal]]):
        self.wayId = wayId
        self.points = points

    def startsWith(self, point):
        return self.points[0] == point

    def endsWith(self, point):
        return self.points[-1] == point

    def reversed(self):
        return BorderSegment(self.wayId, list(reversed(self.points)))

def loadConfig(configPath: str):
    return yaml.full_load(open(configPath))

def loadCountryPolys(countryName:str, countryConf:Dict, outPath:str, outFormat:OutputFormat):
    print(f"Writing country '{countryName}':")
    for regionConf in countryConf:
        name = regionConf["name"]
        areasIds = regionConf["areasIds"]
        print(f"Writing region '{countryName} {name}' ...")
        closedLines = loadOsmCoordinates(areasIds)
        if outFormat == OutputFormat.POLY:
            writePoly(closedLines, f"{countryName}_{name}", f"{outPath}/{countryName}_{name}.poly")
        else:
            writeGPX(closedLines, f"{countryName}_{name}", f"{outPath}/{countryName}_{name}.gpx")

def loadOsmCoordinates(areasIds: List[int]) -> Iterator[Iterator[Tuple[Decimal, Decimal]]]:
    relAreas = [loadRelation(id) for id in areasIds]
    closedLines = mergeAreas(relAreas)
    for line in closedLines:
        yield unchainCoordinates(line)

def loadRelation(id: int) -> List[BorderSegment]:
    relationData = None
    print("  Loading OSM data ...")
    with urlopen(f"https://api.openstreetmap.org/api/0.6/relation/{id}/full.json") as conn:
        relationData = parseRelationJson(conn)
    print("  Parsing data ...")
    rel = next(iter(relationData["relation"].values()))
    waysIds = [way["ref"] for way in rel["members"] if way["type"] == "way"]
    segments = []
    for wayId in waysIds:
        wayData = relationData["way"][wayId]
        nodesIds = wayData["nodes"]
        coords = [ (relationData["node"][id]["lat"], relationData["node"][id]["lon"]) for id in nodesIds]
        segments.append(BorderSegment(wayId, coords))
    return segments

# Use Decimal type instead of float
def parse_json_float(float_str: str):
    return Decimal(float_str)

# Extract all relations, ways and nodes from JSON response
def parseRelationJson(stream):
    rawData = json.load(stream, parse_float=parse_json_float)
    objects = {"relation": dict(),
               "way": dict(),
               "node": dict()}
    for element in rawData["elements"]:
        elementType = element["type"]
        elementId = element["id"]
        objects[elementType][elementId] = element
    return objects

# Merge list of ways into closed polygons
def mergeAreas(areas: List[List[BorderSegment]]) -> Iterator[List[BorderSegment]]:
    #TODO: deduplicate areas
    segments = []
    for l in areas:
        segments += l
    print(f"  Total {len(segments)} segments to chain")
    chain = [segments[0]]
    del segments[0]
    while segments:
        firstChainPoint = chain[0].points[0]
        lastChainPoint = chain[-1].points[-1]

        if firstChainPoint == lastChainPoint:
            print(f"  Found chain of {len(chain)} segment(s)")
            yield chain
            chain = [segments[0]]
            del segments[0]
            continue

        for s in segments:
            if s.startsWith(lastChainPoint):
                chain.append(s)
                segments.remove(s)
                break
            elif s.endsWith(lastChainPoint):
                chain.append(s.reversed())
                segments.remove(s)
                break
        else:
            raise Exception(f"Can't continue chain. Can't find next way after #{chain[-1].wayId} among ways {', '.join(str(s.wayId) for s in segments)}")

    print(f"  Found chain of {len(chain)} segment(s)")
    yield chain

def unchainCoordinates(line: List[BorderSegment]) -> Iterator[Tuple[Decimal, Decimal]]:
    for seg in line:
        yield from seg.points

def writePoly(closedLines:Iterator[Iterator[Tuple[Decimal, Decimal]]], mapName:str, outFilename:str):
    with open(outFilename, "wt") as fout:
        fout.write(mapName + "\n")
        i = 1
        for coordinates in closedLines:
            fout.write(f"{i}\n")
            for lat,lon in coordinates:
                fout.write(f"\t{lon:.6E}\t{lat:.6E}\n")
            fout.write("END\n")
            i += 1
        fout.write("END\n")

def writeGPX(closedLines:Iterator[Iterator[Tuple[Decimal, Decimal]]], mapName:str, outFilename:str):
    with open(outFilename, "wt") as fout:
        fout.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.0"
     creator="BasicAirData GPS Logger 3.1.7"
     xmlns="http://www.topografix.com/GPX/1/0"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">
<name>GPS Logger 20221030-132554</name>
<desc>{mapName}</desc>
<time>2022-11-02T09:50:04Z</time>

<trk>
 <name>Track 1</name>
""")
        i = 1
        for coordinates in closedLines:
            fout.write(f" <trkseg>\n")
            for lat,lon in coordinates:
                fout.write(f'  <trkpt lat="{lat}" lon="{lon}"><ele>844.629</ele><time>2022-10-30T11:25:56Z</time><speed>0.000</speed><sat>11</sat></trkpt>\n')
            fout.write(" </trkseg>\n")
            i += 1
        fout.write("</trk>\n")

if __name__ == '__main__':
    config = loadConfig("data/osm-borders.yml")
    for countryName, countryConfig in config["countries"].items():
        loadCountryPolys(countryName, countryConfig, "data/poly", OutputFormat.POLY)
    print("Done!")
