# -*- coding: utf-8 -*-

import os
from ckanext.spatial.harvested_metadata_fgdc import FGDCDocument

class TestFGDCDocument(object):

    def read_file(self, path):
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
        with open(file_path, "r") as f:
            return f.read()

    def test_parsing_FGDCDocument(self, app):
        xml_content = self.read_file("xml/fgdc/climate-sensitivity-of-sierra-nevada-lakes.xml")
        try:
            fgdc_parser = FGDCDocument(xml_content)
            fgdc_values = fgdc_parser.read_values()

            assert fgdc_values["title"] == "Climate sensitivity of Sierra Nevada Lakes"

            assert fgdc_values["abstract"] == """
  We analyzed the thermal response in the upper mixed layer of a lake in
  the Sierra Nevada of California to interannual variation in air
  temperature, snow deposition, and other climate factors to
  characterize relative effects on water temperature. We then use summer
  temperature data from 19 lakes to understand how the relative
  importance of snow and other factors governing lake temperature vary
  at broad spatial scales and predict sensitivity to warming in over
  1600 lakes across the region. Our study has three specific objectives:
  1) to characterize how water temperatures in mountain lakes are
  responding to variation in air temperature, snow deposition, and other
  climate factors; 2) to evaluate scaling relationships for water
  temperature using landscape and lake morphometric attributes; and 3)
  using those scaling relationships, to identify lakes that are most
  sensitive to warming from ongoing changes in climate. Our results
  emphasize the high rate of climate warming taking place in mountain
  ecosystems, and demonstrate the substantial role of snowpack in
  governing lake temperature. We illustrate the extent to which warming
  within lakes scales with elevation and lake morphometric attributes,
  and use those empirical relationships to identify lakes most sensitive
  to ongoing changes in climate.
"""

            assert fgdc_values["contact-email"] == ["ssadro@ucdavis.edu"]

            tags = fgdc_values.get("tags", [])
            assert len(tags) == 7

            resource_locators = fgdc_values.get("resource-locator", [])
            assert len(resource_locators) == 4
        except Exception as e:
            assert False, "Error parsing FGDC document: %s" % e
