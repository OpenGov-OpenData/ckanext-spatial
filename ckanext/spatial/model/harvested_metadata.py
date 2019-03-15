from lxml import etree

import logging
log = logging.getLogger(__name__)


class MappedXmlObject(object):
    elements = []


class MappedXmlDocument(MappedXmlObject):
    def __init__(self, xml_str=None, xml_tree=None):
        assert (xml_str or xml_tree is not None), 'Must provide some XML in one format or another'
        self.xml_str = xml_str
        self.xml_tree = xml_tree

    def read_values(self):
        '''For all of the elements listed, finds the values of them in the
        XML and returns them.'''
        values = {}
        tree = self.get_xml_tree()
        for element in self.elements:
            values[element.name] = element.read_value(tree)
        self.infer_values(values)
        return values

    def read_value(self, name):
        '''For the given element name, find the value in the XML and return
        it.
        '''
        tree = self.get_xml_tree()
        for element in self.elements:
            if element.name == name:
                return element.read_value(tree)
        raise KeyError

    def get_xml_tree(self):
        if self.xml_tree is None:
            parser = etree.XMLParser(remove_blank_text=True)
            if type(self.xml_str) == unicode:
                xml_str = self.xml_str.encode('utf8')
            else:
                xml_str = self.xml_str
            self.xml_tree = etree.fromstring(xml_str, parser=parser)
        return self.xml_tree

    def infer_values(self, values):
        pass


class MappedXmlElement(MappedXmlObject):
    namespaces = {}

    def __init__(self, name, search_paths=[], multiplicity="*", elements=[]):
        self.name = name
        self.search_paths = search_paths
        self.multiplicity = multiplicity
        self.elements = elements or self.elements

    def read_value(self, tree):
        values = []
        for xpath in self.get_search_paths():
            elements = self.get_elements(tree, xpath)
            values = self.get_values(elements)
            if values:
                break
        return self.fix_multiplicity(values)

    def get_search_paths(self):
        if type(self.search_paths) != type([]):
            search_paths = [self.search_paths]
        else:
            search_paths = self.search_paths
        return search_paths

    def get_elements(self, tree, xpath):
        return tree.xpath(xpath, namespaces=self.namespaces)

    def get_values(self, elements):
        values = []
        if len(elements) == 0:
            pass
        else:
            for element in elements:
                value = self.get_value(element)
                values.append(value)
        return values

    def get_value(self, element):
        if self.elements:
            value = {}
            for child in self.elements:
                value[child.name] = child.read_value(element)
            return value
        elif type(element) == etree._ElementStringResult:
            value = str(element)
        elif type(element) == etree._ElementUnicodeResult:
            value = unicode(element)
        else:
            value = self.element_tostring(element)
        return value

    def element_tostring(self, element):
        return etree.tostring(element, pretty_print=False)

    def fix_multiplicity(self, values):
        '''
        When a field contains multiple values, yet the spec says
        it should contain only one, then return just the first value,
        rather than a list.

        In the ISO19115 specification, multiplicity relates to:
        * 'Association Cardinality'
        * 'Obligation/Condition' & 'Maximum Occurence'
        '''
        if self.multiplicity == "0":
            # 0 = None
            if values:
                log.warn("Values found for element '%s' when multiplicity should be 0: %s",  self.name, values)
            return ""
        elif self.multiplicity == "1":
            # 1 = Mandatory, maximum 1 = Exactly one
            if not values:
                log.warn("Value not found for element '%s'" % self.name)
                return ''
            return values[0]
        elif self.multiplicity == "*":
            # * = 0..* = zero or more
            return values
        elif self.multiplicity == "0..1":
            # 0..1 = Mandatory, maximum 1 = optional (zero or one)
            if values:
                return values[0]
            else:
                return ""
        elif self.multiplicity == "1..*":
            # 1..* = one or more
            return values
        else:
            log.warning('Multiplicity not specified for element: %s',
                        self.name)
            return values


class ISOElement(MappedXmlElement):

    namespaces = {
       "gts": "http://www.isotc211.org/2005/gts",
       "gml": "http://www.opengis.net/gml",
       "gml32": "http://www.opengis.net/gml/3.2",
       "gmx": "http://www.isotc211.org/2005/gmx",
       "gsr": "http://www.isotc211.org/2005/gsr",
       "gss": "http://www.isotc211.org/2005/gss",
       "gco": "http://www.isotc211.org/2005/gco",
       "gmd": "http://www.isotc211.org/2005/gmd",
       "srv": "http://www.isotc211.org/2005/srv",
       "xlink": "http://www.w3.org/1999/xlink",
       "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    }


class ISOResourceLocator(ISOElement):

    elements = [
        ISOElement(
            name="url",
            search_paths=[
                "gmd:linkage/gmd:URL/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="function",
            search_paths=[
                "gmd:function/gmd:CI_OnLineFunctionCode/@codeListValue",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="name",
            search_paths=[
                "gmd:name/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="description",
            search_paths=[
                "gmd:description/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="protocol",
            search_paths=[
                "gmd:protocol/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
    ]


class ISOResponsibleParty(ISOElement):

    elements = [
        ISOElement(
            name="individual-name",
            search_paths=[
                "gmd:individualName/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="organisation-name",
            search_paths=[
                "gmd:organisationName/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="position-name",
            search_paths=[
                "gmd:positionName/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="contact-address",
            search_paths=[
                "gmd:address/gmd:CI_Address",
            ],
            multiplicity="*",
            elements = [
                ISOElement(
                    name="deliveryPoint",
                    search_paths=[
                        "gmd:deliveryPoint/gco:CharacterString/text()",
                    ],
                    multiplicity="*",
                ),
                ISOElement(
                    name="city",
                    search_paths=[
                        "gmd:city/gco:CharacterString/text()",
                    ],
                    multiplicity="0..1",
                ),
                ISOElement(
                    name="administrative-area",
                    search_paths=[
                        "gmd:administrativeArea/gco:CharacterString/text()",
                    ],
                    multiplicity="0..1",
                ),
                ISOElement(
                    name="postal-code",
                    search_paths=[
                        "gmd:postalCode/gco:CharacterString/text()",
                    ],
                    multiplicity="0..1",
                ),
                ISOElement(
                    name="country",
                    search_paths=[
                        "gmd:country/gco:CharacterString/text()",
                    ],
                    multiplicity="0..1",
                ),
            ]
        ),
        ISOElement(
            name="contact-info",
            search_paths=[
                "gmd:contactInfo/gmd:CI_Contact",
            ],
            multiplicity="0..1",
            elements = [
                ISOElement(
                    name="email",
                    search_paths=[
                        "gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString/text()",
                    ],
                    multiplicity="*",
                ),
                ISOElement(
                    name="fax",
                    search_paths=[
                        "gmd:phone/gmd:CI_Telephone/gmd:facsimile/gco:CharacterString/text()",
                    ],
                    multiplicity="*",
                ),
                ISOElement(
                    name="telephone",
                    search_paths=[
                        "gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString/text()",
                    ],
                    multiplicity="*",
                ),
                ISOElement(
                    name="hours-of-service",
                    search_paths=[
                        "gmd:hoursOfService/gco:CharacterString/text()",
                    ],
                    multiplicity="0..1",
                ),
                ISOElement(
                    name="contact-instructions",
                    search_paths=[
                        "gmd:contactInstructions/gco:CharacterString/text()",
                    ],
                    multiplicity="0..1",
                ),
                ISOResourceLocator(
                    name="online-resource",
                    search_paths=[
                        "gmd:onlineResource/gmd:CI_OnlineResource",
                    ],
                    multiplicity="0..1",
                ),
            ]
        ),
        ISOElement(
            name="role",
            search_paths=[
                "gmd:role/gmd:CI_RoleCode/@codeListValue",
            ],
            multiplicity="0..1",
        ),
    ]


class ISODataFormat(ISOElement):

    elements = [
        ISOElement(
            name="name",
            search_paths=[
                "gmd:name/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="version",
            search_paths=[
                "gmd:version/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
    ]


class ISOReferenceDate(ISOElement):

    elements = [
        ISOElement(
            name="type",
            search_paths=[
                "gmd:dateType/gmd:CI_DateTypeCode/@codeListValue",
                "gmd:dateType/gmd:CI_DateTypeCode/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="value",
            search_paths=[
                "gmd:date/gco:Date/text()",
                "gmd:date/gco:DateTime/text()",
            ],
            multiplicity="1",
        ),
    ]

class ISOCoupledResources(ISOElement):

    elements = [
        ISOElement(
            name="title",
            search_paths=[
                "@xlink:title",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="href",
            search_paths=[
                "@xlink:href",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="uuid",
            search_paths=[
                "@uuidref",
            ],
            multiplicity="*",
        ),

    ]


class ISOBoundingBox(ISOElement):

    elements = [
        ISOElement(
            name="west",
            search_paths=[
                "gmd:westBoundLongitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="east",
            search_paths=[
                "gmd:eastBoundLongitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="north",
            search_paths=[
                "gmd:northBoundLatitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="south",
            search_paths=[
                "gmd:southBoundLatitude/gco:Decimal/text()",
            ],
            multiplicity="1",
        ),
    ]


class ISOBoundingAltitude(ISOElement):

    elements = [
        ISOElement(
            name="minimum-altitude",
            search_paths=[
                "gmd:minimumValue/gco:Real",
                "gmd:verticalCRS/gml:VerticalCRS/gml:usesVerticalCS/gml:VerticalCS/gml:axis/gml:CoordinateSystemAxis/gml:minimumValue/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="maximum-altitude",
            search_paths=[
                "gmd:maximumValue/gco:Real",
                "gmd:verticalCRS/gml:VerticalCRS/gml:usesVerticalCS/gml:VerticalCS/gml:axis/gml:CoordinateSystemAxis/gml:maximumValue/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="altitude-units",
            search_paths=[
                "gmd:verticalCRS/gml:VerticalCRS/gml:axis/gml:CoordinateSystemAxis/@uom",
            ],
            multiplicity="1",
        ),
    ]


class ISOBrowseGraphic(ISOElement):

    elements = [
        ISOElement(
            name="file",
            search_paths=[
                "gmd:fileName/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="description",
            search_paths=[
                "gmd:fileDescription/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="type",
            search_paths=[
                "gmd:fileType/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
    ]


class ISOKeyword(ISOElement):

    elements = [
        ISOElement(
            name="keyword",
            search_paths=[
                "gmd:keyword/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="type",
            search_paths=[
                "gmd:type/gmd:MD_KeywordTypeCode/@codeListValue",
                "gmd:type/gmd:MD_KeywordTypeCode/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="thesaurus-name",
            search_paths=[
                "gmd:thesaurusName/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
                "gmd:thesaurusName/@xlink:href",
            ],
            multiplicity="0..1",
        ),
   ]


class ISOUsage(ISOElement):

    elements = [
        ISOElement(
            name="usage",
            search_paths=[
                "gmd:specificUsage/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOResponsibleParty(
            name="contact-info",
            search_paths=[
                "gmd:userContactInfo/gmd:CI_ResponsibleParty",
            ],
            multiplicity="0..1",
        ),

   ]


class ISOAggregationInfo(ISOElement):

    elements = [
        ISOElement(
            name="aggregate-dataset-name",
            search_paths=[
                "gmd:aggregateDatasetName/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="aggregate-dataset-identifier",
            search_paths=[
                "gmd:aggregateDatasetIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="association-type",
            search_paths=[
                "gmd:associationType/gmd:DS_AssociationTypeCode/@codeListValue",
                "gmd:associationType/gmd:DS_AssociationTypeCode/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="initiative-type",
            search_paths=[
                "gmd:initiativeType/gmd:DS_InitiativeTypeCode/@codeListValue",
                "gmd:initiativeType/gmd:DS_InitiativeTypeCode/text()",
            ],
            multiplicity="0..1",
        ),
   ]


class ISOObliqueLineAzimuth(ISOElement):

    elements = [
        ISOElement(
            name="azimuth-angle",
            search_paths=[
                "gmd:MD_ObliqueLineAzimuth/gmd:azimuthAngle/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="azimuth-measure-point-longitude",
            search_paths=[
                "gmd:MD_ObliqueLineAzimuth/gmd:azimuthMeasurePointLongitude/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
   ]


class ISOObliqueLinePoint(ISOElement):

    elements = [
        ISOElement(
            name="oblique-line-latitude",
            search_paths=[
                "gmd:MD_ObliqueLinePoint/gmd:obliqueLineLatitude/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="oblique-line-longitude",
            search_paths=[
                "gmd:MD_ObliqueLinePoint/gmd:obliqueLineLongitude/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
   ]


class ISOMapProjection(ISOElement):

    elements = [
        ISOElement(
            name="map-projection-name",
            search_paths=[
                "gmd:projection/gmd:RS_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="standard-parallel",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:standardParellel/gco:real/text()",
            ],
            multiplicity="0..*",
        ),
        ISOElement(
            name="longitude-of-central-meridian",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:longitudeOfCentralMeridian/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="latitude-of-projection-origin",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:latitudeOfProjectionOrigin/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="false-easting",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:falseEasting/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="false-northing",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:falseNorthing/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="scale-factor-at-equator",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:scaleFactorAtEquator/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="height-of-perspective-point-above-surface",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:heightOfProspectivePointAboveSurface/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="longitude-of-projection-center",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:longitudeOfProjectionCenter/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="latitude-of-projection-center",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:latitudeOfProjectionCenter/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="scale-factor-at-center-line",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:scaleFactorAtCenterLine/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="straight-vertical-longitude-from-pole",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:straightVerticalLongitudeFromPole/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="scale-factor-at-projection-origin",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:scaleFactorAtProjectionOrigin/gco:real/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="other-projections-definition",
            search_paths=[
                "gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOObliqueLineAzimuth(
            name="oblique-line-azimuth",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:obliqueLineAzimuthParameter",
            ],
            multiplicity="0..1",
        ),
        ISOObliqueLinePoint(
            name="oblique-line-point",
            search_paths=[
                "gmd:projectionParameters/gmd:MD_ProjectionParameters/gmd:obliqueLinePointParameter",
            ],
            multiplicity="0..*",
        ),
   ]


class ISODocument(MappedXmlDocument):

    # Attribute specifications from "XPaths for GEMINI" by Peter Parslow.

    elements = [
        ISOElement(
            name="guid",
            search_paths="gmd:fileIdentifier/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="edition",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:edition/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="other-citation-details",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:otherCitationDetails/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="currentness-reference",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gml:TimePeriod/gml:description/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:description/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="geographic-extent-description",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:authority/gmd:CI_Citation/gmd:otherCitationDetails/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="credit",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:credit/gco:CharacterString/text()",
            multiplicity="*",
        ),
        ISOElement(
            name="completeness-report",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_CompletenessCommission/gmd:evaluationMethodDescription/gco:CharacterString/text()",
            multiplicity="1",
        ),
        ISOElement(
            name="methodology-type",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:processStep/gmd:LI_ProcessStep/gmd:rationale/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="methodology-description",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:processStep/gmd:LI_ProcessStep/gmd:description/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="lineage-presentation-form",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceCitation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceCitation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceCitation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceCitation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="lineage-title",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceCitation/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            multiplicity="1",
        ),
        ISOReferenceDate(
            name="lineage-reference-date",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceCitation/gmd:CI_Citation/gmd:date/gmd:CI_Date",
            multiplicity="1..*",
        ),
        ISOElement(
            name="lineage-edition",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceCitation/gmd:CI_Citation/gmd:edition/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOResponsibleParty(
            name="lineage-responsible-organisation",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceCitation/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty",
            multiplicity="1..*",
        ),
        ISOElement(
            name="source-scale-denominator",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:scaleDenominator/gmd:MD_RepresentativeFraction/gmd:denominator/gco:Integer/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="type-of-source-media",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:description/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="source-currentness-reference",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:description/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:description/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="source-citation-abbreviation",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceCitation/gmd:CI_Citation/gmd:alternateTitle/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="source-contribution",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:description/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="process-description",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:processStep/gmd:LI_ProcessStep/gmd:description/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="process-date",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:processStep/gmd:LI_ProcessStep/gmd:dateTime/gco:DateTime/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="distribution-liability",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="environment-description",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:environmentDescription/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="geographic-description",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:authority/gmd:CI_Citation/gmd:otherCitationDetails/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="metadata-language",
            search_paths=[
                "gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:language/gmd:LanguageCode/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="metadata-standard-name",
            search_paths="gmd:metadataStandardName/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="metadata-standard-version",
            search_paths="gmd:metadataStandardVersion/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="resource-type",
            search_paths=[
                "gmd:hierarchyLevel/gmd:MD_ScopeCode/@codeListValue",
                "gmd:hierarchyLevel/gmd:MD_ScopeCode/text()",
            ],
            multiplicity="*",
        ),
        ISOResponsibleParty(
            name="metadata-point-of-contact",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="1..*",
        ),
        ISOElement(
            name="metadata-date",
            search_paths=[
                "gmd:dateStamp/gco:DateTime/text()",
                "gmd:dateStamp/gco:Date/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="spatial-reference-system",
            search_paths=[
                "gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="title",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="alternate-title",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:alternateTitle/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:alternateTitle/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        ISOReferenceDate(
            name="dataset-reference-date",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date",
            ],
            multiplicity="1..*",
        ),
        ISOElement(
            name="unique-resource-identifier",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="presentation-form",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:citation/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="geologic-presentation-form",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_TemporalValidity/gmd:measureIdentification/gmd:MD_Identifier/gmd:authority/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_TemporalValidity/gmd:measureIdentification/gmd:MD_Identifier/gmd:authority/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="geologic-title",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_TemporalValidity/gmd:measureIdentification/gmd:MD_Identifier/gmd:authority/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            multiplicity="1",
        ),
        ISOReferenceDate(
            name="geologic-reference-date",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_TemporalValidity/gmd:measureIdentification/gmd:MD_Identifier/gmd:authority/gmd:CI_Citation/gmd:date/gmd:CI_Date",
            multiplicity="1..*",
        ),
        ISOElement(
            name="geologic-edition",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_TemporalValidity/gmd:measureIdentification/gmd:MD_Identifier/gmd:authority/gmd:CI_Citation/gmd:edition/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOResponsibleParty(
            name="geologic-responsible-party",
            search_paths="gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_TemporalValidity/gmd:measureIdentification/gmd:MD_Identifier/gmd:authority/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty",
            multiplicity="1..*",
        ),
        ISOElement(
            name="classsys-presentation-form",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:classSys/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:classSys/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:classSys/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:classSys/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="classsys-title",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:classSys/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            multiplicity="1",
        ),
        ISOReferenceDate(
            name="classsys-reference-date",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:classSys/gmd:CI_Citation/gmd:date/gmd:CI_Date",
            multiplicity="1..*",
        ),
        ISOElement(
            name="classsys-edition",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:classSys/gmd:CI_Citation/gmd:edition/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOResponsibleParty(
            name="classsys-responsible-party",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:classSys/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty",
            multiplicity="1..*",
        ),
        ISOElement(
            name="idref-presentation-form",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:idref/gmd:RS_Identifier/gmd:authority/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:idref/gmd:RS_Identifier/gmd:authority/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:idref/gmd:RS_Identifier/gmd:authority/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:idref/gmd:RS_Identifier/gmd:authority/gmd:CI_Citation/gmd:presentationForm/gmd:CI_PresentationFormCode/@codeListValue",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="idref-title",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:idref/gmd:RS_Identifier/gmd:authority/gmd:CI_Citation/gmd:title/gco:CharacterString/text()",
            multiplicity="1",
        ),
        ISOReferenceDate(
            name="idref-reference-date",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:idref/gmd:RS_Identifier/gmd:authority/gmd:CI_Citation/gmd:date/gmd:CI_Date",
            multiplicity="1..*",
        ),
        ISOElement(
            name="idref-edition",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:idref/gmd:RS_Identifier/gmd:authority/gmd:CI_Citation/gmd:edition/gco:CharacterString/text()",
            multiplicity="0..1",
        ),
        ISOResponsibleParty(
            name="idref-responsible-party",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:idref/gmd:RS_Identifier/gmd:authority/gmd:CI_Citation/gmd:citedResponsibleParty/gmd:CI_ResponsibleParty",
            multiplicity="1..*",
        ),
        ISOResponsibleParty(
            name="ider-responsible-party",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:obs/gmd:CI_ResponsibleParty",
            multiplicity="1..*",
        ),
        ISOResponsibleParty(
            name="vouchers-responsible-party",
            search_paths="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:taxonomy/gmd:MD_TaxonSys/gmd:voucher/gmd:MD_Vouchers/gmd:reposit/gmd:CI_ResponsibleParty",
            multiplicity="1..*",
        ),
        ISOElement(
            name="abstract",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:abstract/gco:CharacterString/text()",
            ],
            multiplicity="1",
        ),
        ISOElement(
            name="purpose",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:purpose/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:purpose/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOResponsibleParty(
            name="responsible-organisation",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
                "gmd:contact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="1..*",
        ),
        ISOResponsibleParty(
            name="metadata-contact",
            search_paths=[
                "gmd:contact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="frequency-of-update",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceAndUpdateFrequency/gmd:MD_MaintenanceFrequencyCode/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="maintenance-note",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceNote/gco:CharacterString/text()",
                "gmd:identificationInfo/gmd:SV_ServiceIdentification/gmd:resourceMaintenance/gmd:MD_MaintenanceInformation/gmd:maintenanceNote/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="progress",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:status/gmd:MD_ProgressCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:status/gmd:MD_ProgressCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:status/gmd:MD_ProgressCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:status/gmd:MD_ProgressCode/text()",
            ],
            multiplicity="*",
        ),
        ISOKeyword(
            name="keywords",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords",
            ],
            multiplicity="*"
        ),
        ISOElement(
            name="keyword-inspire-theme",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        # Deprecated: kept for backwards compatibilty
        ISOElement(
            name="keyword-controlled-other",
            search_paths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:keywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        ISOUsage(
            name="usage",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceSpecificUsage/gmd:MD_Usage",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceSpecificUsage/gmd:MD_Usage",
            ],
            multiplicity="*"
        ),
        ISOElement(
            name="limitations-on-public-access",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="access-constraints",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/gmd:MD_RestrictionCode/text()",
            ],
            multiplicity="*",
        ),

        ISOElement(
            name="use-constraints",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        ISOAggregationInfo(
            name="aggregation-info",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:aggregationInfo/gmd:MD_AggregateInformation",
                "gmd:identificationInfo/gmd:SV_ServiceIdentification/gmd:aggregationInfo/gmd:MD_AggregateInformation",
            ],
            multiplicity="*"
        ),
        ISOElement(
            name="spatial-data-service-type",
            search_paths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:serviceType/gco:LocalName/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="spatial-resolution",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="spatial-resolution-units",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/@uom",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/gco:Distance/@uom",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="equivalent-scale",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/gco:Integer/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/gmd:MD_RepresentativeFraction/gmd:denominator/gco:Integer/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="dataset-language",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="topic-category",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:topicCategory/gmd:MD_TopicCategoryCode/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="extent-controlled",
            search_paths=[
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="extent-free-text",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()",
            ],
            multiplicity="*",
        ),
        ISOBoundingBox(
            name="bbox",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox",
            ],
            multiplicity="*",
        ),
        ISOBoundingAltitude(
            name="bounding-altitude",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:verticalElement/gmd:EX_VerticalExtent",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="temporal-extent-begin",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:beginPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:beginPosition/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="temporal-extent-end",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition/text()",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:endPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:endPosition/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="lineage-temporal-extent-begin",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:beginPosition/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:beginPosition/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="lineage-temporal-extent-end",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:endPosition/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml32:TimePeriod/gml32:endPosition/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="lineage-temporal-calendar-date",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml:TimeInstant/gml:timePosition/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml32:TimeInstant/gml32:timePosition/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml:TimeInstant/gml:timePosition/text()",
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:source/gmd:LI_Source/gmd:sourceExtent/gmd:EX_Extent/gmd:temporalExtent/gmd:EX_TemporalExtent/gmd:extent/gml32:TimeInstant/gml32:timePosition/text()",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="available-datetime",
            search_paths="gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributionOrderProcess/gmd:MD_StandardOrderProcess/gmd:plannedAvailableDateTime/gco:DateTime/text()",
            multiplicity="0..1",
        ),
        ISOElement(
            name="vertical-extent",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:verticalElement/gmd:EX_VerticalExtent",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:extent/gmd:EX_Extent/gmd:verticalElement/gmd:EX_VerticalExtent",
            ],
            multiplicity="*",
        ),
        ISOCoupledResources(
            name="coupled-resource",
            search_paths=[
                "gmd:identificationInfo/srv:SV_ServiceIdentification/srv:operatesOn",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="additional-information-source",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:supplementalInformation/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISODataFormat(
            name="data-format",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat/gmd:MD_Format",
            ],
            multiplicity="*",
        ),
        ISOResponsibleParty(
            name="distributor",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="*",
        ),
        ISOResourceLocator(
            name="resource-locator",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource",
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor/gmd:distributorTransferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource"
            ],
            multiplicity="*",
        ),
        ISOResourceLocator(
            name="resource-locator-identification",
            search_paths=[
                "gmd:identificationInfo//gmd:CI_OnlineResource",
            ],
            multiplicity="*",
        ),
        ISOElement(
            name="conformity-specification",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:specification",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="conformity-pass",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:pass/gco:Boolean/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="conformity-explanation",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_DomainConsistency/gmd:result/gmd:DQ_ConformanceResult/gmd:explanation/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="lineage",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:statement/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="geologic-time-scale",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimeInstant/gml:name/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="geologic-age-estimate",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimeInstant/gml:timePosition/calendarEraName",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="beginning-geologic-time-scale",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:begin/gml:TimeInstant/gml:name/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="beginning-geologic-age-estimate",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:begin/gml:TimeInstant/gml:timePosition/calendarEraName",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="ending-geologic-time-scale",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:end/gml:TimeInstant/gml:name/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="ending-geologic-age-estimate",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:end/gml:TimeInstant/gml:timePosition/calendarEraName",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="geologic-age-uncertainty",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_TemporalValidity/gmd:result/gmd:DQ_QuantitativeResult/gmd:value/gco:Record/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="geologic-age-explanation",
            search_paths=[
                "gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_TemporalValidity/gmd:evaluationMethodDescription/gco:CharacterString/text()",
            ],
            multiplicity="0..1",
        ),
        ISOBrowseGraphic(
            name="browse-graphic",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:graphicOverview/gmd:MD_BrowseGraphic",
            ],
            multiplicity="*",
        ),
        ISOMapProjection(
            name="map-projection",
            search_paths=[
                "gmd:referenceSystemInfo/gmd:MD_CRS",
            ],
            multiplicity="*",
        ),

    ]

    def infer_values(self, values):
        # Todo: Infer name.
        self.infer_date_released(values)
        self.infer_date_updated(values)
        self.infer_date_created(values)
        self.infer_url(values)
        # Todo: Infer resources.
        self.infer_tags(values)
        self.infer_publisher(values)
        self.infer_originator(values)
        self.infer_contact(values)
        self.infer_contact_email(values)
        return values

    def infer_date_released(self, values):
        value = ''
        for date in values['dataset-reference-date']:
            if date['type'] == 'publication':
                value = date['value']
                break
        values['date-released'] = value

        lineage_value = ''
        for date in values['lineage-reference-date']:
            if date['type'] == 'publication':
                lineage_value = date['value']
                break
        values['lineage-released'] = lineage_value

        geologic_value = ''
        for date in values['geologic-reference-date']:
            if date['type'] == 'publication':
                geologic_value = date['value']
                break
        values['geologic-released'] = geologic_value

        classsys_value = ''
        for date in values['classsys-reference-date']:
            if date['type'] == 'publication':
                classsys_value = date['value']
                break
        values['classsys-released'] = classsys_value

        idref_value = ''
        for date in values['idref-reference-date']:
            if date['type'] == 'creation':
                idref_value = date['value']
                break
        values['idref-released'] = idref_value

    def infer_date_updated(self, values):
        value = ''
        dates = []
        # Use last of several multiple revision dates.
        for date in values['dataset-reference-date']:
            if date['type'] == 'revision':
                dates.append(date['value'])

        if len(dates):
            if len(dates) > 1:
                dates.sort(reverse=True)
            value = dates[0]

        values['date-updated'] = value

    def infer_date_created(self, values):
        value = ''
        for date in values['dataset-reference-date']:
            if date['type'] == 'creation':
                value = date['value']
                break
        values['date-created'] = value

    def infer_url(self, values):
        value = ''
        for locator in values['resource-locator']:
            if locator['function'] == 'information':
                value = locator['url']
                break
        values['url'] = value

    def infer_tags(self, values):
        tags = []
        for key in ['keyword-inspire-theme', 'keyword-controlled-other']:
            for item in values[key]:
                if item not in tags:
                    tags.append(item)
        values['tags'] = tags

    def infer_publisher(self, values):
        value = ''
        for responsible_party in values['responsible-organisation']:
            if responsible_party['role'] == 'publisher':
                value = responsible_party['organisation-name']
            if value:
                break
        values['publisher'] = value

        lineage_value = ''
        for responsible_party in values['lineage-responsible-organisation']:
            if responsible_party['role'] == 'publisher':
                lineage_value = responsible_party['organisation-name']
            if lineage_value:
                break
        values['lineage-publisher'] = lineage_value

        geologic_value = ''
        for responsible_party in values['geologic-responsible-party']:
            if responsible_party['role'] == 'publisher':
                geologic_value = responsible_party['organisation-name']
            if geologic_value:
                break
        values['geologic-publisher'] = geologic_value

        classsys_value = ''
        for responsible_party in values['classsys-responsible-party']:
            if responsible_party['role'] == 'publisher':
                classsys_value = responsible_party['organisation-name']
            if classsys_value:
                break
        values['classsys-publisher'] = classsys_value

        idref_value = ''
        for responsible_party in values['idref-responsible-party']:
            if responsible_party['role'] == 'publisher':
                idref_value = responsible_party['organisation-name']
            if idref_value:
                break
        values['idref-publisher'] = idref_value

    def infer_originator(self, values):
        originator = []
        online_linkage = []
        for responsible_party in values['responsible-organisation']:
            if responsible_party['role'] == 'originator':
                if responsible_party['individual-name']:
                    originator.append(responsible_party['individual-name'])
                if responsible_party['organisation-name']:
                    originator.append(responsible_party['organisation-name'])
                linkage_url = ''
                if responsible_party['contact-info'].get('online-resource'):
                    linkage_url = responsible_party['contact-info']['online-resource'].get('url', '')
                online_linkage.append(linkage_url)
        values['originator'] = originator
        values['originator-online-linkage'] = online_linkage

        lineage_originator = []
        lineage_online_linkage = []
        for responsible_party in values['lineage-responsible-organisation']:
            if responsible_party['role'] == 'originator':
                if responsible_party['individual-name']:
                    lineage_originator.append(responsible_party['individual-name'])
                if responsible_party['organisation-name']:
                    lineage_originator.append(responsible_party['organisation-name'])
                linkage_url = ''
                if responsible_party['contact-info'].get('online-resource'):
                    linkage_url = responsible_party['contact-info']['online-resource'].get('url', '')
                lineage_online_linkage.append(linkage_url)
        values['lineage-originator'] = lineage_originator
        values['lineage-originator-online-linkage'] = lineage_online_linkage

        geologic_originator = []
        geologic_online_linkage = []
        for responsible_party in values['geologic-responsible-party']:
            if responsible_party['role'] == 'originator':
                if responsible_party['individual-name']:
                    geologic_originator.append(responsible_party['individual-name'])
                if responsible_party['organisation-name']:
                    geologic_originator.append(responsible_party['organisation-name'])
                linkage_url = ''
                if responsible_party['contact-info'].get('online-resource'):
                    linkage_url = responsible_party['contact-info']['online-resource'].get('url', '')
                geologic_online_linkage.append(linkage_url)
        values['geologic-originator'] = geologic_originator
        values['geologic-originator-online-linkage'] = geologic_online_linkage

        classsys_originator = []
        classsys_online_linkage = []
        for responsible_party in values['classsys-responsible-party']:
            if responsible_party['role'] == 'originator':
                if responsible_party['individual-name']:
                    classsys_originator.append(responsible_party['individual-name'])
                if responsible_party['organisation-name']:
                    classsys_originator.append(responsible_party['organisation-name'])
                linkage_url = ''
                if responsible_party['contact-info'].get('online-resource'):
                    linkage_url = responsible_party['contact-info']['online-resource'].get('url', '')
                classsys_online_linkage.append(linkage_url)
        values['classsys-originator'] = classsys_originator
        values['classsys-originator-online-linkage'] = classsys_online_linkage

        idref_originator = []
        idref_online_linkage = []
        for responsible_party in values['idref-responsible-party']:
            if responsible_party['role'] in ['originator','author']:
                if responsible_party['individual-name']:
                    idref_originator.append(responsible_party['individual-name'])
                if responsible_party['organisation-name']:
                    idref_originator.append(responsible_party['organisation-name'])
                linkage_url = ''
                if responsible_party['contact-info'].get('online-resource'):
                    linkage_url = responsible_party['contact-info']['online-resource'].get('url', '')
                idref_online_linkage.append(linkage_url)
        values['idref-originator'] = idref_originator
        values['idref-originator-online-linkage'] = idref_online_linkage

    def infer_contact(self, values):
        value = ''
        for responsible_party in values['responsible-organisation']:
            value = responsible_party['organisation-name']
            if value:
                break
        values['contact'] = value

    def infer_contact_email(self, values):
        value = ''
        for responsible_party in values['responsible-organisation']:
            if isinstance(responsible_party, dict) and \
               isinstance(responsible_party.get('contact-info'), dict) and \
               responsible_party['contact-info'].has_key('email'):
                value = responsible_party['contact-info']['email']
                if value:
                    break
        values['contact-email'] = ','.join(value)


class GeminiDocument(ISODocument):
    '''
    For backwards compatibility
    '''
