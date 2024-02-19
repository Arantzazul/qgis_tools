import csv
import googlemaps
import io
from datetime import datetime
from pathlib import Path
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

    # print(points)
    return points

class PlotRoutes:
    def __init__(self):
        self.gmaps = googlemaps.Client("AIzaSyCvJVZR8eK-yi8HDVfcF2VSD9xrYRDzczg")
        self.building_address = {"ATEGORRIETA (LH)": "Atarizar Kalea, 18, 20013 Donostia, Gipuzkoa",
                                 "VILLA SOROA (HH)": "Ategorrieta Hiribidea, 24, 20013 Donostia, Gipuzkoa",
                                 "HURRA (DBH eta BATXILERGOA)": "Indianoene Kalea, 1, Donostia"}
        self.modes = {"Oinez / A pie": "walking",
                      "Autoz / En coche": "driving",
                      "Bizikletaz / En bici": "bicycling",
                      "Autobusez / En autobús": "transit",
                      "Motorrez / En moto": "driving",
                      "Patinetez / En patinete": "bicycling"}

    def get_qgs_feature_from_directions(self, from_address, to_address, mode, departure_time):
        print(f'Mode: {mode}\n')
        directions_result = self.gmaps.directions(from_address, to_address, mode=mode,
                                                  departure_time=departure_time)
        point_str = str(directions_result[0]["overview_polyline"]["points"])
        points = decode(point_str)

        if len(points) <= 0:
            print(f'No points for route from: {from_address}\n\tto: {to_address}\n\tmode: {mode}')

        feature = QgsFeature()
        seg = []
        for i in range(0, len(points)):
            seg.append(QgsPoint(points[i][0], points[i][1]))

        feature.setGeometry(QgsGeometry.fromPolyline(seg))
        feature.setAttributes(["route provided by google maps api"])

        return feature

    def get_addresses_from_file(self, path):
        # TODO import from csv
        # returns a list of tuples (from_address, to_address)
        addresses = []
        with io.open(path, encoding='latin1', newline='') as csv_file:
        # with open(path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            column_names = None
            line_count = 0
            for row in csv_reader:
                if line_count == 0:
                    print(f'Column names are {", ".join(row)}')
                    line_count += 1
                    column_names = row
                else:
                    building = row[column_names.index("Building")]
                    address = row[column_names.index("Address")]
                    city = row[column_names.index("City")]
                    mode_in = row[column_names.index("Way in")]
                    mode_in = self.modes[mode_in]
                    # print(f'\t Building: {building}, Address: {address}, City: {city}.')
                    addresses.append((address + ", " + city, self.building_address[building], mode_in))
                    line_count += 1
            print(f'Processed {line_count} lines.')
            return addresses

    def plot_routes_from_file(self, path, departure_time):
        # Create qgis layer
        layer = QgsVectorLayer('LineStringZ', 'route', "memory")
        pr = layer.dataProvider()
        pr.addAttributes([QgsField("attribution", QVariant.String)])
        layer.updateFields()

        addresses = self.get_addresses_from_file(path)
        for address in addresses:
            feature = self.get_qgs_feature_from_directions(address[0], address[1], address[2], departure_time)
            pr.addFeatures([feature])

        layer.updateExtents()  # update it
        QgsProject.instance().addMapLayer(layer)


def main():
    print("Running plot routes")
    # TODO maybe use a more specific time
    departure_time = datetime.now()
    data_folder = Path("C:/DATOS/PROYECTOS/2303_Mugikortasun batzordea/QGIS/Input data/Familiak joan etorriak Inkesta 2022")
    file_path = data_folder / "Familiak 2022 MUGIKORTASUN PLANA_ IKASTOLARAKO JOAN- ETORRIAK (Erantzunak)-FOR QGIS-City added.csv"
    # file_path = 'C:\DATOS\PROYECTOS\2303_Mugikortasun batzordea\QGIS\Input data\Familiak joan etorriak Inkesta 2022\Familiak 2022 MUGIKORTASUN PLANA_ IKASTOLARAKO JOAN- ETORRIAK (Erantzunak)-FOR QGIS-City added.csv'
    plot_routes = PlotRoutes()
    plot_routes.plot_routes_from_file(file_path, departure_time)

main()

if __name__ == "__main__":
    main()