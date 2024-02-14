import googlemaps
from datetime import datetime
from PyQt5.QtCore import QVariant




def decode(point_str):
    '''Decodes a polyline that has been encoded using Google's algorithm
    http://code.google.com/apis/maps/documentation/polylinealgorithm.html

    This is a generic method that returns a list of (latitude, longitude)
    tuples.

    :param point_str: Encoded polyline string.
    :type point_str: string
    :returns: List of 2-tuples where each tuple is (latitude, longitude)
    :rtype: list

    '''

    # sone coordinate offset is represented by 4 to 5 binary chunks
    coord_chunks = [[]]
    for char in point_str:

        # convert each character to decimal from ascii
        value = ord(char) - 63

        # values that have a chunk following have an extra 1 on the left
        split_after = not (value & 0x20)
        value &= 0x1F

        coord_chunks[-1].append(value)

        if split_after:
            coord_chunks.append([])

    del coord_chunks[-1]

    coords = []

    for coord_chunk in coord_chunks:
        coord = 0

        for i, chunk in enumerate(coord_chunk):
            coord |= chunk << (i * 5)

            # there is a 1 on the right if the coord is negative
        if coord & 0x1:
            coord = ~coord  # invert
        coord >>= 1
        coord /= 100000.0

        coords.append(coord)

    # convert the 1 dimensional list to a 2 dimensional list and offsets to
    # actual values
    points = []
    prev_x = 0
    prev_y = 0
    for i in range(0, len(coords) - 1, 2):
        if coords[i] == 0 and coords[i + 1] == 0:
            continue

        prev_x += coords[i + 1]
        prev_y += coords[i]
        # a round to 6 digits ensures that the floats are the same as when
        # they were encoded
        points.append((round(prev_x, 6), round(prev_y, 6)))

    print(points)
    return points

class PlotRoutes:
    def __init__(self):
        self.gmaps = googlemaps.Client("AIzaSyCvJVZR8eK-yi8HDVfcF2VSD9xrYRDzczg")

    def get_qgs_feature_from_directions(self, from_address, to_address, mode, departure_time):
        directions_result = self.gmaps.directions(from_address, to_address, mode=mode,
                                                  departure_time=departure_time)
        point_str = str(directions_result[0]["overview_polyline"]["points"])
        points = decode(point_str)

        fet = QgsFeature()
        seg = []
        for i in range(0, len(points)):
            seg.append(QgsPoint(points[i][0], points[i][1]))

        fet.setGeometry(QgsGeometry.fromPolyline(seg))
        fet.setAttributes(["route provided by google maps api"])

        return fet

    def get_addresses_from_file(self, path):
        # TODO import from csv

    def plot_routes_from_file(self, path, mode, departure_time):
        addresses = self.get_addresses_from_file(path)
        for address in addresses:
            fet = get_qgs_feature_from_directions(address[0], address[1], mode, departure_time)

# TODO maybe use a more specific time
departure_time = datetime.now()



layer = QgsVectorLayer('LineStringZ', 'route', "memory")
pr = layer.dataProvider()
pr.addAttributes([QgsField("attribution", QVariant.String)])
layer.updateFields()

pr.addFeatures([fet])
layer.updateExtents()  # update it
QgsProject.instance().addMapLayer(layer)

def main():
    plot_routes = PlotRoutes()


if __name__ == "__main__":
    main()