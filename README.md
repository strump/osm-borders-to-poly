# Description
Script to generate .POLY/.GPX files from OSM multipolygon relations.

# Usage

1. Modify `data/osm-borders.yml` config file. Add countries with regions:
2. Run script

    python osm-borders-to-poly.py

Output will be generated into `data/poly` folder.

# Data format

Main config file `data/osm-borders.yml` contains list of countries with regions. Each region is defined by a set of OSM IDs.

# How OSM relations are handled

`osm-borders-to-poly` expects that each OSM relation is a multipolygon. It downloads multipolygon data and glues it to a number or closed lines.


       *---[ Way 1 ]--*            --[Way 5]--
       |              |           /           \
       |              |          /             \
    [Way 3]        [Way 6]      *               *
       |              |          \             /
       |              |           \           /
       *---[ Way 4 ]--*            --[Way 2]--


Imaging we have relation of 6 ways. And we need to extract 2 closed lines of it. First we need to extract all ways (instances `BoardSegment` class). And after that merge ways which have common points. Function `mergeAreas` is responsible for that. It builds a chain of ways where each next way starts where previous way ends.
And because multipolygon in OSM could have more than one closed line, function `mergeAreas` returns list of such chains:

* Chain 1: `Way 1`, `Way 6`, `Way 4`, `Way 3`
* Chain 2: `Way 5`, `Way 2`

And the final step is to export points from those chains of ways into a single POLY/GPX file.
